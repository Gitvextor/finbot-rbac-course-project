"""
Demo support APIs for member C's presentation console.

These endpoints live under /api/demo so the classroom demo can seed accounts,
show document archives, and simulate integrity events without weakening the
normal auth/document routes.
"""

from datetime import datetime, timedelta
from pathlib import Path
import json
import sys

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
from models import AuditAction, AuditLog, Document, User
from services import AuditService, AuthService, DocumentService


router = APIRouter(prefix="/api/demo", tags=["Member C Demo"])


DEMO_ACCOUNTS = [
    {
        "key": "admin",
        "label": "Admin",
        "username": "admin_demo",
        "email": "admin_demo@finbot.local",
        "password": "admin@2026",
        "level": "L1_Executive",
        "department": "Executive",
        "is_admin": True,
        "chat_role": "c_level",
        "scenario": "资料管理、归档查看、全部课程资料访问",
    },
    {
        "key": "teacher",
        "label": "Teacher",
        "username": "teacher_demo",
        "email": "teacher_demo@finbot.local",
        "password": "teacher@2026",
        "level": "L2_Director",
        "department": "R&D",
        "is_admin": False,
        "chat_role": "engineering",
        "scenario": "查看教师答案、评分标准和受限教学资料",
    },
    {
        "key": "ta",
        "label": "TA",
        "username": "ta_demo",
        "email": "ta_demo@finbot.local",
        "password": "ta@2026",
        "level": "L3_Manager",
        "department": "R&D",
        "is_admin": False,
        "chat_role": "engineering",
        "scenario": "查看评分标准、工程说明和课程归档",
    },
    {
        "key": "student",
        "label": "Student",
        "username": "student_demo",
        "email": "student_demo@finbot.local",
        "password": "student@2026",
        "level": "L4_Staff",
        "department": "Public",
        "is_admin": False,
        "chat_role": "employee",
        "scenario": "只能访问公开资料，越权请求会被拒绝",
    },
]


DEMO_DOCUMENTS = [
    {
        "filename": "course_public_syllabus.md",
        "department": "Public",
        "level": "L4_Staff",
        "description": "公开课程说明：所有角色可访问",
        "content": """# FinBot 安全 RAG 课程资料

本公开资料包含项目背景、演示流程和公开问答范围。学生可以查看该文件，但不能访问答案文件、评分标准或隐私数据。""",
    },
    {
        "filename": "teacher_answer_key.md",
        "department": "R&D",
        "level": "L2_Director",
        "description": "教师答案文件：Teacher/Admin 可访问，Student 越权失败",
        "content": """# 期末答案文件

该文件模拟教师答案与评分参考，仅 Teacher/Admin 可访问。任何 Student 角色的检索或下载都应被 RBAC 拦截。""",
    },
    {
        "filename": "grading_rubric.md",
        "department": "R&D",
        "level": "L3_Manager",
        "description": "课程评分标准：TA/Teacher/Admin 可访问，Student 不可访问",
        "content": """# 评分标准

评分重点包括 RBAC 检索层过滤、Prompt Injection 防护、PII 防护、文档签名与篡改检测、审计记录展示。""",
    },
    {
        "filename": "student_privacy_records.csv",
        "department": "HR",
        "level": "L2_Director",
        "description": "含隐私字段的学生记录：用于 PII 与权限演示",
        "content": "name,email,phone,score\nAlice,alice@example.com,5551234567,92\nBob,bob@example.com,5559876543,88\n",
    },
]


def _ensure_user(db: Session, account: dict) -> User:
    user = db.query(User).filter(User.username == account["username"]).first()
    if not user:
        user, _ = AuthService.register_user(
            db=db,
            username=account["username"],
            email=account["email"],
            password=account["password"],
            level=account["level"],
            department=account["department"],
            is_admin=account["is_admin"],
        )
        return user

    user.email = account["email"]
    user.level = account["level"]
    user.department = account["department"]
    user.is_admin = account["is_admin"]
    db.commit()
    db.refresh(user)
    return user


