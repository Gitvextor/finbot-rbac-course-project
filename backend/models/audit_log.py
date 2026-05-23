"""
Audit log model for Secure Corporate RAG Assistant
Security event tracking and logging
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .user import Base
from datetime import datetime
import enum


class AuditAction(str, enum.Enum):
    """Types of auditable actions"""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    
    # Document actions
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_SIGN = "document_sign"
    DOCUMENT_VERIFY = "document_verify"
    
    # Access control
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHECK = "permission_check"
    
    # Security events
    PROMPT_INJECTION_BLOCKED = "prompt_injection_blocked"
    TAMPERING_DETECTED = "tampering_detected"
    SIGNATURE_INVALID = "signature_invalid"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    
    # Admin actions
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    ROLE_CHANGE = "role_change"


class RiskLevel(str, enum.Enum):
    """Risk levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLog(Base):
    """Audit log model for security tracking"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Who
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(255), nullable=True)
    
    # What
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=True)  # document, user, system
    resource_id = Column(String(50), nullable=True)
    
    # Details
    details = Column(Text, nullable=True)  # JSON string with event details
    
    # Risk assessment
    risk_level = Column(String(20), default=RiskLevel.LOW.value)
    is_suspicious = Column(Integer, default=0)  # 0 = normal, 1 = suspicious
    
    # Result
    success = Column(Integer, default=1)  # 1 = success, 0 = failure
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", backref="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.timestamp}: {self.action} by {self.username}>"
    
    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "ip_address": self.ip_address,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "risk_level": self.risk_level,
            "is_suspicious": bool(self.is_suspicious),
            "success": bool(self.success),
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @staticmethod
    def calculate_risk_level(action: str, success: bool) -> RiskLevel:
        """Calculate risk level based on action and outcome"""
        high_risk_actions = {
            AuditAction.UNAUTHORIZED_ACCESS,
            AuditAction.PROMPT_INJECTION_BLOCKED,
            AuditAction.TAMPERING_DETECTED,
            AuditAction.SIGNATURE_INVALID,
            AuditAction.ACCESS_DENIED,
            AuditAction.LOGIN_FAILED
        }
        
        medium_risk_actions = {
            AuditAction.DOCUMENT_UPLOAD,
            AuditAction.DOCUMENT_DELETE,
            AuditAction.USER_CREATE,
            AuditAction.USER_DELETE,
            AuditAction.ROLE_CHANGE
        }
        
        if action in high_risk_actions:
            return RiskLevel.CRITICAL if not success else RiskLevel.HIGH
        elif action in medium_risk_actions:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
