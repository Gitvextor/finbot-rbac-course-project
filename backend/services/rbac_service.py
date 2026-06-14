"""
RBAC service for Secure Corporate RAG Assistant
Role-Based Access Control for departments and levels
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import PERMISSION_MATRIX, LEVEL_HIERARCHY
from models import User, Document, UserLevel, Department
from models.audit_log import AuditLog, AuditAction


class RBACService:
    """Role-Based Access Control service"""
    
    # Level display names
    LEVEL_NAMES = {
        "L1_Executive": "公司高管",
        "L2_Director": "部门总监",
        "L3_Manager": "部门经理",
        "L4_Staff": "普通员工"
    }
    
    # Department display names
    DEPARTMENT_NAMES = {
        "Executive": "执行部门",
        "HR": "人力资源部",
        "Finance": "财务部",
        "IT": "信息技术部",
        "Sales": "销售部",
        "R&D": "研发部",
        "Legal": "法务部",
        "Public": "公共部门"
    }
    
    @staticmethod
    def check_document_access(user: User, document: Document) -> Tuple[bool, str]:
        """
        Check if user can access document
        
        Returns:
            Tuple of (allowed, reason)
        """
        # Admin has full access
        if user.is_admin:
            return True, "Admin access granted"
        
        # Executive has full access
        if user.level == "L1_Executive":
            return True, "Executive access granted"
        
        # Check department access
        user_dept_key = (user.level, user.department)
        if user_dept_key not in PERMISSION_MATRIX:
            return False, f"No permission entry for {user.level} in {user.department}"
        
        allowed_departments = PERMISSION_MATRIX[user_dept_key]
        
        if document.target_department not in allowed_departments:
            return False, (
                f"Access denied: {document.target_department} department documents "
                f"not accessible to {user.level} level in {user.department} department"
            )
        
        # Check level hierarchy
        user_priority = LEVEL_HIERARCHY.get(user.level, 999)
        doc_priority = LEVEL_HIERARCHY.get(document.access_level_required, 0)
        
        # Note: Smaller number = higher privilege
        if user_priority > doc_priority:
            return False, (
                f"Access denied: {document.access_level_required} level or higher required, "
                f"but user is {user.level} level"
            )
        
        return True, "Access granted"
    
    @staticmethod
    def get_accessible_departments(user: User) -> List[str]:
        """Get list of departments user can access"""
        user_dept_key = (user.level, user.department)
        return PERMISSION_MATRIX.get(user_dept_key, [])
    
    @staticmethod
    def get_accessible_levels(user: User) -> List[str]:
        """Get list of levels user can access documents from"""
        user_priority = LEVEL_HIERARCHY.get(user.level, 999)
        
        accessible = []
        for level, priority in LEVEL_HIERARCHY.items():
            if priority >= user_priority:
                accessible.append(level)
        
        return accessible
    
    @staticmethod
    def can_upload_to_department(user: User, department: str) -> bool:
        """Check if user can upload documents to target department"""
        # Everyone can contribute to the public / general collection
        if department == "Public":
            return True

        # Only admin and executive can upload to any department
        if user.is_admin or user.level == "L1_Executive":
            return True
        
        # Directors can upload to their own department
        if user.level == "L2_Director":
            return user.department == department
        
        # Managers can upload to their own department
        if user.level == "L3_Manager":
            return user.department == department
        
        return False
    
    @staticmethod
    def can_delete_document(user: User, document: Document) -> bool:
        """Executives/admins may delete any document; managers only their department."""
        if user.is_admin or user.level == "L1_Executive":
            return True
        if user.level == "L3_Manager":
            return document.target_department == user.department
        return False
    
    @staticmethod
    def can_sign_documents(user: User) -> bool:
        """Check if user can sign documents"""
        if user.is_admin:
            return True
        if user.level in ["L1_Executive", "L2_Director"]:
            return True
        return False
    
    @staticmethod
    def can_manage_users(user: User) -> bool:
        """Check if user can manage other users"""
        return user.is_admin or user.level == "L1_Executive"
    
    @staticmethod
    def can_view_audit_logs(user: User) -> bool:
        """Check if user can view audit logs"""
        if user.is_admin:
            return True
        if user.level in ["L1_Executive", "L2_Director"]:
            return True
        return False
    
    @staticmethod
    def _uploadable_departments(user: User) -> List[str]:
        """Departments the user may upload documents to."""
        departments = ["Public"]
        if user.is_admin or user.level == "L1_Executive":
            return list(RBACService.DEPARTMENT_NAMES.keys())
        if user.level in ["L2_Director", "L3_Manager"] and user.department not in departments:
            departments.append(user.department)
        return departments

    @staticmethod
    def get_permission_matrix_for_user(user: User) -> dict:
        """Get human-readable permission summary for user"""
        return {
            "user": {
                "username": user.username,
                "level": user.level,
                "level_name": RBACService.LEVEL_NAMES.get(user.level, user.level),
                "department": user.department,
                "department_name": RBACService.DEPARTMENT_NAMES.get(user.department, user.department)
            },
            "permissions": {
                "can_access_departments": RBACService.get_accessible_departments(user),
                "can_upload_to": RBACService._uploadable_departments(user),
                "can_delete_documents": (
                    "all"
                    if user.is_admin or user.level == "L1_Executive"
                    else user.department
                    if user.level == "L3_Manager"
                    else "none"
                ),
                "can_sign_documents": RBACService.can_sign_documents(user),
                "can_manage_users": RBACService.can_manage_users(user),
                "can_view_audit_logs": RBACService.can_view_audit_logs(user)
            },
            "restrictions": {
                "cannot_access_departments": [
                    dept for dept in RBACService.DEPARTMENT_NAMES.keys()
                    if dept not in RBACService.get_accessible_departments(user)
                ]
            }
        }
    
    @staticmethod
    def log_access_attempt(
        db: Session,
        user: User,
        document: Document,
        granted: bool,
        reason: str = None
    ):
        """Log access attempt for audit"""
        action = AuditAction.ACCESS_GRANTED.value if granted else AuditAction.ACCESS_DENIED.value
        
        log = AuditLog(
            user_id=user.id,
            username=user.username,
            action=action,
            resource_type="document",
            resource_id=document.doc_id,
            details=reason,
            success=1 if granted else 0,
            is_suspicious=0 if granted else 1
        )
        db.add(log)
        db.commit()
    
    @staticmethod
    def validate_access_level(level: str) -> bool:
        """Validate if level is valid"""
        return level in LEVEL_HIERARCHY
    
    @staticmethod
    def validate_department(department: str) -> bool:
        """Validate if department is valid"""
        return department in RBACService.DEPARTMENT_NAMES
    
    @staticmethod
    def get_level_description(level: str) -> str:
        """Get human-readable description of level"""
        descriptions = {
            "L1_Executive": "公司高管：可访问所有部门的所有文档",
            "L2_Director": "部门总监：可访问本部门及公共文档",
            "L3_Manager": "部门经理：可访问本部门核心文档及公共文档",
            "L4_Staff": "普通员工：仅可访问公共文档"
        }
        return descriptions.get(level, level)
    
    @staticmethod
    def get_department_description(department: str) -> str:
        """Get human-readable description of department"""
        return RBACService.DEPARTMENT_NAMES.get(department, department)
