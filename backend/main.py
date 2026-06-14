"""
Secure Corporate RAG Assistant - Main FastAPI Application
企业文档安全RAG问答助手 - 主应用

整合了成员A的安全底座API和成员B的RAG问答管道
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os
import sys
import traceback
import uuid
import re
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(Path(__file__).parent / ".env")

from database import init_db, SessionLocal
from api import auth_router, documents_router, audit_router, rbac_router, demo_router, rag_admin_router
from config import (
    API_HOST, API_PORT,
    DEEPSEEK_API_BASE,
    DEEPSEEK_MODEL,
    ROLE_COLLECTIONS,
    INJECTION_PATTERNS,
    PII_PATTERNS,
    RAG_SYSTEM_PROMPT,
)
from models.audit_log import AuditAction
from services.rag_source_registry import RAGSourceRegistry

# ── RAG pipeline: lazy load (login/auth should not wait for ML models) ──
RAG_AVAILABLE: bool | None = None
RAG_IMPORT_ERROR = ""
_do_route_query = None
_rag_answer = None


def _ensure_rag_pipeline() -> bool:
    """Import heavy RAG modules on first chat request, not at server startup."""
    global RAG_AVAILABLE, RAG_IMPORT_ERROR, _do_route_query, _rag_answer
    if RAG_AVAILABLE is not None:
        return RAG_AVAILABLE

    try:
        from router import route_query as route_query_fn
        from rag import answer as answer_fn

        _do_route_query = route_query_fn
        _rag_answer = answer_fn
        RAG_AVAILABLE = True
        print("[RAG] Pipeline loaded successfully.")
    except Exception as exc:
        RAG_AVAILABLE = False
        RAG_IMPORT_ERROR = str(exc)
        print(f"[WARNING] RAG pipeline not available: {exc}")

    return RAG_AVAILABLE

SERVER_BOOT_ID = str(uuid.uuid4())


def _rag_service_status() -> str:
    if RAG_AVAILABLE is True:
        return "available"
    if RAG_AVAILABLE is False:
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek_context_fallback"
        return "unavailable"
    return "idle"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    print(f"Starting Secure Corporate RAG Assistant...")
    print(f"RAG pipeline: {_rag_service_status()}")
    print(f"API will be available at http://{API_HOST}:{API_PORT}")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Secure Corporate RAG Assistant",
    description="""
## 企业文档安全RAG问答助手

面向公司内部文档的安全问答系统，实现：

### 核心功能
- **文档加密存储**: AES-256-GCM加密，保护敏感文档
- **RBAC权限控制**: 基于级别和部门的精细化权限管理
- **文档签名验证**: RSA数字签名，确保文档真实性
- **完整性校验**: SHA-256哈希，防止文档篡改
- **审计日志**: 完整的安全事件追踪

### 权限级别
- L1_Executive (公司高管): 可访问所有部门文档
- L2_Director (部门总监): 可访问本部门及公共文档
- L3_Manager (部门经理): 可访问本部门核心文档
- L4_Staff (普通员工): 仅可访问公共文档

### 部门
Executive, HR, Finance, IT, Sales, R&D, Legal, Public
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "type": type(exc).__name__,
        },
    )


# ── Include member-A routers ──
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(audit_router)
app.include_router(rbac_router)
app.include_router(demo_router)
app.include_router(rag_admin_router)


# ═══════════════════════════════════════════════════════════════
#  成员B: /api/chat  — RAG问答端点
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    query: str
    role: str           # "c_level" | "engineering" | "finance" | "marketing" | "hr_manager" | "employee"
    session_id: str = ""
    user_id: str = ""   # for audit logging (maps to member-A user table if available)


LIGHTWEIGHT_ROUTE_KEYWORDS = {
    "engineering": [
        "architecture", "sla", "api", "ci/cd", "cicd", "sprint", "engineering", "工程", "架构",
        "system", "service", "deployment", "uptime", "microservice", "backend", "系统", "服务",
        "部署", "流水线", "技术栈", "微服务",
    ],
    "finance": ["financial", "finance", "budget", "revenue", "profit", "quarterly", "财务", "预算", "收入"],
    "hr": ["hr", "employee count", "employees in", "salary", "headcount", "payroll", "performance", "员工统计", "薪资", "绩效"],
    "marketing": ["marketing", "campaign", "lead", "roi", "广告", "市场", "营销"],
    "general": ["policy", "handbook", "public", "onboarding", "benefit", "leave policy", "leave application", "work hours", "公开", "手册", "福利", "请假政策"],
}


