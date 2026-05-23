"""
Configuration settings for Secure Corporate RAG Assistant
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCUMENTS_DIR = BASE_DIR / "documents"
KEYS_DIR = BASE_DIR / "keys"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(exist_ok=True)
KEYS_DIR.mkdir(exist_ok=True)

# Encryption settings
ENCRYPTION_KEY_FILE = KEYS_DIR / "encryption.key"
RSA_PRIVATE_KEY_FILE = KEYS_DIR / "private_key.pem"
RSA_PUBLIC_KEY_FILE = KEYS_DIR / "public_key.pem"

# Database
DATABASE_URL = "sqlite:///./secure_corporate_rag.db"

# JWT settings
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# RBAC Permission Matrix
PERMISSION_MATRIX = {
    ("L1_Executive", "Executive"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "HR"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "Finance"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "IT"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "Sales"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "R&D"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "Legal"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L2_Director", "HR"): ["HR", "Public"],
    ("L2_Director", "Finance"): ["Finance", "Public"],
    ("L2_Director", "IT"): ["IT", "Public"],
    ("L2_Director", "Sales"): ["Sales", "Public"],
    ("L2_Director", "R&D"): ["R&D", "Public"],
    ("L2_Director", "Legal"): ["Legal", "Public"],
    ("L3_Manager", "HR"): ["HR", "Public"],
    ("L3_Manager", "Finance"): ["Finance", "Public"],
    ("L3_Manager", "IT"): ["IT", "Public"],
    ("L3_Manager", "Sales"): ["Sales", "Public"],
    ("L3_Manager", "R&D"): ["R&D", "Public"],
    ("L3_Manager", "Legal"): ["Legal", "Public"],
    ("L4_Staff", "HR"): ["Public"],
    ("L4_Staff", "Finance"): ["Public"],
    ("L4_Staff", "IT"): ["Public"],
    ("L4_Staff", "Sales"): ["Public"],
    ("L4_Staff", "R&D"): ["Public"],
    ("L4_Staff", "Legal"): ["Public"],
}

LEVEL_HIERARCHY = {
    "L1_Executive": 1,
    "L2_Director": 2,
    "L3_Manager": 3,
    "L4_Staff": 4,
}

# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000

# Audit settings
AUDIT_LOG_ENABLED = True
AUDIT_LOG_FILE = BASE_DIR / "audit_logs.jsonl"

# ============================================================
# RAG Pipeline Configuration (成员B)
# ============================================================

COLLECTION_NAME = "finbot_docs"
GROQ_MODEL = "llama-3.1-8b-instant"
SENTENCE_TRANSFORMER_LLM = "all-MiniLM-L6-v2"

# Role → accessible collections (RBAC for RAG queries)
ROLE_COLLECTIONS = {
    "c_level":     ["engineering", "finance", "hr", "marketing", "general"],
    "engineering": ["engineering", "general"],
    "finance":     ["finance", "general"],
    "marketing":   ["marketing", "general"],
    "hr_manager":  ["hr", "general"],
    "employee":    ["general"],
}

# Collection → roles (metadata at ingestion)
ROLE_ACCESS = {
    "engineering": ["c_level", "engineering"],
    "finance":     ["c_level", "finance"],
    "hr":          ["c_level", "hr_manager"],
    "marketing":   ["c_level", "marketing"],
    "general":     ["c_level", "engineering", "finance", "marketing", "hr_manager", "employee"],
}

MAX_QUERIES = 20

# --- Input Guardrails ---

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|your)\s+(instructions?|prompts?|rules?)",
    r"you\s+are\s+now\s+(dan|dev|jailbreak)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if\s+)?(a\s+different|another)",
    r"forget\s+(everything|all|your\s+training)",
    r"system\s*prompt\s*:",
    r"new\s+instructions?\s*:",
    r"disregard\s+(previous|all)",
    r"do\s+not\s+follow",
    r"忽略\s*(所有|之前|上述)",
    r"现在\s*开始\s*扮演",
    r"忘记\s*(所有|你的\s*训练)",
]

PII_PATTERNS = {
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    "ssn":         r"\b\d{3}-\d{2}-\d{4}\b",
    "email":       r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone":       r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "aadhaar":     r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "passport":    r"\b[A-Z]{1,2}\d{6,7}\b",
}

# --- Output Guardrails ---

ROLE_SENSITIVE_KEYWORDS = {
    "finance": [
        "revenue", "profit", "budget", "expenditure", "ebitda",
        "balance sheet", "cash flow", "financial statement", "earnings",
        "net income", "operating margin", "fiscal year", "annual report",
    ],
    "engineering": [
        "architecture", "microservices", "ci/cd", "api endpoint",
        "database schema", "deployment pipeline", "kubernetes",
        "docker", "system design", "infrastructure", "backend service",
    ],
    "hr": [
        "salary", "compensation", "headcount", "payroll", "termination",
        "disciplinary", "performance review", "promotion", "bonus",
    ],
    "marketing": [
        "campaign roi", "cac", "lead conversion", "cost per lead",
        "channel performance", "ad spend", "marketing budget", "ctr",
    ],
}

UNGROUNDED_WARNING = (
    "\n\n⚠️ 注意：部分内容可能未经来源验证，请核实信息准确性。"
)

CITATION_WARNING = (
    "\n\n⚠️ 注意：回答缺少明确的来源引用，请参考原始文档验证。"
)

LEAKAGE_WARNING = (
    "\n\n⚠️ 安全警告：检测到可能存在跨部门信息泄露。请核实您的访问权限。"
)

# --- RAGAs Evaluation test data ---

mock_ques = [
    "What is the system architecture of the platform?",
    "How does the CI/CD pipeline work?",
    "What is the SLA for API uptime?",
    "Explain the microservices setup",
    "What tech stack is used for the backend?",
    "How do I set up the local development environment?",
    "What are the engineering sprint metrics for 2024?",
    "Describe the incident response runbook",
    "What is the company's total revenue this quarter?",
    "Show me the profit and loss statement",
    "What is the operating budget for 2024?",
    "What are the key financial KPIs?",
    "What is the leave balance for Pavan Krishnan?",
    "How many female employees are in HR?",
    "What is the average salary for Senior HR Executives?",
    "How many employees are in the Finance department?",
    "What is the company's vision and mission?",
    "What is the onboarding process for new employees?",
    "What benefits are offered to employees?",
    "How many types of leave are available?",
    "What is the marketing campaign performance?",
    "How many leads were generated last quarter?",
    "What is the customer acquisition cost?",
    "Which channels drive the most conversions?",
]

mock_ground_truth = mock_ques  # placeholder
