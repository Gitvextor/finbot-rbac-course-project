"""
Audit API routes for Secure Corporate RAG Assistant
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
from services import AuditService, get_current_active_user, require_admin
from models import User
from .models import AuditLogResponse, RiskDashboard


router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    risk_level: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get recent audit logs
    
    Requires audit log viewing permission (admin or director+)
    """
    if not current_user.is_admin and current_user.level not in ["L1_Executive", "L2_Director"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view audit logs"
        )
    
    logs = AuditService.get_recent_events(
        db=db,
        limit=limit,
        risk_level=risk_level,
        action_type=action
    )
    
    return [log.to_dict() for log in logs]


@router.get("/user/{user_id}", response_model=List[AuditLogResponse])
def get_user_activity(
    user_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get activity logs for specific user"""
    # Users can only view their own logs unless admin
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view other user's logs"
        )
    
    logs = AuditService.get_user_activity(db=db, user_id=user_id, limit=limit)
    return [log.to_dict() for log in logs]


@router.get("/suspicious", response_model=List[AuditLogResponse])
def get_suspicious_events(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get suspicious security events"""
    logs = AuditService.get_suspicious_events(db=db, hours=hours, limit=limit)
    return [log.to_dict() for log in logs]


@router.get("/dashboard", response_model=RiskDashboard)
def get_risk_dashboard(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get risk dashboard statistics
    
    Returns summary of security events, risk levels, and critical incidents
    """
    dashboard = AuditService.get_risk_dashboard(db=db, hours=hours)
    return dashboard


@router.get("/access-stats")
def get_access_stats(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get access denied and security event statistics"""
    stats = AuditService.get_access_denied_stats(db=db, hours=hours)
    return stats


@router.get("/document/{doc_id}", response_model=List[AuditLogResponse])
def get_document_history(
    doc_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get access history for specific document"""
    # Check if user has permission to view this document's history
    if not current_user.is_admin and current_user.level not in ["L1_Executive", "L2_Director"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view document history"
        )
    
    logs = AuditService.get_document_access_history(db=db, doc_id=doc_id, limit=limit)
    return [log.to_dict() for log in logs]


@router.get("/search", response_model=List[AuditLogResponse])
def search_logs(
    query: Optional[str] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Search audit logs with filters"""
    logs = AuditService.search_logs(
        db=db,
        query_text=query,
        user_id=user_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return [log.to_dict() for log in logs]
