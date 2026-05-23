"""
Digital signature utilities for Secure Corporate RAG Assistant
RSA signature for document authenticity verification
"""

import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.backends import default_backend
from typing import Tuple, Optional
from pathlib import Path


class SignatureUtils:
    """RSA digital signature utilities"""
    
    KEY_SIZE = 2048  # RSA key size in bits
    PUBLIC_EXPONENT = 65537  # Standard public exponent
    
    @staticmethod
    def generate_keypair() -> Tuple[RSAPrivateKey, RSAPublicKey]:
        """
        Generate RSA key pair
        
        Returns:
            Tuple of (private_key, public_key)
        """
        private_key = rsa.generate_private_key(
            public_exponent=SignatureUtils.PUBLIC_EXPONENT,
            key_size=SignatureUtils.KEY_SIZE,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    @staticmethod
    def save_private_key(private_key: RSAPrivateKey, filepath: str, password: Optional[str] = None):
        """
        Save private key to file
        
        Args:
            private_key: RSA private key
            filepath: Path to save key
            password: Optional encryption password
        """
        if password:
            encryption = serialization.BestAvailableEncryption(password.encode())
        else:
            encryption = serialization.NoEncryption()
        
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(pem)
    
    @staticmethod
    def save_public_key(public_key: RSAPublicKey, filepath: str):
        """Save public key to file"""
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(pem)
    
    @staticmethod
    def load_private_key(filepath: str, password: Optional[str] = None) -> RSAPrivateKey:
        """Load private key from file"""
        with open(filepath, 'rb') as f:
            pem = f.read()
        
        if password:
            return serialization.load_pem_private_key(
                pem, password=password.encode(), backend=default_backend()
            )
        return serialization.load_pem_private_key(
            pem, password=None, backend=default_backend()
        )
    
    @staticmethod
    def load_public_key(filepath: str) -> RSAPublicKey:
        """Load public key from file"""
        with open(filepath, 'rb') as f:
            pem = f.read()
        return serialization.load_pem_public_key(
            pem, backend=default_backend()
        )
    
    @staticmethod
    def sign(data: bytes, private_key: RSAPrivateKey) -> bytes:
        """
        Sign data using RSA private key
        
        Args:
            data: Data to sign
            private_key: RSA private key
            
        Returns:
            Signature bytes
        """
        return private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    @staticmethod
    def verify(data: bytes, signature: bytes, public_key: RSAPublicKey) -> bool:
        """
        Verify RSA signature
        
        Args:
            data: Original data
            signature: Signature to verify
            public_key: RSA public key
            
        Returns:
            True if signature is valid
        """
        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    def sign_and_encode(data: bytes, private_key: RSAPrivateKey) -> str:
        """Sign data and return base64-encoded signature"""
        signature = SignatureUtils.sign(data, private_key)
        return base64.b64encode(signature).decode('utf-8')
    
    @staticmethod
    def verify_from_encoded(data: bytes, signature_b64: str, public_key: RSAPublicKey) -> bool:
        """Verify signature from base64-encoded string"""
        signature = base64.b64decode(signature_b64)
        return SignatureUtils.verify(data, signature, public_key)
    
    @staticmethod
    def create_document_signature(document_hash: str, private_key: RSAPrivateKey) -> str:
        """
        Create signature for document hash
        
        Args:
            document_hash: SHA-256 hash of document
            private_key: Signing private key
            
        Returns:
            Base64-encoded signature
        """
        return SignatureUtils.sign_and_encode(
            document_hash.encode('utf-8'), 
            private_key
        )
    
    @staticmethod
    def verify_document_signature(
        document_hash: str, 
        signature: str, 
        public_key: RSAPublicKey
    ) -> bool:
        """
        Verify document signature
        
        Args:
            document_hash: SHA-256 hash of document
            signature: Base64-encoded signature
            public_key: Verification public key
            
        Returns:
            True if signature is valid
        """
        return SignatureUtils.verify_from_encoded(
            document_hash.encode('utf-8'),
            signature,
            public_key
        )


def ensure_keypair_exists(private_path: str, public_path: str) -> Tuple[RSAPrivateKey, RSAPublicKey]:
    """
    Ensure keypair exists, generate if not
    
    Returns:
        Tuple of (private_key, public_key)
    """
    private_path = Path(private_path)
    public_path = Path(public_path)
    
    if not private_path.exists() or not public_path.exists():
        print(f"Generating new RSA keypair at {private_path.parent}")
        private_key, public_key = SignatureUtils.generate_keypair()
        SignatureUtils.save_private_key(private_key, str(private_path))
        SignatureUtils.save_public_key(public_key, str(public_path))
        return private_key, public_key
    
    return (
        SignatureUtils.load_private_key(str(private_path)),
        SignatureUtils.load_public_key(str(public_path))
    )


def sign_document_package(doc_id: str, doc_hash: str, private_key: RSAPrivateKey) -> dict:
    """
    Create a complete document signature package
    
    Returns:
        Dictionary with doc_id, hash, and signature
    """
    return {
        "doc_id": doc_id,
        "original_hash": doc_hash,
        "signature": SignatureUtils.create_document_signature(doc_hash, private_key),
        "algorithm": "RSA-2048-SHA256-PSS"
    }


def verify_document_package(package: dict, public_key: RSAPublicKey) -> dict:
    """
    Verify a document signature package
    
    Returns:
        Dictionary with verification result
    """
    is_valid = SignatureUtils.verify_document_signature(
        package["original_hash"],
        package["signature"],
        public_key
    )
    
    return {
        "doc_id": package["doc_id"],
        "is_valid": is_valid,
        "original_hash": package["original_hash"]
    }
