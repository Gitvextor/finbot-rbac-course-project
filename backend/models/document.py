"""
Document model for Secure Corporate RAG Assistant
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from .user import Base
from datetime import datetime


class Document(Base):
    """Document model"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String(50), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    
    # File info
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt, etc.
    
    # Encryption info
    is_encrypted = Column(Boolean, default=True)
    encryption_salt = Column(String(50), nullable=True)
    encryption_nonce = Column(String(50), nullable=True)
    encryption_tag = Column(String(50), nullable=True)
    
    # Integrity info
    sha256_hash = Column(String(64), nullable=False, index=True)
    manifest_hash = Column(String(64), nullable=True)
    
    # Signature info
    is_signed = Column(Boolean, default=False)
    signature = Column(Text, nullable=True)
    signed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    signed_at = Column(DateTime, nullable=True)
    
    # RBAC fields
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_department = Column(String(20), nullable=False)  # Which department this doc belongs to
    access_level_required = Column(String(20), nullable=False)  # Min level to access
    is_verified = Column(Boolean, default=False)  # Signature verified
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(Text, nullable=True)
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], backref="documents")
    signer = relationship("User", foreign_keys=[signed_by], backref="signed_documents")
    
    def __repr__(self):
        return f"<Document {self.doc_id}: {self.original_filename}>"
    
    def to_dict(self, include_signature=False):
        """Convert document to dictionary"""
        result = {
            "id": self.id,
            "doc_id": self.doc_id,
            "filename": self.original_filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "is_encrypted": self.is_encrypted,
            "sha256_hash": self.sha256_hash,
            "is_signed": self.is_signed,
            "owner_department": self.target_department,
            "access_level_required": self.access_level_required,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "description": self.description
        }
        
        if include_signature and self.is_signed:
            result["signature"] = self.signature
            result["signed_by"] = self.signer.username if self.signer else None
            result["signed_at"] = self.signed_at.isoformat() if self.signed_at else None
        
        return result
    
    def is_accessible_by_level(self, user_level: str, level_hierarchy: dict) -> bool:
        """Check if user level can access this document"""
        user_priority = level_hierarchy.get(user_level, 999)
        doc_priority = level_hierarchy.get(self.access_level_required, 0)
        return user_priority <= doc_priority