def _ensure_documents(db: Session, owner: User) -> list[dict]:
    doc_service = DocumentService()
    created_or_existing = []

    for item in DEMO_DOCUMENTS:
        existing = db.query(Document).filter(Document.original_filename == item["filename"]).first()
        if existing:
            existing.target_department = item["department"]
            existing.access_level_required = item["level"]
            existing.description = item["description"]
            db.commit()
            db.refresh(existing)
            created_or_existing.append(existing.to_dict())
            continue

        document, _ = doc_service.upload_document(
            db=db,
            file_content=item["content"].encode("utf-8"),
            filename=item["filename"],
            owner=owner,
            target_department=item["department"],
            access_level_required=item["level"],
            description=item["description"],
            sign_document=True,
        )
        created_or_existing.append(document.to_dict())

    return created_or_existing


@router.get("/accounts")
def get_demo_accounts():
    """Return the demo accounts shown on the member C login screen."""
    return {"accounts": DEMO_ACCOUNTS}


@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """Create or update demo accounts and encrypted/signed demo documents."""
    users = [_ensure_user(db, account) for account in DEMO_ACCOUNTS]
    admin_user = next(user for user in users if user.username == "admin_demo")
    documents = _ensure_documents(db, admin_user)

    return {
        "message": "Demo accounts and documents are ready",
        "accounts": DEMO_ACCOUNTS,
        "documents": documents,
    }


@router.get("/documents")
def list_demo_documents(db: Session = Depends(get_db)):
    """List demo document metadata without exposing decrypted content."""
    filenames = [item["filename"] for item in DEMO_DOCUMENTS]
    docs = (
        db.query(Document)
        .filter(Document.original_filename.in_(filenames))
        .order_by(Document.created_at.desc())
        .all()
    )
    return {"documents": [doc.to_dict() for doc in docs]}


@router.post("/tamper-simulation")
def simulate_tamper_detection(db: Session = Depends(get_db)):
    """Record a safe tamper-detection event without modifying encrypted files."""
    doc = db.query(Document).filter(Document.original_filename == "teacher_answer_key.md").first()

    AuditService.log_event(
        db=db,
        action=AuditAction.TAMPERING_DETECTED.value,
        username="member_c_demo",
        resource_type="document",
        resource_id=doc.doc_id if doc else "demo_missing_document",
        details=json.dumps(
            {
                "expected_hash": doc.sha256_hash if doc else None,
                "actual_hash": "SIMULATED_HASH_MISMATCH",
                "note": "Non-destructive demo event for presentation dashboard",
            },
            ensure_ascii=False,
        ),
        success=False,
        is_suspicious=True,
    )

    return {
        "blocked": True,
        "status": "tampering_detected",
        "document": doc.to_dict() if doc else None,
        "message": "已记录非破坏性文档篡改检测事件",
    }


@router.get("/risk-dashboard")
def get_demo_risk_dashboard(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """Return presentation-ready security metrics without requiring admin JWT."""
    since = datetime.utcnow() - timedelta(hours=hours)

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

    by_action = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .filter(AuditLog.timestamp >= since)
        .group_by(AuditLog.action)
        .all()
    )
    by_risk = (
        db.query(AuditLog.risk_level, func.count(AuditLog.id))
        .filter(AuditLog.timestamp >= since)
        .group_by(AuditLog.risk_level)
        .all()
    )
    recent = (
        db.query(AuditLog)
        .filter(AuditLog.timestamp >= since)
        .order_by(desc(AuditLog.timestamp))
        .limit(12)
        .all()
    )

    return {
        "period": f"Last {hours} hours",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "attack_count": attack_count,
            "sensitive_query_count": sensitive_count,
            "unauthorized_access_count": unauthorized_count,
            "tamper_detection_count": tamper_count,
            "total_events": sum(count for _, count in by_action),
        },
        "by_action": {action: count for action, count in by_action},
        "by_risk_level": {risk: count for risk, count in by_risk},
        "recent_events": [event.to_dict() for event in recent],
    }
