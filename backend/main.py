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
import sys
import traceback
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, SessionLocal
from api import auth_router, documents_router, audit_router, rbac_router
from config import (
    API_HOST, API_PORT,
    ROLE_COLLECTIONS,
)

# ── RAG pipeline imports (成员B) ──
try:
    from router import route_query as do_route_query
    from rag import answer as rag_answer
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    RAG_IMPORT_ERROR = str(e)
    print(f"[WARNING] RAG pipeline not available: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    print(f"Starting Secure Corporate RAG Assistant...")
    print(f"RAG pipeline: {'AVAILABLE' if RAG_AVAILABLE else 'UNAVAILABLE'}")
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


# ═══════════════════════════════════════════════════════════════
#  成员B: /api/chat  — RAG问答端点
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    query: str
    role: str           # "c_level" | "engineering" | "finance" | "marketing" | "hr_manager" | "employee"
    session_id: str = ""
    user_id: str = ""   # for audit logging (maps to member-A user table if available)


def _log_query_audit(user_id: str, username: str, query: str, route: str, success: bool, details: str = ""):
    """Record RAG query event into the member-A audit_logs table."""
    try:
        from services.audit_service import AuditService
        db = SessionLocal()
        AuditService.log_event(
            db=db,
            action="rag_query" if success else "rag_query_blocked",
            user_id=user_id or None,
            username=username or "anonymous",
            resource_type="rag",
            details=details,
            success=success,
            is_suspicious=not success,
        )
        db.close()
    except Exception:
        pass  # audit logging is best-effort


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

    if not RAG_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                "detail": f"RAG pipeline unavailable: {RAG_IMPORT_ERROR}",
                "hint": "Install dependencies: pip install -r requirements.txt",
            },
        )

    # ── 1. Input guardrails: Prompt Injection + PII ──
    try:
        sid = body.session_id or _extract_session_id(request)
        route = do_route_query(body.query, sid)
    except ValueError as guardrail_err:
        reason = str(guardrail_err)
        _log_query_audit(
            body.user_id, "", body.query,
            "blocked", False,
            details=body.query[:200],
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
            f"Access denied: role '{body.role}' cannot access collection '{route}'. "
            f"Allowed: {allowed_collections}"
        )
        _log_query_audit(
            body.user_id, "", body.query,
            route, False,
            details=reason,
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
        ans, context_chunks = rag_answer(body.query, route, body.role)
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"RAG pipeline error: {str(exc)}",
                "type": type(exc).__name__,
            },
        )

    # ── 4. Source verification ──
    sources = _extract_sources(context_chunks)

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


def _extract_sources(context_chunks: list) -> list:
    """Parse source metadata from RAG context chunks."""
    sources = []
    seen = set()
    for chunk in context_chunks:
        # chunk is a formatted string like "[Source 1 | file.pdf | Page 3]\ntext..."
        if chunk.startswith("[Source"):
            line = chunk.split("\n")[0]
            key = line.strip()
            if key not in seen:
                seen.add(key)
                sources.append({
                    "source": line,
                    "verified": False,  # not verified through member-A's signature system
                })
    return sources


# ── Health & Info ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "Secure Corporate RAG Assistant",
        "version": "1.0.0",
        "status": "healthy",
        "rag_pipeline": "available" if RAG_AVAILABLE else "unavailable",
        "description": "企业文档安全RAG问答助手",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "services": {
            "database": "connected",
            "encryption": "available",
            "rbac": "available",
            "rag": "available" if RAG_AVAILABLE else "unavailable",
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
        },
        "documentation": "/docs",
        "openapi": "/openapi.json",
    }


if __name__ == "__main__":
    import os
    import uvicorn

    reload_enabled = os.getenv("FINBOT_RELOAD", "1") == "1"
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
