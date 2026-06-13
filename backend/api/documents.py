"""
Document API routes for Secure Corporate RAG Assistant
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
from services import DocumentService, AuditService, get_current_active_user, RBACService
from models import User, Document
from .models import DocumentResponse, DocumentMetadata, DocumentVerifyResponse, AccessCheckResponse


router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    target_department: str = "Public",
    access_level_required: str = "L4_Staff",
    description: str = None,
    sign_document: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and encrypt a document
    
    - File will be encrypted using AES-256-GCM
    - SHA-256 hash is computed for integrity verification
    - Document can be digitally signed by admin/director
    """
    # Check upload permission
    if not RBACService.can_upload_to_department(current_user, target_department):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to upload documents to {target_department} department"
        )
    
    # Read file content
    file_content = await file.read()
    
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded"
        )
    
    try:
        doc_service = DocumentService()
        document, metadata = doc_service.upload_document(
            db=db,
            file_content=file_content,
            filename=file.filename,
            owner=current_user,
            target_department=target_department,
            access_level_required=access_level_required,
            description=description,
            sign_document=sign_document and RBACService.can_sign_documents(current_user)
        )
        
        return {
            "message": "Document uploaded successfully",
            "document": document.to_dict(),
            "metadata": metadata
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all documents accessible to current user"""
    doc_service = DocumentService()
    documents = doc_service.list_accessible_documents(db, current_user)
    return [doc.to_dict() for doc in documents]


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get document metadata"""
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check access permission
    allowed, reason = RBACService.check_document_access(current_user, document)
    if not allowed:
        # Log access attempt
        RBACService.log_access_attempt(db, current_user, document, False, reason)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )
    
    return document.to_dict()


@router.get("/{doc_id}/download")
async def download_document(
    request: Request,
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download and decrypt document"""
    client_ip = request.client.host
    
    try:
        doc_service = DocumentService()
        file_content, document = doc_service.download_document(
            db=db,
            doc_id=doc_id,
            user=current_user,
            ip_address=client_ip
        )
        
        # Determine content type
        content_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'csv': 'text/csv',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xls': 'application/vnd.ms-excel',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        }
        
        content_type = content_types.get(document.file_type, 'application/octet-stream')
        
        return Response(
            content=file_content,
            media_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{document.original_filename}"'
            }
        )
    
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{doc_id}/verify", response_model=DocumentVerifyResponse)
def verify_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Verify document integrity and signature"""
    doc_service = DocumentService()
    
    try:
        result = doc_service.verify_document_integrity(
            db=db,
            doc_id=doc_id,
            user=current_user
        )
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{doc_id}/sign")
def sign_document(
    doc_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Sign a document (admin/director only)"""
    if not RBACService.can_sign_documents(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to sign documents"
        )
    
    doc_service = DocumentService()
    
    try:
        document = doc_service.sign_document(
            db=db,
            doc_id=doc_id,
            signer=current_user,
            force=force
        )
        return {
            "message": "Document signed successfully",
            "document": document.to_dict(include_signature=True)
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document (owner or admin only)"""
    doc_service = DocumentService()
    
    try:
        success = doc_service.delete_document(
            db=db,
            doc_id=doc_id,
            user=current_user
        )
        return {"message": "Document deleted successfully", "success": success}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/access-check", response_model=AccessCheckResponse)
def check_access(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check if current user can access a document"""
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    allowed, reason = RBACService.check_document_access(current_user, document)
    return {"allowed": allowed, "reason": reason}