DEMO_CONTEXTS = {
    "general": {
        "source": "company_public_handbook.md",
        "text": (
            "FinSolve Technologies 是一家服务银行、保险和投资管理客户的 B2B fintech 公司，"
            "内部资料助手 FinBot 用于安全查询公司知识库。新员工入职流程包括 HR 文件核验、"
            "IT 账号开通、安全意识培训、直属经理团队介绍，以及 30 天内完成合规模块和 buddy 辅导。"
            "员工福利包括健康保险、带薪年假、病假、健康支持、学习预算报销和适用的退休缴费。"
            "请假政策要求通过 HRMS 提交年假申请并由经理审批，病假按需提交证明，紧急假可由经理和 HR 补批。"
            "标准工作时间为周一至周五 9:30 到 18:30。Employee 只能查看公共资料，不能访问 HR、财务、工程或市场等部门敏感资料。"
        ),
    },
    "engineering": {
        "source": "engineering_sla_report.md",
        "text": (
            "工程资料包含 API uptime SLA、CI/CD 流水线、微服务架构、部署状态和 sprint metrics。"
            "Engineering 与 Executive 身份可以访问工程资料，其他普通身份应被 RBAC 拦截。"
        ),
    },
    "finance": {
        "source": "finance_quarterly_summary.md",
        "text": (
            "财务资料包含季度收入、预算执行、费用摘要、供应商付款和财务 KPI。"
            "Finance 与 Executive 身份可以访问财务资料，其他部门默认不可见。"
        ),
    },
    "hr": {
        "source": "hr_employee_records.csv",
        "text": (
            "HR 员工记录包含姓名、邮箱、电话、部门等敏感字段，只用于 PII 与权限演示。"
            "HR 与 Executive 身份可以访问，普通 Employee 不应看到该资料内容。"
        ),
    },
    "marketing": {
        "source": "marketing_campaign_report.md",
        "text": (
            "市场资料包含 campaign performance、leads、cost per lead、conversion channel 和 ROI。"
            "Marketing 与 Executive 身份可以访问市场资料，其他部门默认不可见。"
        ),
    },
}


def _classify_blocked_query(reason: str, route: str = "blocked") -> str:
    """Map blocked chat outcomes to dashboard-friendly audit actions."""
    reason_lower = (reason or "").lower()
    if "prompt injection" in reason_lower or "jailbreak" in reason_lower:
        return AuditAction.PROMPT_INJECTION_BLOCKED.value
    if (
        "pii" in reason_lower
        or "credit_card" in reason_lower
        or "email" in reason_lower
        or "ssn" in reason_lower
        or "phone" in reason_lower
    ):
        return AuditAction.PII_BLOCKED.value
    if route and route != "blocked":
        return AuditAction.UNAUTHORIZED_ACCESS.value
    return "rag_query_blocked"


def _log_query_audit(
    user_id: str,
    username: str,
    query: str,
    route: str,
    success: bool,
    details: str = "",
    action: str | None = None,
):
    """Record RAG query event into the member-A audit_logs table."""
    try:
        from services.audit_service import AuditService
        db = SessionLocal()
        audit_action = action or ("rag_query" if success else _classify_blocked_query(details, route))
        AuditService.log_event(
            db=db,
            action=audit_action,
            user_id=None,
            username=username or user_id or "anonymous",
            resource_type="rag",
            resource_id=route,
            details=details,
            success=success,
            is_suspicious=not success,
        )
        db.close()
    except Exception:
        pass  # audit logging is best-effort


def _lightweight_route(query: str) -> str:
    text = query.lower()
    scores = {route: 0 for route in LIGHTWEIGHT_ROUTE_KEYWORDS}
    for route, keywords in LIGHTWEIGHT_ROUTE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                scores[route] += 1
    best_route, score = max(scores.items(), key=lambda item: item[1])
    return best_route if score > 0 else "general"


