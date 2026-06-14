# rag.py

from docling_core.transforms.chunker import BaseChunk
import os
import hashlib
import tempfile
import threading
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

from csv_handler import (
    parse_csv_to_row_chunks,
    generate_csv_summary_chunks,
    try_csv_computation,
)
from sentence_transformers import SentenceTransformer
from openai import OpenAI

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.transforms.chunker import HierarchicalChunker
from hierarchical.postprocessor import ResultPostprocessor

from langsmith import traceable

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
)

from config import (
    ROLE_ACCESS,
    COLLECTION_NAME,
    DEEPSEEK_MODEL,
    DEEPSEEK_API_BASE,
    SENTENCE_TRANSFORMER_LLM,
    NO_CONTEXT_MESSAGE,
    RAG_SYSTEM_PROMPT,
    ROLE_COLLECTIONS,
)

from output_guardrails import OutputGuardrails
from database import SessionLocal
from services.rag_source_registry import RAGSourceRegistry


# -------------------------------
# Constants
# -------------------------------
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".csv"}
BACKEND_DIR = Path(__file__).parent
DATA_ROOT = BACKEND_DIR.parent / "data"

load_dotenv(BACKEND_DIR / ".env")

_COLLECTION_BUILD_LOCK = threading.Lock()


def get_llm_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is not set in backend/.env")
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_API_BASE)


def chat_completion(client: OpenAI, user_message: str):
    return client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        extra_body={"thinking": {"type": "disabled"}},
    )


# -------------------------------
# Qdrant Client
# -------------------------------
def get_qdrant_client() -> QdrantClient:
    # client = QdrantClient(
    #     url=os.getenv("QDRANT_URL"),
    #     api_key=os.getenv("QDRANT_API_KEY")
    # )
    client = QdrantClient(path="./qdrant_data")
    return client

#for in-memory but shared collection
#client = QdrantClient(":memory:")   

# -------------------------------
# Helpers
# -------------------------------
def generate_chunk_id(text: str, source_document: str) -> str:
    return hashlib.md5((text + source_document).encode()).hexdigest()


def build_metadata(
    chunk: BaseChunk,
    access_roles: List[str],
    collection: str,
    source_document: str,
    verification: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    meta = chunk.meta

    page_number = None
    if meta.doc_items and meta.doc_items[0].prov:
        page_number = meta.doc_items[0].prov[0].page_no

    chunk_type = None
    if meta.doc_items:
        chunk_type = meta.doc_items[0].label.value

    parent_chunk_id = None
    if meta.doc_items and meta.doc_items[0].parent:
        parent_chunk_id = meta.doc_items[0].parent.cref

    section_title = None
    if meta.headings:
        section_title = meta.headings[-1]

    verification = verification or {}
    is_verified = bool(verification.get("is_verified"))
    signature_valid = bool(verification.get("signature_valid"))

    return {
        "chunk_id": generate_chunk_id(chunk.text, source_document),
        "source_document": source_document,
        "collection": collection,
        "access_roles": access_roles,
        "section_title": section_title,
        "page_number": page_number,
        "chunk_type": chunk_type,
        "parent_chunk_id": parent_chunk_id,
        "doc_id": verification.get("doc_id"),
        "document_hash": verification.get("document_hash"),
        "is_verified": is_verified,
        "signature_valid": signature_valid,
        "ingestion_source": verification.get("ingestion_source", "documents"),
    }


# -------------------------------
# Document Loading + Chunking
# -------------------------------
@traceable(name="Document Loading + Chunking")
def load_documents_chunker() -> List[Any]:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False

    converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.DOCX,
            InputFormat.MD,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )

    registry = RAGSourceRegistry()
    db = SessionLocal()

    collection_docs = []
    csv_chunks = []
    temp_files: List[Path] = []

    try:
        registry.ensure_corpus_bootstrapped(db, DATA_ROOT)
        ingestibles = registry.list_verified_rag_documents(db)
        print(f"[load_documents] Ingesting {len(ingestibles)} verified document(s) from documents/ store")

        for item in ingestibles:
            doc = item["document"]
            collection = item["collection"]
            verification = item["verification"]
            filename = doc.original_filename
            ext = Path(filename).suffix.lower()

            try:
                if ext == ".pdf":
                    print(
                        f"[load_documents] Skip PDF (requires HuggingFace models): {filename}"
                    )
                    continue

                content = registry.read_decrypted_content(db, doc.doc_id)
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=ext,
                    prefix=f"rag_{doc.doc_id}_",
                )
                temp_file.write(content)
                temp_file.close()
                file_path = Path(temp_file.name)
                temp_files.append(file_path)

                if ext == ".csv":
                    access_roles = ROLE_ACCESS.get(collection, ["all"])
                    print(f"[load_documents] CSV from store: {filename} → csv_handler")

                    row_chunks = parse_csv_to_row_chunks(
                        file_path, collection, access_roles, verification=verification
                    )
                    summary_chunks = generate_csv_summary_chunks(
                        file_path, collection, access_roles, verification=verification
                    )
                    csv_chunks.extend(row_chunks)
                    csv_chunks.extend(summary_chunks)
                    continue

                result = converter.convert(str(file_path))
                if ext == ".pdf":
                    ResultPostprocessor(result).process()

                collection_docs.append({
                    "filename": filename,
                    "doc": result.document,
                    "collection": collection,
                    "verification": verification,
                })

            except Exception as exc:
                print(f"[load_documents] ERROR loading {filename}: {exc}")
    finally:
        db.close()


    # -------------------------------
    # Chunking (non-CSV documents)
    # -------------------------------
    chunker = HierarchicalChunker()
    all_chunks = []

    for item in collection_docs:
        doc = item["doc"]
        filename = item["filename"]
        collection = item["collection"]
        verification = item["verification"]

        chunks = chunker.chunk(doc)

        for i,chunk in enumerate(chunks):

            metadata = build_metadata(
                chunk=chunk,
                access_roles=ROLE_ACCESS.get(collection, ["all"]),
                collection=collection,
                source_document=filename,
                verification=verification,
            )

            all_chunks.append({
                "text": chunk.text,
                "metadata": metadata,
            })

    # Merge CSV chunks with document chunks
    all_chunks.extend(csv_chunks)

    for temp_path in temp_files:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

    print("Chunking done...")
    if len(all_chunks) > 100:
        print(all_chunks[100])
    print(f"Total chunks: {len(all_chunks)} (including {len(csv_chunks)} from CSV files)")

    return all_chunks


