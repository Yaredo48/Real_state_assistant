"""
Document management routes.
File: backend/app/api/routes/documents.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.config import settings
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentDetailResponse,
    DocumentUploadResponse,
    DocumentProcessRequest,
    DocumentProcessResponse,
    DocumentListResponse,
    DocumentUpdate
)
from app.models.document import Document
from app.models.property import Property
from app.models.user import User
from app.api.dependencies import get_current_active_user, require_credits
from app.services.file_service import file_service
from app.services.task_queue import task_queue

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    file: UploadFile = File(...),
    property_id: Optional[UUID] = None
):
    """
    Upload a document for processing.
    
    Args:
        db: Database session
        current_user: Authenticated user
        file: Uploaded file
        property_id: Optional property ID to associate document with
    
    Returns:
        Upload response with document ID
    """
    # Validate file
    is_valid, error_msg = await file_service.validate_file(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # If property_id provided, verify it belongs to user
    if property_id:
        property = db.query(Property).filter(
            Property.id == property_id,
            Property.user_id == current_user.id
        ).first()
        
        if not property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
    
    try:
        # Save file
        storage_path, file_size = await file_service.save_file(
            file=file,
            user_id=str(current_user.id),
            property_id=str(property_id) if property_id else None
        )
        
        # Create document record
        document = Document(
            user_id=current_user.id,
            property_id=property_id,
            filename=file.filename,
            file_size=file_size,
            mime_type=file.content_type,
            storage_path=storage_path,
            status="pending"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Add to processing queue
        task_id = await task_queue.add_task(
            task_type="process_document",
            task_data={
                "file_path": storage_path,
                "document_id": str(document.id),
                "user_id": str(current_user.id)
            }
        )
        
        logger.info(f"Document {document.id} uploaded, processing task {task_id}")
        
        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            status=document.status,
            message="Document uploaded successfully and queued for processing"
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


@router.post("/upload/multiple", response_model=List[DocumentUploadResponse])
async def upload_multiple_documents(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    files: List[UploadFile] = File(...),
    property_id: Optional[UUID] = None
):
    """
    Upload multiple documents at once.
    """
    responses = []
    
    for file in files:
        try:
            response = await upload_document(
                db=db,
                current_user=current_user,
                file=file,
                property_id=property_id
            )
            responses.append(response)
        except Exception as e:
            responses.append(
                DocumentUploadResponse(
                    id=None,
                    filename=file.filename,
                    status="failed",
                    message=f"Upload failed: {str(e)}"
                )
            )
    
    return responses


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    property_id: Optional[UUID] = None,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """
    List documents for the current user.
    """
    query = db.query(Document).filter(Document.user_id == current_user.id)
    
    if property_id:
        query = query.filter(Document.property_id == property_id)
    
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    if status:
        query = query.filter(Document.status == status)
    
    total = query.count()
    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    # Calculate total pages
    pages = (total + limit - 1) // limit if limit > 0 else 1
    
    return DocumentListResponse(
        items=documents,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        size=limit,
        pages=pages
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get document details by ID.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    document_in: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update document metadata.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update fields
    update_data = document_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a document.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file from storage
    if document.storage_path:
        file_service.delete_file(document.storage_path)
    
    # Delete from database
    db.delete(document)
    db.commit()


@router.post("/{document_id}/reprocess", response_model=DocumentProcessResponse)
async def reprocess_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_credits(1))
):
    """
    Reprocess a document (consumes 1 credit).
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Deduct credit
    current_user.credits_remaining -= 1
    db.commit()
    
    # Add to processing queue
    task_id = await task_queue.add_task(
        task_type="process_document",
        task_data={
            "file_path": document.storage_path,
            "document_id": str(document.id),
            "user_id": str(current_user.id)
        }
    )
    
    return DocumentProcessResponse(
        job_id=task_id,
        document_count=1,
        estimated_time=30,
        status="queued"
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get download URL for document.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if not document.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found"
        )
    
    # In production, generate presigned URL
    # For now, return file path
    return {
        "filename": document.filename,
        "url": f"/api/documents/{document_id}/file"
    }


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get status of a background task.
    """
    status = await task_queue.get_task_status(task_id)
    return status