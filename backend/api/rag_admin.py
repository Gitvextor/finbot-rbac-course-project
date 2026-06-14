"""
RAG index management API (reindex from documents/ store).
"""

from fastapi import APIRouter, Depends, HTTPException, status

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import get_current_active_user, RBACService
from models import User
from rag_index_service import get_rebuild_status, rebuild_rag_index, schedule_rag_rebuild

router = APIRouter(prefix="/api/rag", tags=["RAG Index"])


def _require_reindex_permission(user: User) -> None:
    if not (user.is_admin or RBACService.can_sign_documents(user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only executives/directors can manage the RAG index.",
        )


@router.get("/status")
def rag_index_status(
    current_user: User = Depends(get_current_active_user),
):
    """Return Qdrant collection and background rebuild status."""
    _require_reindex_permission(current_user)
    return get_rebuild_status()


@router.post("/reindex")
def rag_reindex(
    background: bool = True,
    current_user: User = Depends(get_current_active_user),
):
    """
    Rebuild the RAG index from verified documents in documents/ store.

    Default: run in background. Pass background=false to wait for completion.
    """
    _require_reindex_permission(current_user)

    if background:
        schedule_rag_rebuild()
        return {
            "message": "RAG reindex started in background.",
            **get_rebuild_status(),
        }

    try:
        result = rebuild_rag_index()
        return {"message": "RAG reindex completed.", "result": result}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG reindex failed: {exc}",
        ) from exc
