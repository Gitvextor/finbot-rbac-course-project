"""Demo support APIs for the FinBot company RBAC console."""

from datetime import datetime, timedelta
from pathlib import Path
import json
import sys

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DOCUMENTS_DIR
from database import get_db
from models import AuditAction, AuditLog, Document, User
from services import AuditService, AuthService, DocumentService


router = APIRouter(prefix="/api/demo", tags=["Company Demo"])


DEMO_ACCOUNTS = [
    {
        "key": "executive",
        "label": "Executive",
        "username": "ceo",
        "email": "ceo@company.com",
        "password": "password123",
        "level": "L1_Executive",
        "department": "Executive",
        "is_admin": True,
        "chat_role": "c_level",
        "scenario": "全公司资料、跨部门问答、审计演示",
    },
    {
        "key": "hr",
        "label": "HR Manager",
        "username": "hr_manager",
        "email": "hr_manager@company.com",
        "password": "password123",
        "level": "L3_Manager",
        "department": "HR",
        "is_admin": False,
        "chat_role": "hr_manager",
        "scenario": "HR 员工数据、招聘与公共政策",
    },
    {
        "key": "finance",
        "label": "Finance",
        "username": "finance_manager",
        "email": "finance_manager@company.com",
        "password": "password123",
        "level": "L3_Manager",
        "department": "Finance",
        "is_admin": False,
        "chat_role": "finance",
        "scenario": "预算、报表、开支与公共资料",
    },
    {
        "key": "engineering",
        "label": "Engineering",
        "username": "rd_director",
        "email": "rd_director@company.com",
        "password": "password123",
        "level": "L2_Director",
        "department": "R&D",
        "is_admin": False,
        "chat_role": "engineering",
        "scenario": "系统架构、SLA、CI/CD 与工程资料",
    },
    {
        "key": "marketing",
        "label": "Marketing",
        "username": "marketing_manager",
        "email": "marketing_manager@company.com",
        "password": "password123",
        "level": "L3_Manager",
        "department": "Sales",
        "is_admin": False,
        "chat_role": "marketing",
        "scenario": "营销活动、获客指标与市场报告",
    },
    {
        "key": "employee",
        "label": "Employee",
        "username": "employee_demo",
        "email": "employee_demo@company.com",
        "password": "password123",
        "level": "L4_Staff",
        "department": "Public",
        "is_admin": False,
        "chat_role": "employee",
        "scenario": "仅公共资料，越权访问会被拒绝",
    },
]


DEMO_DOCUMENTS = [
    {
        "filename": "company_public_handbook.md",
        "department": "Public",
        "level": "L4_Staff",
        "description": "公司公开手册：所有角色可访问",
        "content": """# Company Public Handbook

## Company Profile
FinSolve Technologies is a B2B fintech company serving banking, insurance, and investment-management clients. The company builds secure internal platforms for financial analytics, workflow automation, and client reporting.

## Onboarding Process
New employees complete four steps during onboarding: HR document verification, IT account setup, security awareness training, and manager-led team orientation. During the first 30 days, each employee receives a buddy, reviews role expectations, and completes required compliance modules.

## Employee Benefits
Employees receive health insurance, paid annual leave, sick leave, wellness support, learning budget reimbursement, and retirement contributions where applicable. Benefits questions should be handled through HRMS or the HR helpdesk.

## Leave Policy
Annual leave requests are submitted through HRMS and require manager approval. Sick leave can be filed with supporting documentation when required. Emergency leave may be approved retroactively by the manager and HR. Unused annual leave may be carried forward according to the yearly HR policy notice.

## Work Hours and IT Usage
Standard work hours are 9:30 AM to 6:30 PM, Monday to Friday. Employees must use company devices for internal systems, enable multi-factor authentication, and avoid sharing credentials or confidential documents outside approved channels.""",
    },
    {
        "filename": "engineering_sla_report.md",
        "department": "R&D",
        "level": "L3_Manager",
        "description": "工程 SLA 与系统架构：Engineering/Executive 可访问",
        "content": """# Engineering SLA Report

工程资料包含 API uptime SLA、CI/CD 流水线、微服务架构、部署状态和 sprint metrics。""",
    },
    {
        "filename": "finance_quarterly_summary.md",
        "department": "Finance",
        "level": "L3_Manager",
        "description": "季度财务摘要：Finance/Executive 可访问",
        "content": """# Quarterly Financial Summary

财务资料包含季度收入、预算执行、费用摘要、供应商付款和财务 KPI。""",
    },
    {
        "filename": "hr_employee_records.csv",
        "department": "HR",
        "level": "L3_Manager",
        "description": "员工隐私记录：HR Manager/Executive 可访问",
        "content": "name,email,phone,department\nAlice,alice@example.com,5551234567,HR\nBob,bob@example.com,5559876543,Finance\n",
    },
    {
        "filename": "marketing_campaign_report.md",
        "department": "Sales",
        "level": "L3_Manager",
        "description": "市场活动报告：Marketing/Executive 可访问",
        "content": """# Marketing Campaign Report

市场资料包含 campaign performance、leads、cost per lead、conversion channel 和 ROI。""",
    },
]


LEGACY_DEMO_FILENAMES = [
    "course_public_syllabus.md",
    "teacher_answer_key.md",
    "grading_rubric.md",
    "student_privacy_records.csv",
]


def _cleanup_seeded_demo_documents(db: Session) -> None:
    filenames = LEGACY_DEMO_FILENAMES + [item["filename"] for item in DEMO_DOCUMENTS]
    demo_docs = db.query(Document).filter(Document.original_filename.in_(filenames)).all()
    for doc in demo_docs:
        encrypted_path = DOCUMENTS_DIR / doc.filename
        if encrypted_path.exists():
            encrypted_path.unlink()
        db.delete(doc)
    if demo_docs:
        db.commit()


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
    """Return the demo accounts shown on the login screen."""
    return {"accounts": DEMO_ACCOUNTS}


@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """Create or update company demo accounts and encrypted/signed documents."""
    _cleanup_seeded_demo_documents(db)
    users = [_ensure_user(db, account) for account in DEMO_ACCOUNTS]
    admin_user = next(user for user in users if user.username == "ceo")
    documents = _ensure_documents(db, admin_user)

    return {
        "message": "Company demo accounts and documents are ready",
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
    doc = db.query(Document).filter(Document.original_filename == "finance_quarterly_summary.md").first()

    AuditService.log_event(
        db=db,
        action=AuditAction.TAMPERING_DETECTED.value,
        username="company_demo",
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
