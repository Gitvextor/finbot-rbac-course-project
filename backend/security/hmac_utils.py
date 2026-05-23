"""
HMAC authentication utilities for Secure Corporate RAG Assistant
Request authentication and integrity verification
"""

import hmac
import hashlib
import time
import secrets
from typing import Tuple, Optional
from datetime import datetime, timedelta


class HMACUtils:
    """HMAC-based request authentication utilities"""
    
    DEFAULT_TIMESTAMP_TOLERANCE = 300  # 5 minutes tolerance
    
    @staticmethod
    def generate_secret_key(length: int = 32) -> str:
        """
        Generate a secure random secret key
        
        Args:
            length: Key length in bytes
            
        Returns:
            Hex-encoded secret key
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def compute_hmac(message: str, secret_key: str, algorithm: str = "sha256") -> str:
        """
        Compute HMAC for message
        
        Args:
            message: Message to authenticate
            secret_key: Secret key
            algorithm: Hash algorithm (sha256, sha384, sha512)
            
        Returns:
            Hex-encoded HMAC
        """
        hash_func = getattr(hashlib, algorithm)
        mac = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hash_func
        )
        return mac.hexdigest()
    
    @staticmethod
    def verify_hmac(message: str, signature: str, secret_key: str, algorithm: str = "sha256") -> bool:
        """
        Verify HMAC signature
        
        Args:
            message: Original message
            signature: HMAC signature to verify
            secret_key: Secret key
            algorithm: Hash algorithm
            
        Returns:
            True if signature is valid
        """
        expected_mac = HMACUtils.compute_hmac(message, secret_key, algorithm)
        return hmac.compare_digest(expected_mac, signature.lower())
    
    @staticmethod
    def create_auth_token(
        user_id: str,
        secret_key: str,
        expires_in: int = 3600,
        extra_data: Optional[dict] = None
    ) -> dict:
        """
        Create a time-based authentication token
        
        Args:
            user_id: User identifier
            secret_key: Secret key for signing
            expires_in: Token validity in seconds
            extra_data: Additional data to include
            
        Returns:
            Token dictionary with signature
        """
        timestamp = int(time.time())
        expires_at = timestamp + expires_in
        
        message_parts = [user_id, str(timestamp), str(expires_at)]
        if extra_data:
            for key in sorted(extra_data.keys()):
                message_parts.append(f"{key}:{extra_data[key]}")
        
        message = "|".join(message_parts)
        signature = HMACUtils.compute_hmac(message, secret_key)
        
        return {
            "user_id": user_id,
            "timestamp": timestamp,
            "expires_at": expires_at,
            "signature": signature,
            "extra_data": extra_data or {}
        }
    
    @staticmethod
    def verify_auth_token(
        token: dict,
        secret_key: str,
        tolerance: int = None
    ) -> Tuple[bool, str]:
        """
        Verify authentication token
        
        Args:
            token: Token dictionary
            secret_key: Secret key
            tolerance: Time tolerance in seconds
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if tolerance is None:
            tolerance = HMACUtils.DEFAULT_TIMESTAMP_TOLERANCE
        
        current_time = int(time.time())
        
        # Check expiration
        if token["expires_at"] < current_time:
            return False, "Token expired"
        
        # Check timestamp is within tolerance
        if abs(current_time - token["timestamp"]) > tolerance:
            return False, "Timestamp outside tolerance window"
        
        # Verify signature
        message_parts = [
            token["user_id"],
            str(token["timestamp"]),
            str(token["expires_at"])
        ]
        for key in sorted(token.get("extra_data", {}).keys()):
            message_parts.append(f"{key}:{token['extra_data'][key]}")
        
        message = "|".join(message_parts)
        
        if not HMACUtils.verify_hmac(message, token["signature"], secret_key):
            return False, "Invalid signature"
        
        return True, "Valid"
    
    @staticmethod
    def create_request_signature(
        method: str,
        path: str,
        body: str,
        timestamp: int,
        secret_key: str
    ) -> str:
        """
        Create HMAC signature for API request
        
        Args:
            method: HTTP method
            path: Request path
            body: Request body
            timestamp: Unix timestamp
            secret_key: Secret key
            
        Returns:
            HMAC signature
        """
        message = f"{method}|{path}|{body}|{timestamp}"
        return HMACUtils.compute_hmac(message, secret_key)
    
    @staticmethod
    def verify_request_signature(
        method: str,
        path: str,
        body: str,
        timestamp: int,
        signature: str,
        secret_key: str,
        tolerance: int = None
    ) -> bool:
        """
        Verify API request signature
        
        Args:
            method: HTTP method
            path: Request path
            body: Request body
            timestamp: Unix timestamp
            signature: Request signature
            secret_key: Secret key
            tolerance: Time tolerance in seconds
            
        Returns:
            True if signature is valid
        """
        if tolerance is None:
            tolerance = HMACUtils.DEFAULT_TIMESTAMP_TOLERANCE
        
        # Check timestamp
        current_time = int(time.time())
        if abs(current_time - timestamp) > tolerance:
            return False
        
        # Verify signature
        expected_sig = HMACUtils.create_request_signature(
            method, path, body, timestamp, secret_key
        )
        return hmac.compare_digest(expected_sig, signature.lower())
    
    @staticmethod
    def create_api_key() -> Tuple[str, str]:
        """
        Create API key pair (key_id, secret)
        
        Returns:
            Tuple of (api_key_id, api_secret)
        """
        key_id = f"ak_{secrets.token_hex(16)}"
        secret = secrets.token_hex(32)
        return key_id, secret
    
    @staticmethod
    def hash_api_secret(secret: str, salt: Optional[str] = None) -> str:
        """
        Hash API secret for storage
        
        Args:
            secret: Original secret
            salt: Optional salt
            
        Returns:
            Hashed secret
        """
        if salt is None:
            salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac(
            'sha256',
            secret.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex() + ":" + salt


def create_request_auth_header(
    method: str,
    path: str,
    body: str,
    secret_key: str,
    user_id: str
) -> dict:
    """
    Create authentication headers for API request
    
    Returns:
        Dictionary of headers
    """
    timestamp = int(time.time())
    signature = HMACUtils.create_request_signature(
        method, path, body, timestamp, secret_key
    )
    
    return {
        "X-User-ID": user_id,
        "X-Timestamp": str(timestamp),
        "X-Signature": signature
    }
