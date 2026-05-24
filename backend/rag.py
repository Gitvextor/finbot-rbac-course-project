# rag.py

from docling_core.transforms.chunker import BaseChunk
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

from csv_handler import (
    parse_csv_to_row_chunks,
    generate_csv_summary_chunks,
    try_csv_computation,
    get_csv_files_for_collection,
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


# -------------------------------
# Constants
# -------------------------------
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".csv"}
DATA_ROOT = Path(__file__).parent.parent / "data"

load_dotenv()


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


def build_metadata(chunk:BaseChunk, access_roles:List[str], collection:str, source_document:str) -> Dict[str, Any]:
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

    return {
        "chunk_id": generate_chunk_id(chunk.text, source_document),
        "source_document": source_document,
        "collection": collection,
        "access_roles": access_roles,
        "section_title": section_title,
        "page_number": page_number,
        "chunk_type": chunk_type,
        "parent_chunk_id": parent_chunk_id,
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
            # CSV removed — handled separately by csv_handler
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )

    collections = list(ROLE_ACCESS.keys())

    collection_docs = []
    csv_chunks = []  # CSV chunks collected separately

    for collection in collections:
        folder = DATA_ROOT / collection

        if not folder.exists():
            print(f"[load_documents] Skip missing folder: {folder}")
            continue

        files = [
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        for file_path in files:
            try:
                if file_path.suffix.lower() == ".pdf":
                    print(
                        f"[load_documents] Skip PDF (requires HuggingFace models): {file_path.name}"
                    )
                    continue

                # ----- DIVERT: CSV files go through csv_handler -----
                if file_path.suffix.lower() == ".csv":
                    access_roles = ROLE_ACCESS.get(collection, ["all"])
                    print(f"[load_documents] CSV detected: {file_path.name} → using csv_handler")

                    row_chunks = parse_csv_to_row_chunks(file_path, collection, access_roles)
                    summary_chunks = generate_csv_summary_chunks(file_path, collection, access_roles)
                    csv_chunks.extend(row_chunks)
                    csv_chunks.extend(summary_chunks)
                    continue
                # ----- END DIVERT -----

                result = converter.convert(str(file_path))

                if file_path.suffix.lower() == ".pdf":
                    ResultPostprocessor(result).process()

                collection_docs.append({
                    "filename": file_path.name,
                    "doc": result.document,
                    "collection": collection
                })


            except Exception as exc:
                print(f"[load_documents] ERROR loading {file_path.name}: {exc}")


    # -------------------------------
    # Chunking (non-CSV documents)
    # -------------------------------
    chunker = HierarchicalChunker()
    all_chunks = []

    for item in collection_docs:
        doc = item["doc"]
        filename = item["filename"]
        collection = item["collection"]

        chunks = chunker.chunk(doc)

        for i,chunk in enumerate(chunks):

            metadata = build_metadata(
                chunk=chunk,
                access_roles=ROLE_ACCESS.get(collection, ["all"]),
                collection=collection,
                source_document=filename,
            )

            all_chunks.append({
                "text": chunk.text,
                "metadata": metadata,
            })

    # Merge CSV chunks with document chunks
    all_chunks.extend(csv_chunks)

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
) -> tuple[str, List[str], List[str]]:
    query_vector = embedder.encode(query).tolist()

    def _query(collection: str | None = None, collections: List[str] | None = None):
        conditions = [
            FieldCondition(
                key="access_roles",
                match=MatchValue(value=role),
            )
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

    for i, point in enumerate(results.points, 1):
        payload = point.payload

        parts.append(
            f"[Source {i} | {payload.get('source_document')} | Page {payload.get('page_number')}]\n"
            f"{payload.get('text')}"
        )

        citations.append(
            f"[Source {i} | {payload.get('source_document')} | Page {payload.get('page_number')}]"
        )

    context = "\n\n".join(parts)
    return context, parts, citations

def collection_exists(client:QdrantClient)->bool:
    collections = client.get_collections().collections
    return any(c.name == COLLECTION_NAME for c in collections)

# -------------------------------
# Main RAG Pipeline
# -------------------------------
@traceable(name="RAG Answer Pipeline")
def answer(query:str, stream:str, role:str)->Dict[str, list[str]]:
    
    client = get_qdrant_client()

    embedder = SentenceTransformer(SENTENCE_TRANSFORMER_LLM)

    if not collection_exists(client):
        #chunks = load_documents_chunker(stream)
        print("Collection does not exist, creating new collection...")
        chunks = load_documents_chunker()
        collect_all_chunks_qdrant(chunks, client, embedder)

    # ----- DIVERT: For HR route, try pandas computation first -----
    csv_computed_context = None
    if stream == "hr":
        csv_files = get_csv_files_for_collection(DATA_ROOT, "hr")
        for csv_path in csv_files:
            success, result = try_csv_computation(query, csv_path)
            if success:
                csv_computed_context = result
                print(f"[answer] CSV computation succeeded: {result}")
                break
    # ----- END DIVERT -----

    context, context_chunks, citations = retrieve_and_context(
        query, role, client, embedder, stream
    )

    if not context.strip() and not csv_computed_context:
        print(f"[answer] No retrieved context for role={role}, stream={stream}")
        return NO_CONTEXT_MESSAGE, context_chunks

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

        # Skip output guardrails for CSV-computed answers
        # (grounding/citation checks are designed for document-based retrieval, not computed data)
        final_response = response.choices[0].message.content

        # Add CSV-specific citation
        final_response += "\n\n## 引用来源\n\n"
        final_response += "- `[Source: hr_data.csv (computed from database)]`\n"
        for citation in citations:
            final_response += f"- `{citation}`\n"

        print('final_response: ', final_response)
        return final_response, context_chunks

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

    return final_response, context_chunks