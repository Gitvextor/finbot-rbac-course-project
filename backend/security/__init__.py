"""
Security module for Secure Corporate RAG Assistant
"""

from .crypto_utils import CryptoUtils, generate_master_key, encrypt_with_master_key, decrypt_with_master_key
from .hash_utils import HashUtils, compute_file_integrity_hash, create_integrity_report
from .signature_utils import SignatureUtils, ensure_keypair_exists, sign_document_package, verify_document_package
from .hmac_utils import HMACUtils, create_request_auth_header

__all__ = [
    'CryptoUtils',
    'HashUtils', 
    'SignatureUtils',
    'HMACUtils',
    'generate_master_key',
    'encrypt_with_master_key',
    'decrypt_with_master_key',
    'compute_file_integrity_hash',
    'create_integrity_report',
    'ensure_keypair_exists',
    'sign_document_package',
    'verify_document_package',
    'create_request_auth_header'
]
