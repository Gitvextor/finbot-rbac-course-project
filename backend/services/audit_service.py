"""
Audit service for Secure Corporate RAG Assistant
Security event logging and risk dashboard
"""

import json
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import AUDIT_LOG_FILE, AUDIT_LOG_ENABLED
from models import AuditLog, AuditAction, RiskLevel, User


class AuditService:
    """Audit logging and reporting service"""
    
    @staticmethod
    def log_event(
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        is_suspicious: bool = False
    ) -> AuditLog:
        """
        Log a security event
        
        Returns:
            Created AuditLog object
        """
        # Calculate risk level
        risk_level = AuditLog.calculate_risk_level(action, success)
        
        # Serialize details if dict
        if details and isinstance(details, dict):
            details_str = json.dumps(details)
        else:
            details_str = details
        
        # Create audit log entry
        audit_log = AuditLog(
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details_str,
            risk_level=risk_level.value,
            is_suspicious=1 if is_suspicious else 0,
            success=1 if success else 0,
            error_message=error_message
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        # Also write to file for backup
        if AUDIT_LOG_ENABLED:
            AuditService._write_to_file(audit_log)
        
        return audit_log
    
    @staticmethod
    def _write_to_file(audit_log: AuditLog):
        """Write audit log to JSON file"""
        try:
            with open(AUDIT_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_log.to_dict(), ensure_ascii=False) + '\n')
        except Exception:
            pass  # Don't fail if file write fails
    
    @staticmethod
    def get_user_activity(
        db: Session,
        user_id: int,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[AuditLog]:
        """Get activity log for specific user"""
        query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
        
        if since:
            query = query.filter(AuditLog.timestamp >= since)
        
        return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_recent_events(
        db: Session,
        limit: int = 100,
        risk_level: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> List[AuditLog]:
        """Get recent audit events with filters"""
        query = db.query(AuditLog)
        
        if risk_level:
            query = query.filter(AuditLog.risk_level == risk_level)
        if action_type:
            query = query.filter(AuditLog.action == action_type)
        
        return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_suspicious_events(
        db: Session,
        hours: int = 24,
        limit: int = 50
    ) -> List[AuditLog]:
        """Get suspicious events in the last N hours"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return db.query(AuditLog).filter(
            AuditLog.timestamp >= since,
            (AuditLog.is_suspicious == 1) | (AuditLog.risk_level.in_([RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]))
        ).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_risk_dashboard(db: Session, hours: int = 24) -> dict:
        """
        Generate risk dashboard statistics
        
        Returns:
            Dashboard statistics dictionary
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Total events
        total_events = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= since
        ).scalar()
        
        # Events by action type
        action_counts = db.query(
            AuditLog.action,
            func.count(AuditLog.id)
        ).filter(
            AuditLog.timestamp >= since
        ).group_by(AuditLog.action).all()
        
        # Events by risk level
        risk_counts = db.query(
            AuditLog.risk_level,
            func.count(AuditLog.id)
        ).filter(
            AuditLog.timestamp >= since
        ).group_by(AuditLog.risk_level).all()
        
        # Failed events
        failed_events = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= since,
            AuditLog.success == 0
        ).scalar()
        
        # Suspicious events
        suspicious_events = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= since,
            AuditLog.is_suspicious == 1
        ).scalar()
        
        # Top active users
        top_users = db.query(
            AuditLog.username,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= since
        ).group_by(AuditLog.username).order_by(desc('count')).limit(10).all()
        
        # Recent critical events
        critical_events = db.query(AuditLog).filter(
            AuditLog.timestamp >= since,
            AuditLog.risk_level == RiskLevel.CRITICAL.value
        ).order_by(desc(AuditLog.timestamp)).limit(10).all()

        # Presentation dashboard counters
        def count_action(action: str) -> int:
            return (
                db.query(func.count(AuditLog.id))
                .filter(AuditLog.timestamp >= since, AuditLog.action == action)
                .scalar()
                or 0
            )

        attack_count = count_action(AuditAction.PROMPT_INJECTION_BLOCKED.value)
        sensitive_count = count_action(AuditAction.PII_BLOCKED.value)
        unauthorized_count = count_action(AuditAction.UNAUTHORIZED_ACCESS.value) + count_action(
            AuditAction.ACCESS_DENIED.value
        )
        tamper_count = count_action(AuditAction.TAMPERING_DETECTED.value)

        recent_events = db.query(AuditLog).filter(
            AuditLog.timestamp >= since
        ).order_by(desc(AuditLog.timestamp)).limit(12).all()
        
        return {
            "period": f"Last {hours} hours",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_events": total_events or 0,
                "failed_events": failed_events or 0,
                "suspicious_events": suspicious_events or 0,
                "critical_events": len(critical_events),
                "attack_count": attack_count,
                "sensitive_query_count": sensitive_count,
                "unauthorized_access_count": unauthorized_count,
                "tamper_detection_count": tamper_count,
            },
            "by_action": {action: count for action, count in action_counts},
            "by_risk_level": {risk: count for risk, count in risk_counts},
            "top_active_users": [{"username": u, "events": c} for u, c in top_users],
            "critical_events": [e.to_dict() for e in critical_events],
            "recent_events": [e.to_dict() for e in recent_events],
        }
    
    @staticmethod
    def get_access_denied_stats(db: Session, hours: int = 24) -> dict:
        """Get access denied statistics"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        denied_count = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= since,
            AuditLog.action == AuditAction.ACCESS_DENIED.value
        ).scalar()
        
        unauthorized_count = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= since,
            AuditLog.action == AuditAction.UNAUTHORIZED_ACCESS.value
        ).scalar()
        
        prompt_injection_count = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= since,
            AuditLog.action == AuditAction.PROMPT_INJECTION_BLOCKED.value
        ).scalar()

        pii_count = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= since,
            AuditLog.action == AuditAction.PII_BLOCKED.value
        ).scalar()
        
        tampering_count = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= since,
            AuditLog.action == AuditAction.TAMPERING_DETECTED.value
        ).scalar()
        
        return {
            "period": f"Last {hours} hours",
            "access_denied": denied_count or 0,
            "unauthorized_access": unauthorized_count or 0,
            "prompt_injection_blocked": prompt_injection_count or 0,
            "pii_blocked": pii_count or 0,
            "tampering_detected": tampering_count or 0,
            "total_security_events": (
                (denied_count or 0) + 
                (unauthorized_count or 0) + 
                (prompt_injection_count or 0) + 
                (pii_count or 0) +
                (tampering_count or 0)
            )
        }
    
    @staticmethod
    def search_logs(
        db: Session,
        query_text: Optional[str] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Search audit logs with filters"""
        q = db.query(AuditLog)
        
        if user_id:
            q = q.filter(AuditLog.user_id == user_id)
        if action:
            q = q.filter(AuditLog.action == action)
        if start_date:
            q = q.filter(AuditLog.timestamp >= start_date)
        if end_date:
            q = q.filter(AuditLog.timestamp <= end_date)
        if query_text:
            q = q.filter(AuditLog.details.contains(query_text))
        
        return q.order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_document_access_history(
        db: Session,
        doc_id: str,
        limit: int = 50
    ) -> List[AuditLog]:
        """Get access history for a specific document"""
        return db.query(AuditLog).filter(
            AuditLog.resource_type == "document",
            AuditLog.resource_id == doc_id
        ).order_by(desc(AuditLog.timestamp)).limit(limit).all()
