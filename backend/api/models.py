"""
API models for Secure Corporate RAG Assistant
Pydantic models for request/response
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# Authentication models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    level: str = "L4_Staff"
    department: str = "Public"
    is_admin: bool = False


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    level: str
    department: str
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]


# Document models
class DocumentUpload(BaseModel):
    target_department: str
    access_level_required: str
    description: Optional[str] = None
    sign_document: bool = True


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    file_size: int
    file_type: str
    is_encrypted: bool
    sha256_hash: str
    is_signed: bool
    owner_department: str
    access_level_required: str
    is_verified: bool
    created_at: Optional[datetime]
    description: Optional[str]


class DocumentMetadata(BaseModel):
    doc_id: str
    original_hash: str
    encrypted: bool
    signature: Optional[str]
    verified: bool


class DocumentVerifyResponse(BaseModel):
    doc_id: str
    filename: str
    stored_hash: str
    current_hash: Optional[str]
    is_signed: bool
    is_verified: bool
    signature_valid: Optional[bool]
    integrity_check: str
    status: str


# Audit models
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str]
    ip_address: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[str]
    risk_level: str
    is_suspicious: bool
    success: bool
    error_message: Optional[str]
    timestamp: datetime


class RiskDashboard(BaseModel):
    period: str
    generated_at: str
    summary: dict
    by_action: dict
    by_risk_level: dict
    top_active_users: List[dict] = Field(default_factory=list)
    critical_events: List[dict] = Field(default_factory=list)
    recent_events: List[dict] = Field(default_factory=list)


# RBAC models
class PermissionResponse(BaseModel):
    user: dict
    permissions: dict
    restrictions: dict


class AccessCheckRequest(BaseModel):
    doc_id: str


class AccessCheckResponse(BaseModel):
    allowed: bool
    reason: str


# Generic response models
class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    success: bool = False
