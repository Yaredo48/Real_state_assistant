"""
Property models for real estate properties.
File: backend/app/models/property.py
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.core.database import Base
from app.core.base import BaseModel


class Property(BaseModel):
    """
    Real estate property model.
    Groups documents and reports for a specific property.
    """
    
    __tablename__ = "properties"
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Property details
    property_address = Column(Text)
    property_city = Column(String(100), index=True)
    property_zone = Column(String(100))
    property_description = Column(Text)
    
    # Status
    status = Column(String(50), default="draft", index=True)  # draft, analyzing, completed
    
    # Property metadata
    metadata = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="properties")
    documents = relationship("Document", back_populates="property", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="property", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Property {self.property_address or self.id}>"
    
    @property
    def document_count(self):
        """Get number of documents for this property."""
        return len(self.documents)
    
    @property
    def document_types(self):
        """Get list of document types for this property."""
        return list(set(doc.document_type for doc in self.documents if doc.document_type))
    

# Add to Property class relationships
analysis_jobs = relationship("AnalysisJob", back_populates="property", cascade="all, delete-orphan")
reports = relationship("Report", back_populates="property", cascade="all, delete-orphan")