# -------------------------------
# Vector Store
# -------------------------------
@traceable(name="Vector Store Build")
def collect_all_chunks_qdrant(chunks:List[Dict[str, Any]], client:QdrantClient, embedder:SentenceTransformer) -> None:
    texts = [c["text"] for c in chunks]
    vectors = list(embedder.encode(texts, show_progress_bar=True))

    dim = embedder.get_sentence_embedding_dimension()

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="access_roles",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="collection",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="is_verified",
        field_schema=models.PayloadSchemaType.BOOL,
    )

    points = [
        PointStruct(
            id=chunk["metadata"]["chunk_id"],
            vector=vectors[idx],
            payload={
                "text": chunk["text"],
                **chunk["metadata"],
            },
        )
        for idx, chunk in enumerate(chunks)
    ]

    print("Embedding done...")
    print(len(points))

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=False,
    )


# -------------------------------
# Retrieval
# -------------------------------
@traceable(name="Retrieval Step")
def retrieve_and_context(
    query: str,
    role: str,
    client: QdrantClient,
    embedder: SentenceTransformer,
    stream: str,
) -> tuple[str, List[str], List[str], List[Dict[str, Any]]]:
    query_vector = embedder.encode(query).tolist()

    def _query(collection: str | None = None, collections: List[str] | None = None):
        conditions = [
            FieldCondition(
                key="access_roles",
                match=MatchValue(value=role),
            ),
            FieldCondition(
                key="is_verified",
                match=MatchValue(value=True),
            ),
        ]
        if collection:
            conditions.append(
                FieldCondition(
                    key="collection",
                    match=MatchValue(value=collection),
                )
            )
        elif collections:
            conditions.append(
                FieldCondition(
                    key="collection",
                    match=MatchAny(any=collections),
                )
            )

        return client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=Filter(must=conditions),
            limit=5,
            with_payload=True,
        )

    results = _query(collection=stream)

    if not results.points:
        allowed = ROLE_COLLECTIONS.get(role, ["general"])
        print(
            f"[retrieve] No hits for stream={stream}, role={role}; "
            f"retry across allowed collections: {allowed}"
        )
        results = _query(collections=allowed)

    parts = []
    citations = []
    source_metas = []

    for i, point in enumerate(results.points, 1):
        payload = point.payload
        source_line = (
            f"[Source {i} | {payload.get('source_document')} | Page {payload.get('page_number')}]"
        )

        parts.append(
            f"{source_line}\n"
            f"{payload.get('text')}"
        )

        citations.append(source_line)
        source_metas.append(
            {
                "source": source_line,
                "doc_id": payload.get("doc_id"),
                "document_hash": payload.get("document_hash"),
                "is_verified": payload.get("is_verified"),
                "signature_valid": payload.get("signature_valid"),
                "verified": bool(payload.get("is_verified") and payload.get("signature_valid")),
            }
        )

    context = "\n\n".join(parts)
    return context, parts, citations, source_metas

