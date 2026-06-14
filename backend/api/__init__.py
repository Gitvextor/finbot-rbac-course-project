"""
API module initialization
"""

from .auth import router as auth_router
from .documents import router as documents_router
from .audit import router as audit_router
from .rbac import router as rbac_router
from .demo import router as demo_router
from .rag_admin import router as rag_admin_router

__all__ = [
    'auth_router',
    'documents_router',
    'audit_router',
    'rbac_router',
    'demo_router',
    'rag_admin_router',
]
