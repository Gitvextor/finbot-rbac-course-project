"""
Secure Corporate RAG Assistant - Main FastAPI Application
企业文档安全RAG问答助手 - 主应用
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db
from api import auth_router, documents_router, audit_router, rbac_router
from config import API_HOST, API_PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    print(f"Starting Secure Corporate RAG Assistant...")
    print(f"API will be available at http://{API_HOST}:{API_PORT}")
    
    yield
    
    # Shutdown
    print("Shutting down...")


# Create FastAPI app
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
- **L1_Executive (公司高管)**: 可访问所有部门文档
- **L2_Director (部门总监)**: 可访问本部门及公共文档
- **L3_Manager (部门经理)**: 可访问本部门核心文档
- **L4_Staff (普通员工)**: 仅可访问公共文档

### 部门
Executive, HR, Finance, IT, Sales, R&D, Legal, Public
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "type": type(exc).__name__
        }
    )


# Include routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(audit_router)
app.include_router(rbac_router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check"""
    return {
        "name": "Secure Corporate RAG Assistant",
        "version": "1.0.0",
        "status": "healthy",
        "description": "企业文档安全RAG问答助手"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "services": {
            "database": "connected",
            "encryption": "available",
            "rbac": "available"
        }
    }


@app.get("/api/info", tags=["Info"])
async def api_info():
    """Get API information"""
    return {
        "title": "Secure Corporate RAG Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "documents": "/api/documents",
            "audit": "/api/audit",
            "rbac": "/api/rbac"
        },
        "documentation": "/docs",
        "openapi": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
