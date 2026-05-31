"""
RBAC API routes for Secure Corporate RAG Assistant
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
from services import RBACService, get_current_active_user
from models import User
from .models import PermissionResponse


router = APIRouter(prefix="/api/rbac", tags=["RBAC"])


@router.get("/permissions", response_model=PermissionResponse)
def get_my_permissions(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's permissions"""
    return RBACService.get_permission_matrix_for_user(current_user)


@router.get("/levels")
def get_available_levels():
    """Get all available user levels"""
    levels = [
        {
            "code": "L1_Executive",
            "name": "公司高管",
            "description": "可访问所有部门的所有文档"
        },
        {
            "code": "L2_Director",
            "name": "部门总监",
            "description": "可访问本部门及公共文档"
        },
        {
            "code": "L3_Manager",
            "name": "部门经理",
            "description": "可访问本部门核心文档及公共文档"
        },
        {
            "code": "L4_Staff",
            "name": "普通员工",
            "description": "仅可访问公共文档"
        }
    ]
    return {"levels": levels}


@router.get("/departments")
def get_available_departments():
    """Get all available departments"""
    departments = [
        {"code": "Executive", "name": "执行部门"},
        {"code": "HR", "name": "人力资源部"},
        {"code": "Finance", "name": "财务部"},
        {"code": "IT", "name": "信息技术部"},
        {"code": "Sales", "name": "销售部"},
        {"code": "R&D", "name": "研发部"},
        {"code": "Legal", "name": "法务部"},
        {"code": "Public", "name": "公共部门"}
    ]
    return {"departments": departments}


@router.get("/departments/{department}/accessible")
def get_department_access_info(
    department: str,
    current_user: User = Depends(get_current_active_user)
):
    """Check what departments current user can access"""
    accessible = RBACService.get_accessible_departments(current_user)
    
    return {
        "user_level": current_user.level,
        "user_department": current_user.department,
        "can_access": department in accessible,
        "accessible_departments": accessible
    }


@router.get("/can-upload/{department}")
def check_upload_permission(
    department: str,
    current_user: User = Depends(get_current_active_user)
):
    """Check if current user can upload to target department"""
    can_upload = RBACService.can_upload_to_department(current_user, department)
    
    return {
        "can_upload": can_upload,
        "user_level": current_user.level,
        "user_department": current_user.department,
        "target_department": department
    }


@router.get("/can-sign")
def check_sign_permission(
    current_user: User = Depends(get_current_active_user)
):
    """Check if current user can sign documents"""
    return {
        "can_sign": RBACService.can_sign_documents(current_user),
        "user_level": current_user.level,
        "is_admin": current_user.is_admin
    }


@router.get("/can-manage-users")
def check_manage_users_permission(
    current_user: User = Depends(get_current_active_user)
):
    """Check if current user can manage other users"""
    return {
        "can_manage": RBACService.can_manage_users(current_user),
        "user_level": current_user.level,
        "is_admin": current_user.is_admin
    }
