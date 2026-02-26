"""
Pydantic schemas for document data validation and serialization.
File: backend/app/schemas/document.py
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import enum


class DocumentType(str, enum.Enum):
    """Document type enumeration."""
    TITLE_DEED = "title_deed"
    SALE_AGREEMENT = "sale_agreement"
    TAX_RECORD = "tax_record"
    LEASE = "lease"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    """Document processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Base document schema
class DocumentBase(BaseModel):
    """Base document schema with common attributes."""
    document_type: Optional[DocumentType] = None
    filename: str
    file_size: int
    mime_type: str


# Schema for document upload response
class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    id: UUID
    filename: str
    document_type: Optional[str] = None
    status: str
    upload_url: Optional[str] = None
    message: str = "Document uploaded successfully"


# Schema for document creation
class DocumentCreate(BaseModel):
    """Schema for creating a document record."""
    property_id: UUID
    document_type: Optional[DocumentType] = None
    filename: str
    file_size: int
    mime_type: str
    
    @validator('file_size')
    def validate_file_size(cls, v):
        """Validate file size (max 25MB)."""
        max_size = 25 * 1024 * 1024  # 25MB
        if v > max_size:
            raise ValueError(f'File size exceeds maximum of {max_size} bytes')
        return v


# Schema for document update
class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""
    document_type: Optional[DocumentType] = None
    status: Optional[DocumentStatus] = None
    metadata: Optional[Dict[str, Any]] = None


# Schema for document response
class DocumentResponse(BaseModel):
    """Schema for document response (sent to client)."""
    id: UUID
    property_id: UUID
    user_id: UUID
    document_type: Optional[str] = None
    filename: str
    file_size: int
    mime_type: str
    status: str
    processing_progress: int
    page_count: Optional[int] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


# Schema for document detail (includes extracted text)
class DocumentDetailResponse(DocumentResponse):
    """Detailed document schema including extracted text."""
    extracted_text: Optional[str] = None
    ocr_used: bool = False
    ocr_confidence: Optional[float] = None


# Schema for document chunk
class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response."""
    id: UUID
    document_id: UUID
    chunk_index: int
    chunk_text: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    token_count: int
    
    class Config:
        from_attributes = True


# Schema for document processing request
class DocumentProcessRequest(BaseModel):
    """Request to start document processing."""
    document_ids: List[UUID]
    force_reprocess: bool = False


# Schema for document processing response
class DocumentProcessResponse(BaseModel):
    """Response for document processing request."""
    job_id: str
    document_count: int
    estimated_time: int  # seconds
    status: str


# Schema for document list with pagination
class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    items: List[DocumentResponse]
    total: int
    page: int
    size: int
    pages: int