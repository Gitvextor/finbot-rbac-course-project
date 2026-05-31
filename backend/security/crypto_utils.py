"""
Cryptographic utilities for Secure Corporate RAG Assistant
AES-256 encryption for document storage
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Tuple
import json


class CryptoUtils:
    """AES-256-GCM encryption and decryption utilities"""
    
    NONCE_SIZE = 12  # 96 bits, recommended for GCM
    KEY_SIZE = 32    # 256 bits
    SALT_SIZE = 16   # 128 bits
    ITERATIONS = 100000  # PBKDF2 iterations
    
    @staticmethod
    def generate_key(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """
        Generate AES-256 key from password using PBKDF2
        
        Args:
            password: Master password for key derivation
            salt: Random salt (generated if not provided)
            
        Returns:
            Tuple of (key, salt)
        """
        if salt is None:
            salt = os.urandom(CryptoUtils.SALT_SIZE)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=CryptoUtils.KEY_SIZE,
            salt=salt,
            iterations=CryptoUtils.ITERATIONS,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        return key, salt
    
    @staticmethod
    def encrypt(data: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Plaintext data to encrypt
            key: 32-byte encryption key
            
        Returns:
            Tuple of (ciphertext, nonce, tag)
        """
        nonce = os.urandom(CryptoUtils.NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        # GCM appends the tag to ciphertext, separate them
        tag = ciphertext[-16:]
        encrypted_data = ciphertext[:-16]
        
        return encrypted_data, nonce, tag
    
    @staticmethod
    def decrypt(encrypted_data: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: Ciphertext without tag
            key: 32-byte encryption key
            nonce: 12-byte nonce used during encryption
            tag: 16-byte authentication tag
            
        Returns:
            Decrypted plaintext
        """
        aesgcm = AESGCM(key)
        # Reconstruct ciphertext with tag
        ciphertext = encrypted_data + tag
        return aesgcm.decrypt(nonce, ciphertext, None)
    
    @staticmethod
    def encrypt_file(file_content: bytes, password: str) -> dict:
        """
        Encrypt file content and return encrypted package
        
        Args:
            file_content: Raw file bytes
            password: Encryption password
            
        Returns:
            Dictionary with encrypted data, salt, nonce, tag
        """
        key, salt = CryptoUtils.generate_key(password)
        encrypted_data, nonce, tag = CryptoUtils.encrypt(file_content, key)
        
        return {
            "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8'),
            "salt": base64.b64encode(salt).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "tag": base64.b64encode(tag).decode('utf-8')
        }
    
    @staticmethod
    def decrypt_file(encrypted_package: dict, password: str) -> bytes:
        """
        Decrypt file from encrypted package
        
        Args:
            encrypted_package: Dictionary with encrypted data
            password: Decryption password
            
        Returns:
            Decrypted file bytes
        """
        key, _ = CryptoUtils.generate_key(
            password, 
            base64.b64decode(encrypted_package["salt"])
        )
        
        return CryptoUtils.decrypt(
            base64.b64decode(encrypted_package["encrypted_data"]),
            key,
            base64.b64decode(encrypted_package["nonce"]),
            base64.b64decode(encrypted_package["tag"])
        )
    
    @staticmethod
    def save_encrypted_package(encrypted_package: dict, filepath: str):
        """Save encrypted package to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(encrypted_package, f, indent=2)
    
    @staticmethod
    def load_encrypted_package(filepath: str) -> dict:
        """Load encrypted package from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def generate_master_key() -> bytes:
        """Generate a random 256-bit master key."""
        return os.urandom(CryptoUtils.KEY_SIZE)

    @staticmethod
    def encrypt_with_master_key(data: bytes, master_key: bytes) -> Tuple[bytes, bytes]:
        """Encrypt data directly with a raw AES-GCM master key."""
        nonce = os.urandom(CryptoUtils.NONCE_SIZE)
        aesgcm = AESGCM(master_key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return ciphertext, nonce

    @staticmethod
    def decrypt_with_master_key(ciphertext: bytes, master_key: bytes, nonce: bytes) -> bytes:
        """Decrypt data encrypted with encrypt_with_master_key."""
        aesgcm = AESGCM(master_key)
        return aesgcm.decrypt(nonce, ciphertext, None)


def generate_master_key() -> bytes:
    """Generate a random master key for document encryption"""
    return os.urandom(CryptoUtils.KEY_SIZE)


def encrypt_with_master_key(data: bytes, master_key: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt data using master key (for storage)
    
    Returns:
        Tuple of (encrypted_data, nonce)
    """
    nonce = os.urandom(CryptoUtils.NONCE_SIZE)
    aesgcm = AESGCM(master_key)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return ciphertext, nonce


def decrypt_with_master_key(ciphertext: bytes, master_key: bytes, nonce: bytes) -> bytes:
    """Decrypt data using master key"""
    aesgcm = AESGCM(master_key)
    return aesgcm.decrypt(nonce, ciphertext, None)
