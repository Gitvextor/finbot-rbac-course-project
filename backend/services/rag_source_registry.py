"""
Bridge member-A document security records with member-B RAG ingestion.

Ensures files under data/ are registered in the encrypted document store,
signed, and expose verification metadata for Qdrant chunks and /api/chat.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Document, User
from security.hash_utils import HashUtils
from services.auth_service import AuthService
from services.document_service import DocumentService

COLLECTION_DEPARTMENT = {
    "engineering": ("R&D", "L3_Manager"),
    "finance": ("Finance", "L3_Manager"),
    "hr": ("HR", "L3_Manager"),
    "marketing": ("Sales", "L3_Manager"),
    "general": ("Public", "L4_Staff"),
}

DEFAULT_SYNC_OWNER = "ceo"


class RAGSourceRegistry:
    """Sync RAG corpus files with member-A Document records and verification."""

    def __init__(self) -> None:
        self.doc_service = DocumentService()

    def _get_sync_owner(self, db: Session) -> User:
        owner = db.query(User).filter(User.username == DEFAULT_SYNC_OWNER).first()
        if owner:
            return owner

        owner = db.query(User).filter(User.is_admin.is_(True)).first()
        if owner:
            return owner

        owner, _ = AuthService.register_user(
            db=db,
            username=DEFAULT_SYNC_OWNER,
            email="ceo@company.com",
            password="password123",
            level="L1_Executive",
            department="Executive",
            is_admin=True,
        )
        return owner

    def sync_data_file(
        self,
        db: Session,
        file_path: Path,
        collection: str,
    ) -> Optional[Document]:
        """Register or refresh a data/ file in the encrypted document store."""
        if not file_path.is_file():
            return None

        filename = file_path.name
        content = file_path.read_bytes()
        file_hash = HashUtils.sha256_file(content)
        owner = self._get_sync_owner(db)
        dept, level = COLLECTION_DEPARTMENT.get(collection, ("Public", "L4_Staff"))

        existing = (
            db.query(Document)
            .filter(Document.original_filename == filename)
            .first()
        )

        if existing:
            if existing.sha256_hash != file_hash:
                existing.is_verified = False
                db.commit()
                db.refresh(existing)
                return existing

            if not existing.is_signed:
                try:
                    self.doc_service.sign_document(
                        db=db,
                        doc_id=existing.doc_id,
                        signer=owner,
                        force=False,
                    )
                    db.refresh(existing)
                except (PermissionError, ValueError):
                    pass

            self.doc_service.verify_document_integrity(db=db, doc_id=existing.doc_id)
            db.refresh(existing)
            return existing

        document, _ = self.doc_service.upload_document(
            db=db,
            file_content=content,
            filename=filename,
            owner=owner,
            target_department=dept,
            access_level_required=level,
            description=f"RAG corpus: {collection}/{filename}",
            sign_document=True,
        )
        return document

    def verification_from_document(self, db: Session, doc: Document) -> Dict[str, Any]:
        """Build chunk metadata fields from a Document record."""
        result = self.doc_service.verify_document_integrity(db=db, doc_id=doc.doc_id)
        signature_valid = result.get("signature_valid") is True
        integrity_valid = result.get("integrity_check") == "valid"
        is_verified = bool(doc.is_verified and integrity_valid and signature_valid)

        return {
            "doc_id": doc.doc_id,
            "document_hash": doc.sha256_hash,
            "is_verified": is_verified,
            "signature_valid": signature_valid,
        }

    def get_verification_metadata(
        self,
        db: Session,
        filename: str,
        *,
        sync_path: Optional[Path] = None,
        collection: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return verification metadata for a RAG source filename."""
        doc = (
            db.query(Document)
            .filter(Document.original_filename == filename)
            .first()
        )

        if doc is None and sync_path is not None and collection is not None:
            doc = self.sync_data_file(db, sync_path, collection)

        if doc is None:
            return {
                "doc_id": None,
                "document_hash": None,
                "is_verified": False,
                "signature_valid": False,
            }

        return self.verification_from_document(db, doc)

    def sync_collection(self, db: Session, data_root: Path, collection: str) -> None:
        """Sync all supported files in a collection directory."""
        folder = data_root / collection
        if not folder.exists():
            return

        supported = {".pdf", ".docx", ".md", ".csv"}
        for file_path in sorted(folder.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in supported:
                self.sync_data_file(db, file_path, collection)

    def verify_doc_for_citation(self, doc_id: str) -> Dict[str, Any]:
        """Re-verify a document before returning it as a chat source."""
        db = SessionLocal()
        try:
            result = self.doc_service.verify_document_integrity(db=db, doc_id=doc_id)
            verified = (
                result.get("integrity_check") == "valid"
                and result.get("signature_valid") is True
            )
            return {
                "doc_id": doc_id,
                "document_hash": result.get("stored_hash"),
                "signature_valid": result.get("signature_valid"),
                "verified": verified,
                "integrity_check": result.get("integrity_check"),
            }
        finally:
            db.close()

    def build_verified_sources(self, source_metas: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Re-verify unique doc_ids and shape /api/chat source payloads."""
        verified_by_doc: Dict[str, Dict[str, Any]] = {}
        output: list[Dict[str, Any]] = []

        for meta in source_metas:
            doc_id = meta.get("doc_id")
            if doc_id and doc_id not in verified_by_doc:
                verified_by_doc[doc_id] = self.verify_doc_for_citation(doc_id)

            verification = verified_by_doc.get(doc_id or "", {})
            verified = bool(verification.get("verified")) if doc_id else False

            output.append(
                {
                    "source": meta.get("source"),
                    "doc_id": doc_id,
                    "document_hash": verification.get("document_hash") or meta.get("document_hash"),
                    "signature_valid": verification.get("signature_valid", meta.get("signature_valid")),
                    "verified": verified,
                }
            )

        return output