def _lightweight_guardrail(query: str) -> str | None:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return "Prompt injection detected. Request blocked."
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            return f"PII detected ({pii_type}). Request blocked."
    return None


def _generate_with_deepseek(query: str, route: str, role: str, context: str) -> str:
    """Generate an answer with DeepSeek when vector embeddings are unavailable."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_API_BASE)
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"当前用户角色：{role}\n"
                    f"已授权资料路由：{route}\n"
                    f"Context:\n{context}\n\n"
                    f"Question:\n{query}"
                ),
            },
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or "未生成回答。"


def _fallback_chat_response(body: ChatRequest):
    """Presentation-safe chat path when the heavyweight RAG model cannot load."""
    guardrail_reason = _lightweight_guardrail(body.query)
    if guardrail_reason:
        _log_query_audit(
            body.user_id,
            body.user_id,
            body.query,
            "blocked",
            False,
            details=guardrail_reason,
            action=_classify_blocked_query(guardrail_reason),
        )
        return {
            "role": body.role,
            "route": "blocked",
            "allowed_collections": [],
            "blocked": True,
            "block_reason": guardrail_reason,
            "answer": None,
            "sources": [],
            "guardrail_triggered": True,
            "fallback_mode": True,
        }

    route = _lightweight_route(body.query)
    allowed_collections = ROLE_COLLECTIONS.get(body.role, ["general"])
    if route not in allowed_collections:
        reason = (
            f"访问被拒绝：角色 `{body.role}` 无权访问 `{route}` 文档库。"
            f"允许范围：{allowed_collections}。"
        )
        _log_query_audit(
            body.user_id,
            body.user_id,
            body.query,
            route,
            False,
            details=reason,
            action=AuditAction.UNAUTHORIZED_ACCESS.value,
        )
        return {
            "role": body.role,
            "route": route,
            "allowed_collections": allowed_collections,
            "blocked": True,
            "block_reason": reason,
            "answer": None,
            "sources": [],
            "fallback_mode": True,
        }

    context_item = DEMO_CONTEXTS.get(route, DEMO_CONTEXTS["general"])
    try:
        answer_text = _generate_with_deepseek(body.query, route, body.role, context_item["text"])
        fallback_note = "deepseek contextual fallback"
        source_label = f"[DeepSeek fallback | {context_item['source']}]"
    except Exception as exc:
        answer_text = (
            "## 资料助手回答\n\n"
            f"根据当前可访问资料，问题被路由到 `{route}`，当前角色 `{body.role}` "
            f"允许访问范围为 `{allowed_collections}`。\n\n"
            f"{context_item['text']}\n\n"
            f"> DeepSeek 生成暂时不可用：{type(exc).__name__}。"
        )
        fallback_note = f"local contextual fallback: {type(exc).__name__}"
        source_label = f"[Local fallback | {context_item['source']}]"
    _log_query_audit(
        body.user_id,
        body.user_id,
        body.query,
        route,
        True,
        details=fallback_note,
    )
    fallback_sources = _verified_sources_for_label(source_label, context_item["source"])
    return {
        "role": body.role,
        "route": route,
        "allowed_collections": allowed_collections,
        "blocked": False,
        "guardrail_triggered": False,
        "answer": answer_text,
        "sources": fallback_sources,
        "fallback_mode": True,
    }


@app.post("/api/chat")
def chat_endpoint(body: ChatRequest, request: Request):
    """
    RAG chat endpoint with full security pipeline:

    1. Prompt Injection + PII detection (input guardrails)
    2. Semantic routing to department collection
    3. RBAC enforcement — role ↔ collection access
    4. RAG retrieval + LLM generation
    5. Source verification & citation
    6. Audit logging
    """
    if not body.query.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "query is required"},
        )

    if not _ensure_rag_pipeline():
        return _fallback_chat_response(body)

    # ── 1. Input guardrails: Prompt Injection + PII ──
    try:
        sid = body.session_id or _extract_session_id(request)
        route = _do_route_query(body.query, sid)
    except ValueError as guardrail_err:
        reason = str(guardrail_err)
        _log_query_audit(
            body.user_id, "", body.query,
            "blocked", False,
            details=reason,
            action=_classify_blocked_query(reason),
        )
        return {
            "role": body.role,
            "route": "blocked",
            "allowed_collections": [],
            "blocked": True,
            "block_reason": reason,
            "answer": None,
            "sources": [],
            "guardrail_triggered": True,
        }

    # ── 2. RBAC enforcement ──
    allowed_collections = ROLE_COLLECTIONS.get(body.role, ["general"])
    if route not in allowed_collections:
        reason = (
            f"访问被拒绝：角色 `{body.role}` 无权访问 `{route}` 文档库。"
            f"允许范围：{allowed_collections}。"
            f"请更换角色（如 c_level）或使用与部门匹配的问题。"
        )
        _log_query_audit(
            body.user_id, "", body.query,
            route, False,
            details=reason,
            action=AuditAction.UNAUTHORIZED_ACCESS.value,
        )
        return {
            "role": body.role,
            "route": route,
            "allowed_collections": allowed_collections,
            "blocked": True,
            "block_reason": reason,
            "answer": None,
            "sources": [],
        }

    # ── 3. RAG answer generation ──
    try:
        ans, context_chunks, source_metas = _rag_answer(body.query, route, body.role)
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"RAG pipeline error: {str(exc)}",
                "type": type(exc).__name__,
            },
        )

    # ── 4. Source verification (member-A integrity + signature) ──
    registry = RAGSourceRegistry()
    sources = registry.build_verified_sources(source_metas)
    sources = [source for source in sources if source.get("verified")]

    # ── 5. Audit logging ──
    _log_query_audit(
        body.user_id, "", body.query,
        route, True,
        details=f"sources: {len(sources)} chunks",
    )

    # ── 6. Return ──
    return {
        "role": body.role,
        "route": route,
        "allowed_collections": allowed_collections,
        "blocked": False,
        "guardrail_triggered": False,
        "answer": ans,
        "sources": sources,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_session_id(request: Request) -> str:
    """Extract session identifier from headers / client info."""
    return (
        request.headers.get("x-session-id")
        or request.headers.get("x-forwarded-for", "").split(",")[0]
        or (request.client.host if request.client else "unknown")
    )


def _verified_sources_for_label(source_label: str, filename: str) -> list:
    """Resolve fallback/demo source labels through member-A verification."""
    db = SessionLocal()
    try:
        registry = RAGSourceRegistry()
        verification = registry.get_verification_metadata(db, filename)
        source_metas = [
            {
                "source": source_label,
                "doc_id": verification.get("doc_id"),
                "document_hash": verification.get("document_hash"),
                "signature_valid": verification.get("signature_valid"),
                "verified": bool(
                    verification.get("is_verified") and verification.get("signature_valid")
                ),
            }
        ]
        verified = registry.build_verified_sources(source_metas)
        return [source for source in verified if source.get("verified")]
    finally:
        db.close()


def _extract_sources(context_chunks: list) -> list:
    """Legacy parser kept for compatibility with older callers."""
    sources = []
    seen = set()
    for chunk in context_chunks:
        if chunk.startswith("[Source"):
            line = chunk.split("\n")[0]
            key = line.strip()
            if key not in seen:
                seen.add(key)
                sources.append({"source": line, "verified": False})
    return sources


# ── Health & Info ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "Secure Corporate RAG Assistant",
        "version": "1.0.0",
        "status": "healthy",
        "rag_pipeline": _rag_service_status(),
        "description": "企业文档安全RAG问答助手",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "boot_id": SERVER_BOOT_ID,
        "services": {
            "database": "connected",
            "encryption": "available",
            "rbac": "available",
            "rag": _rag_service_status(),
        },
    }


@app.get("/api/info", tags=["Info"])
async def api_info():
    return {
        "title": "Secure Corporate RAG Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "documents": "/api/documents",
            "audit": "/api/audit",
            "rbac": "/api/rbac",
            "chat": "/api/chat",
            "demo": "/api/demo",
        },
        "documentation": "/docs",
        "openapi": "/openapi.json",
    }


if __name__ == "__main__":
    import os
    import uvicorn

    reload_enabled = os.getenv("FINBOT_RELOAD", "0") == "1"
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=reload_enabled,
        reload_excludes=[
            "qdrant_data",
            "qdrant_data/*",
            "*.db",
            "*.db-journal",
            "__pycache__",
            "__pycache__/*",
        ],
    )
