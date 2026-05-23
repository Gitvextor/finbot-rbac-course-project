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
SECRET_KEY = "your-secret-key-change-in-production"  # Should be loaded from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# RBAC Permission Matrix
# Format: {(user_level, user_department): [allowed_departments]}
PERMISSION_MATRIX = {
    # Level 1 - Executive: can access all departments
    ("L1_Executive", "Executive"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "HR"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "Finance"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "IT"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "Sales"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "R&D"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    ("L1_Executive", "Legal"): ["Executive", "HR", "Finance", "IT", "Sales", "R&D", "Legal", "Public"],
    
    # Level 2 - Director: can access own department and below
    ("L2_Director", "HR"): ["HR", "Public"],
    ("L2_Director", "Finance"): ["Finance", "Public"],
    ("L2_Director", "IT"): ["IT", "Public"],
    ("L2_Director", "Sales"): ["Sales", "Public"],
    ("L2_Director", "R&D"): ["R&D", "Public"],
    ("L2_Director", "Legal"): ["Legal", "Public"],
    
    # Level 3 - Manager: can access core documents in own department
    ("L3_Manager", "HR"): ["HR", "Public"],
    ("L3_Manager", "Finance"): ["Finance", "Public"],
    ("L3_Manager", "IT"): ["IT", "Public"],
    ("L3_Manager", "Sales"): ["Sales", "Public"],
    ("L3_Manager", "R&D"): ["R&D", "Public"],
    ("L3_Manager", "Legal"): ["Legal", "Public"],
    
    # Level 4 - Staff: can only access public documents
    ("L4_Staff", "HR"): ["Public"],
    ("L4_Staff", "Finance"): ["Public"],
    ("L4_Staff", "IT"): ["Public"],
    ("L4_Staff", "Sales"): ["Public"],
    ("L4_Staff", "R&D"): ["Public"],
    ("L4_Staff", "Legal"): ["Public"],
}

# Level hierarchy (higher number = higher privilege)
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
