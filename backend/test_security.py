"""
Test script for security module
测试安全模块功能
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from security import (
    CryptoUtils, HashUtils, SignatureUtils, HMACUtils,
    ensure_keypair_exists, sign_document_package, verify_document_package
)


def test_crypto_utils():
    """Test encryption/decryption"""
    print("\n[Test] CryptoUtils - AES-256-GCM Encryption")
    
    plaintext = b"Hello, this is a secret message!"
    password = "test_password_123"
    
    # Test password-based encryption
    encrypted = CryptoUtils.encrypt_file(plaintext, password)
    print(f"  Original: {plaintext}")
    print(f"  Encrypted package keys: {list(encrypted.keys())}")
    
    # Decrypt
    decrypted = CryptoUtils.decrypt_file(encrypted, password)
    print(f"  Decrypted: {decrypted}")
    assert decrypted == plaintext, "Decryption failed!"
    print("  [PASS] Encryption/Decryption successful!")
    
    # Test with master key
    master_key = CryptoUtils.generate_master_key()
    ciphertext, nonce = CryptoUtils.encrypt_with_master_key(plaintext, master_key)
    decrypted2 = CryptoUtils.decrypt_with_master_key(ciphertext, master_key, nonce)
    assert decrypted2 == plaintext, "Master key decryption failed!"
    print("  [PASS] Master key encryption successful!")


def test_hash_utils():
    """Test hashing functions"""
    print("\n[Test] HashUtils - SHA-256 Hashing")
    
    test_data = "Test document content"
    
    # Basic hash
    hash1 = HashUtils.sha256(test_data)
    hash2 = HashUtils.sha256(test_data)
    assert hash1 == hash2, "Same data should produce same hash!"
    print(f"  SHA-256 Hash: {hash1[:32]}...")
    
    # File hash
    file_content = b"File content for testing"
    file_hash = HashUtils.sha256_file(file_content)
    print(f"  File Hash: {file_hash[:32]}...")
    
    # Verification
    assert HashUtils.verify_hash(test_data, hash1), "Hash verification failed!"
    print("  [PASS] Hash verification successful!")
    
    # Multiple checksums
    checksums = HashUtils.generate_checksum_pairs(test_data)
    print(f"  Checksums generated: {list(checksums.keys())}")
    print("  [PASS] Multiple checksums successful!")


def test_signature_utils():
    """Test digital signatures"""
    print("\n[Test] SignatureUtils - RSA Digital Signatures")
    
    # Generate keypair
    private_key, public_key = SignatureUtils.generate_keypair()
    print("  Generated RSA keypair (2048 bits)")
    
    # Sign data
    document_hash = "abc123def456"
    signature = SignatureUtils.sign_and_encode(document_hash.encode(), private_key)
    print(f"  Signature (base64): {signature[:40]}...")
    
    # Verify signature
    is_valid = SignatureUtils.verify_from_encoded(document_hash.encode(), signature, public_key)
    assert is_valid, "Signature verification failed!"
    print("  [PASS] Signature verification successful!")
    
    # Test tampering detection
    tampered_data = "tampered_hash"
    is_valid_tampered = SignatureUtils.verify_from_encoded(tampered_data.encode(), signature, public_key)
    assert not is_valid_tampered, "Should detect tampering!"
    print("  [PASS] Tampering detection successful!")
    
    # Test document package
    doc_id = "doc_12345"
    package = sign_document_package(doc_id, document_hash, private_key)
    print(f"  Document package created for: {doc_id}")
    
    verification = verify_document_package(package, public_key)
    assert verification["is_valid"], "Package verification failed!"
    print("  [PASS] Document package verification successful!")


def test_hmac_utils():
    """Test HMAC authentication"""
    print("\n[Test] HMACUtils - HMAC Authentication")
    
    secret_key = "my_secret_key"
    message = "Request data to authenticate"
    
    # Compute HMAC
    hmac_sig = HMACUtils.compute_hmac(message, secret_key)
    print(f"  HMAC: {hmac_sig[:32]}...")
    
    # Verify HMAC
    is_valid = HMACUtils.verify_hmac(message, hmac_sig, secret_key)
    assert is_valid, "HMAC verification failed!"
    print("  [PASS] HMAC verification successful!")
    
    # Test with different algorithms
    for algo in ["sha256", "sha384", "sha512"]:
        mac = HMACUtils.compute_hmac(message, secret_key, algorithm=algo)
        assert HMACUtils.verify_hmac(message, mac, secret_key, algorithm=algo)
    print("  [PASS] Multiple algorithms successful!")
    
    # Test auth token
    token = HMACUtils.create_auth_token("user123", secret_key, expires_in=3600)
    print(f"  Auth token created for user123")
    
    is_valid_token, reason = HMACUtils.verify_auth_token(token, secret_key)
    assert is_valid_token, f"Token verification failed: {reason}"
    print("  [PASS] Auth token verification successful!")
    
    # Test request signature
    method, path, body = "POST", "/api/documents", '{"test": "data"}'
    timestamp = 1234567890
    req_sig = HMACUtils.create_request_signature(method, path, body, timestamp, secret_key)
    
    is_valid_req = HMACUtils.verify_request_signature(
        method, path, body, timestamp, req_sig, secret_key
    )
    assert is_valid_req, "Request signature verification failed!"
    print("  [PASS] Request signature verification successful!")


def test_keypair_file_operations():
    """Test keypair file operations"""
    print("\n[Test] Keypair File Operations")
    
    temp_dir = Path(__file__).parent / "keys" / "test"
    temp_dir.mkdir(exist_ok=True, parents=True)
    
    private_path = temp_dir / "test_private.pem"
    public_path = temp_dir / "test_public.pem"
    
    # Generate and save
    private_key, public_key = SignatureUtils.generate_keypair()
    SignatureUtils.save_private_key(private_key, str(private_path))
    SignatureUtils.save_public_key(public_key, str(public_path))
    print(f"  Saved keypair to {temp_dir}")
    
    # Load and verify
    loaded_private = SignatureUtils.load_private_key(str(private_path))
    loaded_public = SignatureUtils.load_public_key(str(public_path))
    
    # Sign with loaded key
    test_data = b"Test data for loaded key"
    signature = SignatureUtils.sign(test_data, loaded_private)
    is_valid = SignatureUtils.verify(test_data, signature, loaded_public)
    assert is_valid, "Loaded key verification failed!"
    print("  [PASS] Keypair file operations successful!")
    
    # Cleanup
    private_path.unlink()
    public_path.unlink()


def main():
    """Run all security tests"""
    print("=" * 60)
    print(" Secure Corporate RAG - Security Module Tests")
    print("=" * 60)
    
    try:
        test_crypto_utils()
        test_hash_utils()
        test_signature_utils()
        test_hmac_utils()
        test_keypair_file_operations()
        
        print("\n" + "=" * 60)
        print(" All security tests PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
