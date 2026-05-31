"""
Hash utilities for Secure Corporate RAG Assistant
SHA-256 hashing for document integrity verification
"""

import hashlib
import hmac
from typing import Union


class HashUtils:
    """SHA-256 hashing utilities for document integrity"""
    
    @staticmethod
    def sha256(data: Union[str, bytes]) -> str:
        """
        Calculate SHA-256 hash of data
        
        Args:
            data: String or bytes to hash
            
        Returns:
            Hexadecimal hash string
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def sha256_file(file_content: bytes) -> str:
        """
        Calculate SHA-256 hash of file content
        
        Args:
            file_content: Raw file bytes
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(file_content).hexdigest()
    
    @staticmethod
    def sha256_file_chunked(filepath: str, chunk_size: int = 8192) -> str:
        """
        Calculate SHA-256 hash of file using chunked reading
        
        Args:
            filepath: Path to file
            chunk_size: Size of chunks to read
            
        Returns:
            Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def verify_hash(data: Union[str, bytes], expected_hash: str) -> bool:
        """
        Verify data matches expected hash
        
        Args:
            data: Data to verify
            expected_hash: Expected hash value
            
        Returns:
            True if hash matches
        """
        actual_hash = HashUtils.sha256(data)
        return hmac.compare_digest(actual_hash, expected_hash.lower())
    
    @staticmethod
    def verify_file_hash(file_content: bytes, expected_hash: str) -> bool:
        """
        Verify file content matches expected hash
        
        Args:
            file_content: File bytes
            expected_hash: Expected SHA-256 hash
            
        Returns:
            True if hash matches
        """
        return HashUtils.verify_hash(file_content, expected_hash)
    
    @staticmethod
    def generate_checksum_pairs(data: str) -> dict:
        """
        Generate multiple hash checksums for enhanced security
        
        Args:
            data: String data to hash
            
        Returns:
            Dictionary with different hash types
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return {
            "sha256": hashlib.sha256(data).hexdigest(),
            "sha384": hashlib.sha384(data).hexdigest(),
            "sha512": hashlib.sha512(data).hexdigest(),
            "md5": hashlib.md5(data).hexdigest()
        }
    
    @staticmethod
    def generate_document_manifest(documents: list) -> dict:
        """
        Generate a manifest of document hashes
        
        Args:
            documents: List of (doc_id, file_content) tuples
            
        Returns:
            Manifest dictionary
        """
        manifest = {
            "version": "1.0",
            "total_documents": len(documents),
            "documents": []
        }
        
        for doc_id, content in documents:
            manifest["documents"].append({
                "id": doc_id,
                "sha256": HashUtils.sha256_file(content),
                "size": len(content)
            })
        
        # Generate manifest hash
        manifest_str = str(manifest["documents"])
        manifest["manifest_hash"] = HashUtils.sha256(manifest_str)
        
        return manifest


def compute_file_integrity_hash(filepath: str) -> str:
    """Convenience function to compute file integrity hash"""
    with open(filepath, 'rb') as f:
        content = f.read()
    return HashUtils.sha256_file(content)


def create_integrity_report(files: list) -> dict:
    """
    Create integrity report for multiple files
    
    Args:
        files: List of file paths
        
    Returns:
        Integrity report dictionary
    """
    report = {
        "timestamp": None,  # Will be set by caller
        "total_files": len(files),
        "files": []
    }
    
    for filepath in files:
        try:
            hash_value = compute_file_integrity_hash(filepath)
            report["files"].append({
                "path": filepath,
                "sha256": hash_value,
                "status": "ok"
            })
        except Exception as e:
            report["files"].append({
                "path": filepath,
                "error": str(e),
                "status": "error"
            })
    
    # Overall integrity hash
    report["integrity_hash"] = HashUtils.sha256(str(report["files"]))
    return report
