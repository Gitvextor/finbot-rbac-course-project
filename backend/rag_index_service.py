"""
RAG index lifecycle: invalidate and rebuild Qdrant from documents/ store.
"""

from __future__ import annotations

import threading
from typing import Any, Dict

from sentence_transformers import SentenceTransformer

from config import COLLECTION_NAME, SENTENCE_TRANSFORMER_LLM
from rag import (
    _COLLECTION_BUILD_LOCK,
    collect_all_chunks_qdrant,
    collection_exists,
    get_qdrant_client,
    load_documents_chunker,
)

_rebuild_state: Dict[str, Any] = {
    "running": False,
    "last_result": None,
    "last_error": None,
}


def invalidate_rag_index() -> bool:
    """Drop the Qdrant collection so the next query rebuilds from documents/."""
    client = get_qdrant_client()
    if not collection_exists(client):
        return False
    client.delete_collection(COLLECTION_NAME)
    return True


def rebuild_rag_index() -> Dict[str, Any]:
    """Synchronously rebuild the RAG index from verified documents/."""
    with _COLLECTION_BUILD_LOCK:
        invalidate_rag_index()
        chunks = load_documents_chunker()
        if not chunks:
            return {
                "status": "empty",
                "chunks": 0,
                "message": "No verified documents available for indexing.",
            }

        client = get_qdrant_client()
        embedder = SentenceTransformer(SENTENCE_TRANSFORMER_LLM)
        collect_all_chunks_qdrant(chunks, client, embedder)
        return {
            "status": "ok",
            "chunks": len(chunks),
            "message": f"Indexed {len(chunks)} chunks from documents/ store.",
        }


def _rebuild_worker() -> None:
    global _rebuild_state
    _rebuild_state["running"] = True
    _rebuild_state["last_error"] = None
    try:
        _rebuild_state["last_result"] = rebuild_rag_index()
    except Exception as exc:
        _rebuild_state["last_error"] = str(exc)
        _rebuild_state["last_result"] = {"status": "error", "message": str(exc)}
    finally:
        _rebuild_state["running"] = False


def schedule_rag_rebuild() -> None:
    """Rebuild the RAG index in a background thread."""
    if _rebuild_state["running"]:
        return
    thread = threading.Thread(target=_rebuild_worker, daemon=True)
    thread.start()


def get_rebuild_status() -> Dict[str, Any]:
    client = get_qdrant_client()
    return {
        "collection_exists": collection_exists(client),
        "rebuild_running": _rebuild_state["running"],
        "last_result": _rebuild_state["last_result"],
        "last_error": _rebuild_state["last_error"],
    }


def refresh_rag_if_eligible(target_department: str, is_verified: bool) -> None:
    """Schedule rebuild when a RAG-eligible document becomes verified."""
    if not is_verified:
        return

    from services.rag_source_registry import DEPARTMENT_TO_COLLECTION

    if target_department not in DEPARTMENT_TO_COLLECTION:
        return

    schedule_rag_rebuild()