def collection_exists(client:QdrantClient)->bool:
    collections = client.get_collections().collections
    return any(c.name == COLLECTION_NAME for c in collections)


def collection_has_verification_metadata(client: QdrantClient) -> bool:
    if not collection_exists(client):
        return False

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=1,
        with_payload=True,
    )
    if not points:
        return True

    payload = points[0].payload or {}
    return (
        "is_verified" in payload
        and "doc_id" in payload
        and payload.get("ingestion_source") == "documents"
    )


def ensure_verified_collection(client: QdrantClient, embedder: SentenceTransformer) -> None:
    with _COLLECTION_BUILD_LOCK:
        if collection_exists(client) and not collection_has_verification_metadata(client):
            print("[rag] Rebuilding Qdrant collection (documents/ ingestion)...")
            client.delete_collection(COLLECTION_NAME)

        if not collection_exists(client):
            print("Collection does not exist, creating new collection...")
            chunks = load_documents_chunker()
            collect_all_chunks_qdrant(chunks, client, embedder)

# -------------------------------
# Main RAG Pipeline
# -------------------------------
@traceable(name="RAG Answer Pipeline")
def answer(query:str, stream:str, role:str)->tuple[str | Dict[str, list[str]], List[str], List[Dict[str, Any]]]:
    
    client = get_qdrant_client()

    embedder = SentenceTransformer(SENTENCE_TRANSFORMER_LLM)

    ensure_verified_collection(client, embedder)

    # ----- DIVERT: For HR route, try pandas computation first -----
    csv_computed_context = None
    csv_source_meta = None
    if stream == "hr":
        registry = RAGSourceRegistry()
        db = SessionLocal()
        try:
            for item in registry.list_verified_csv_documents(db, "hr"):
                doc = item["document"]
                verification = item["verification"]
                csv_path: Path | None = None
                try:
                    content = registry.read_decrypted_content(db, doc.doc_id)
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=".csv",
                        prefix=f"rag_csv_{doc.doc_id}_",
                    )
                    temp_file.write(content)
                    temp_file.close()
                    csv_path = Path(temp_file.name)

                    success, result = try_csv_computation(query, csv_path)
                    if success:
                        csv_computed_context = result
                        csv_source_meta = {
                            "source": f"[Source: {doc.original_filename} (computed from verified database)]",
                            "doc_id": verification.get("doc_id"),
                            "document_hash": verification.get("document_hash"),
                            "is_verified": verification.get("is_verified"),
                            "signature_valid": verification.get("signature_valid"),
                            "verified": True,
                        }
                        print(f"[answer] CSV computation succeeded: {result}")
                        break
                finally:
                    if csv_path is not None:
                        csv_path.unlink(missing_ok=True)
        finally:
            db.close()
    # ----- END DIVERT -----

    context, context_chunks, citations, source_metas = retrieve_and_context(
        query, role, client, embedder, stream
    )

    if not context.strip() and not csv_computed_context:
        print(f"[answer] No retrieved context for role={role}, stream={stream}")
        return NO_CONTEXT_MESSAGE, context_chunks, source_metas

    llm_client = get_llm_client()

    # ----- If CSV computation succeeded, use computed data as primary source -----
    if csv_computed_context:
        user_message = (
            f"以下数据来自公司 HR 数据库，可直接作为准确依据：\n\n"
            f"{csv_computed_context}\n\n"
            f"文档补充 Context（可能为英文）：\n{context}\n\n"
            f"用户问题：{query}\n\n"
            f"请优先使用计算结果，并用 Markdown 格式用中文回答。"
        )

        response = chat_completion(llm_client, user_message)

        print("response_llm: ", response)

        final_response = response.choices[0].message.content

        final_response += "\n\n## 引用来源\n\n"
        if csv_source_meta:
            final_response += f"- `{csv_source_meta['source']}`\n"
            source_metas = [csv_source_meta] + source_metas
        for citation in citations:
            final_response += f"- `{citation}`\n"

        print('final_response: ', final_response)
        return final_response, context_chunks, source_metas

    # ----- Normal RAG flow (no CSV computation) -----
    user_message = (
        f"Context（检索到的文档片段，可能为英文）：\n{context}\n\n"
        f"用户问题：{query}"
    )

    response = chat_completion(llm_client, user_message)

    print("response_llm: ", response)

    output_guardrails = OutputGuardrails()

    final_response = output_guardrails.run(
        response.choices[0].message.content,
        context,
        role,
    )

    final_response += "\n\n## 引用来源\n\n"

    for citation in citations:
        final_response += f"- `{citation}`\n"

    print('final_response: ', final_response)

    return final_response, context_chunks, source_metas
