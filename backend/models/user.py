"""
User model for Secure Corporate RAG Assistant
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class UserLevel(str, enum.Enum):
    """User privilege levels"""
    L1_EXECUTIVE = "L1_Executive"
    L2_DIRECTOR = "L2_Director"
    L3_MANAGER = "L3_Manager"
    L4_STAFF = "L4_Staff"


class Department(str, enum.Enum):
    """Company departments"""
    EXECUTIVE = "Executive"
    HR = "HR"
    FINANCE = "Finance"
    IT = "IT"
    SALES = "Sales"
    RD = "R&D"
    LEGAL = "Legal"
    PUBLIC = "Public"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # RBAC fields
    level = Column(String(20), nullable=False, default=UserLevel.L4_STAFF.value)
    department = Column(String(20), nullable=False, default=Department.PUBLIC.value)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User {self.username} ({self.level}, {self.department})>"
    
    def can_access_department(self, target_department: str, permission_matrix: dict) -> bool:
        """Check if user can access target department based on RBAC"""
        key = (self.level, self.department)
        if key in permission_matrix:
            allowed = permission_matrix[key]
            return target_department in allowed or "Public" in allowed
        return False
    
    def get_accessible_departments(self, permission_matrix: dict) -> list:
        """Get list of departments user can access"""
        key = (self.level, self.department)
        if key in permission_matrix:
            return permission_matrix[key]
        return []
    
    def to_dict(self):
        """Convert user to dictionary (excluding password)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "level": self.level,
            "department": self.department,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
