"""
Document service for Secure Corporate RAG Assistant
Document encryption, upload, and integrity verification
"""

import os
import uuid
import json
from typing import Optional, Tuple, List
from datetime import datetime
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DOCUMENTS_DIR, KEYS_DIR, RSA_PRIVATE_KEY_FILE, RSA_PUBLIC_KEY_FILE, PERMISSION_MATRIX, LEVEL_HIERARCHY
from models import User, Document, AuditLog, AuditAction, RiskLevel
from security import (
    CryptoUtils, HashUtils, SignatureUtils, 
    ensure_keypair_exists, sign_document_package, 
    verify_document_package, compute_file_integrity_hash
)


class DocumentService:
    """Document management service with encryption and verification"""
    
    def __init__(self):
        """Initialize document service"""
        # Ensure keypair exists
        self.private_key, self.public_key = ensure_keypair_exists(
            str(RSA_PRIVATE_KEY_FILE),
            str(RSA_PUBLIC_KEY_FILE)
        )
    
    def upload_document(
        self,
        db: Session,
        file_content: bytes,
        filename: str,
        owner: User,
        target_department: str,
        access_level_required: str,
        description: str = None,
        sign_document: bool = True
    ) -> Tuple[Document, dict]:
        """
        Upload and encrypt document
        
        Args:
            db: Database session
            file_content: Raw file bytes
            filename: Original filename
            owner: User uploading the document
            target_department: Which department this document belongs to
            access_level_required: Minimum level required to access
            description: Optional description
            sign_document: Whether to sign the document
            
        Returns:
            Tuple of (Document object, metadata)
        """
        # Generate document ID
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        # Calculate file hash before encryption
        file_hash = HashUtils.sha256_file(file_content)
        
        # Encrypt file content
        encrypted_package = CryptoUtils.encrypt_file(file_content, doc_id)
        
        # Save encrypted file
        encrypted_filepath = DOCUMENTS_DIR / f"{doc_id}.enc"
        CryptoUtils.save_encrypted_package(encrypted_package, str(encrypted_filepath))
        
        # Determine file type
        file_ext = Path(filename).suffix.lower().lstrip('.')
        file_type_map = {
            'pdf': 'pdf', 'docx': 'docx', 'doc': 'doc',
            'txt': 'txt', 'md': 'md', 'csv': 'csv',
            'xlsx': 'xlsx', 'xls': 'xls', 'pptx': 'pptx'
        }
        file_type = file_type_map.get(file_ext, 'unknown')
        
        # Create document record
        document = Document(
            doc_id=doc_id,
            filename=f"{doc_id}.enc",
            original_filename=filename,
            file_size=len(file_content),
            file_type=file_type,
            is_encrypted=True,
            encryption_salt=encrypted_package["salt"],
            encryption_nonce=encrypted_package["nonce"],
            encryption_tag=encrypted_package["tag"],
            sha256_hash=file_hash,
            owner_id=owner.id,
            target_department=target_department,
            access_level_required=access_level_required,
            description=description
        )
        
        # Sign document if requested
        if sign_document:
            try:
                signature_package = sign_document_package(doc_id, file_hash, self.private_key)
                document.is_signed = True
                document.signature = signature_package["signature"]
                document.signed_by = owner.id
                document.signed_at = datetime.utcnow()
                document.is_verified = True
            except Exception as e:
                print(f"[DocumentService] Signing failed for {doc_id}: {e}")
        
        db.add(document)
        
        # Audit log
        audit_log = AuditLog(
            user_id=owner.id,
            username=owner.username,
            action=AuditAction.DOCUMENT_UPLOAD.value,
            resource_type="document",
            resource_id=doc_id,
            details=json.dumps({
                "filename": filename,
                "department": target_department,
                "level_required": access_level_required,
                "size": len(file_content)
            })
        )
        db.add(audit_log)
        db.commit()
        db.refresh(document)
        
        # Return metadata
        metadata = {
            "doc_id": doc_id,
            "original_hash": file_hash,
            "encrypted": True,
            "signature": document.signature if document.is_signed else None,
            "verified": document.is_verified
        }
        
        return document, metadata
    
    def download_document(
        self,
        db: Session,
        doc_id: str,
        user: User,
        ip_address: str = None
    ) -> Tuple[bytes, Document]:
        """
        Download and decrypt document
        
        Returns:
            Tuple of (decrypted file content, Document object)
        """
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not document:
            raise ValueError("Document not found")
        
        # Check permissions
        self._check_access_permission(user, document)
        
        # Load encrypted file
        encrypted_filepath = DOCUMENTS_DIR / document.filename
        if not encrypted_filepath.exists():
            raise FileNotFoundError("Encrypted file not found")
        
        encrypted_package = CryptoUtils.load_encrypted_package(str(encrypted_filepath))
        
        # Decrypt file
        file_content = CryptoUtils.decrypt_file(encrypted_package, doc_id)
        
        # Verify integrity
        current_hash = HashUtils.sha256_file(file_content)
        if current_hash != document.sha256_hash:
            # Log tampering attempt
            audit_log = AuditLog(
                user_id=user.id,
                username=user.username,
                action=AuditAction.TAMPERING_DETECTED.value,
                resource_type="document",
                resource_id=doc_id,
                risk_level=RiskLevel.CRITICAL.value,
                success=0,
                details=json.dumps({
                    "expected_hash": document.sha256_hash,
                    "actual_hash": current_hash
                })
            )
            db.add(audit_log)
            db.commit()
            raise ValueError("Document integrity check failed - possible tampering detected")
        
        # Audit log
        audit_log = AuditLog(
            user_id=user.id,
            username=user.username,
            action=AuditAction.DOCUMENT_DOWNLOAD.value,
            resource_type="document",
            resource_id=doc_id,
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
        
        return file_content, document

    def read_decrypted_content_for_rag(
        self,
        db: Session,
        doc_id: str,
    ) -> Tuple[bytes, Document]:
        """
        Decrypt document content for RAG ingestion.

        Skips user RBAC checks but enforces integrity verification.
        """
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not document:
            raise ValueError("Document not found")

        encrypted_filepath = DOCUMENTS_DIR / document.filename
        if not encrypted_filepath.exists():
            raise FileNotFoundError(f"Encrypted file not found: {encrypted_filepath}")

        encrypted_package = CryptoUtils.load_encrypted_package(str(encrypted_filepath))
        file_content = CryptoUtils.decrypt_file(encrypted_package, doc_id)

        current_hash = HashUtils.sha256_file(file_content)
        if current_hash != document.sha256_hash:
            raise ValueError(
                f"Document integrity check failed for {doc_id} — possible tampering"
            )

        return file_content, document
    
    def verify_document_integrity(
        self,
        db: Session,
        doc_id: str,
        user: User = None
    ) -> dict:
        """
        Verify document integrity and signature
        
        Returns:
            Verification result dictionary
        """
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not document:
            raise ValueError("Document not found")
        
        result = {
            "doc_id": doc_id,
            "filename": document.original_filename,
            "stored_hash": document.sha256_hash,
            "is_signed": document.is_signed,
            "is_verified": document.is_verified,
            "integrity_check": "pending"
        }
        
        # Load encrypted file to verify
        encrypted_filepath = DOCUMENTS_DIR / document.filename
        if not encrypted_filepath.exists():
            result["integrity_check"] = "file_missing"
            result["status"] = "error"
            return result
        
        encrypted_package = CryptoUtils.load_encrypted_package(str(encrypted_filepath))
        
        # Decrypt and hash
        try:
            file_content = CryptoUtils.decrypt_file(encrypted_package, doc_id)
            current_hash = HashUtils.sha256_file(file_content)
            
            if current_hash == document.sha256_hash:
                result["integrity_check"] = "valid"
                result["current_hash"] = current_hash
                result["status"] = "ok"
            else:
                result["integrity_check"] = "hash_mismatch"
                result["current_hash"] = current_hash
                result["status"] = "warning"
        except Exception as e:
            result["integrity_check"] = "decryption_failed"
            result["status"] = "error"
            result["error"] = str(e)
        
        # Verify signature if present
        if document.is_signed and document.signature:
            signature_package = {
                "doc_id": document.doc_id,
                "original_hash": document.sha256_hash,
                "signature": document.signature
            }
            verification = verify_document_package(signature_package, self.public_key)
            result["signature_valid"] = verification["is_valid"]
            
            if not verification["is_valid"]:
                result["status"] = "warning"
                document.is_verified = False
                db.commit()
        else:
            result["signature_valid"] = None
        
        # Audit log
        if user:
            audit_log = AuditLog(
                user_id=user.id,
                username=user.username,
                action=AuditAction.DOCUMENT_VERIFY.value,
                resource_type="document",
                resource_id=doc_id,
                details=json.dumps(result)
            )
            db.add(audit_log)
            db.commit()
        
        return result
    
    def sign_document(
        self,
        db: Session,
        doc_id: str,
        signer: User,
        force: bool = False
    ) -> Document:
        """
        Sign a document with RSA signature
        
        Args:
            db: Database session
            doc_id: Document ID
            signer: User signing the document
            force: Force re-sign even if already signed
            
        Returns:
            Updated Document object
        """
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not document:
            raise ValueError("Document not found")
        
        if document.is_signed and not force:
            raise ValueError("Document already signed")
        
        # Only admins or executives can sign documents
        if not signer.is_admin and signer.level not in ["L1_Executive", "L2_Director"]:
            raise PermissionError("Insufficient privileges to sign documents")
        
        # Create signature
        signature_package = sign_document_package(
            document.doc_id,
            document.sha256_hash,
            self.private_key
        )
        
        document.is_signed = True
        document.signature = signature_package["signature"]
        document.signed_by = signer.id
        document.signed_at = datetime.utcnow()
        document.is_verified = True
        
        # Audit log
        audit_log = AuditLog(
            user_id=signer.id,
            username=signer.username,
            action=AuditAction.DOCUMENT_SIGN.value,
            resource_type="document",
            resource_id=doc_id
        )
        db.add(audit_log)
        db.commit()
        db.refresh(document)
        
        return document
    
    def _check_access_permission(self, user: User, document: Document) -> bool:
        """
        Check if user has access to document
        
        Returns:
            True if access allowed
            
        Raises:
            PermissionError if access denied
        """
        # Admin can access everything
        if user.is_admin:
            return True
        
        # Executive can access everything
        if user.level == "L1_Executive":
            return True
        
        # Check department access
        user_dept_key = (user.level, user.department)
        if user_dept_key in PERMISSION_MATRIX:
            allowed_depts = PERMISSION_MATRIX[user_dept_key]
            if document.target_department not in allowed_depts:
                raise PermissionError(
                    f"Access denied: {document.target_department} department documents "
                    f"not accessible to {user.level} in {user.department}"
                )
        else:
            raise PermissionError("Access denied: no permission matrix entry")
        
        # Check level hierarchy
        user_priority = LEVEL_HIERARCHY.get(user.level, 999)
        doc_priority = LEVEL_HIERARCHY.get(document.access_level_required, 0)
        
        # Note: Lower number = higher privilege
        if user_priority > doc_priority:
            raise PermissionError(
                f"Access denied: {document.access_level_required} level required, "
                f"but user is {user.level}"
            )
        
        return True
    
    def list_accessible_documents(self, db: Session, user: User) -> List[Document]:
        """List all documents accessible by user"""
        # Get allowed departments
        user_dept_key = (user.level, user.department)
        allowed_departments = PERMISSION_MATRIX.get(user_dept_key, [])
        
        # Get user's level priority
        user_priority = LEVEL_HIERARCHY.get(user.level, 999)
        
        # Query accessible documents
        query = db.query(Document)
        
        # Filter by accessible departments
        if user.level != "L1_Executive" and not user.is_admin:
            query = query.filter(Document.target_department.in_(allowed_departments))
        
        documents = query.all()
        
        # Filter by level (in Python for flexibility)
        accessible_docs = []
        for doc in documents:
            doc_priority = LEVEL_HIERARCHY.get(doc.access_level_required, 0)
            if user_priority <= doc_priority or user.is_admin or user.level == "L1_Executive":
                accessible_docs.append(doc)
        
        return accessible_docs
    
    def delete_document(
        self,
        db: Session,
        doc_id: str,
        user: User
    ) -> bool:
        """
        Delete document
        
        Returns:
            True if deleted successfully
        """
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not document:
            raise ValueError("Document not found")
        
        # Check permissions (only owner or admin can delete)
        if document.owner_id != user.id and not user.is_admin:
            raise PermissionError("Only document owner or admin can delete")
        
        # Delete encrypted file
        encrypted_filepath = DOCUMENTS_DIR / document.filename
        if encrypted_filepath.exists():
            os.remove(encrypted_filepath)
        
        # Audit log
        audit_log = AuditLog(
            user_id=user.id,
            username=user.username,
            action=AuditAction.DOCUMENT_DELETE.value,
            resource_type="document",
            resource_id=doc_id,
            details=json.dumps({"filename": document.original_filename})
        )
        db.add(audit_log)
        
        # Delete record
        db.delete(document)
        db.commit()
        
        return True
