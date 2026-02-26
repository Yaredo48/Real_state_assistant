"""
Document models for uploaded property documents.
File: backend/app/models/document.py
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.core.database import Base
from app.core.base import BaseModel


class Document(BaseModel):
    """
    Property document model.
    Stores metadata and processing status for uploaded documents.
    """
    
    __tablename__ = "documents"
    
    # Foreign keys
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Document metadata
    document_type = Column(String(50), index=True)  # title_deed, sale_agreement, tax_record, lease
    filename = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    storage_path = Column(Text)
    
    # Processing status
    status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    processing_progress = Column(Integer, default=0)  # 0-100
    
    # Extracted content
    extracted_text = Column(Text)
    ocr_used = Column(Boolean, default=False)
    ocr_confidence = Column(Float)
    page_count = Column(Integer)
    
    # Timestamps
    processed_at = Column(DateTime, nullable=True)
    
    # Metadata for additional info
    extra_data = Column(JSON, default={})
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    property = relationship("Property", back_populates="documents")
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    risk_findings = relationship("RiskFinding", back_populates="document")
    
    def __repr__(self):
        return f"<Document {self.filename} ({self.status})>"


class DocumentChunk(BaseModel):
    """
    Document chunks for RAG processing.
    Stores text segments with their embeddings.
    """
    
    __tablename__ = "document_chunks"
    
    # Foreign keys
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Chunk data
    chunk_index = Column(Integer)
    chunk_text = Column(Text)
    embedding_id = Column(String(255), nullable=True)  # Reference to vector DB
    page_number = Column(Integer)
    section_title = Column(String(255), nullable=True)
    
    # Chunk metadata
    token_count = Column(Integer)
    extra_data = Column(JSON, default={})
    
    # Relationships
    document = relationship("Document", back_populates="chunks")