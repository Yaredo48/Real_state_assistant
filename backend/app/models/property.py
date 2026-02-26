"""
Property models for real estate properties.
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.core.database import Base


class Property(Base):
    """Real estate property model."""
    
    __tablename__ = "properties"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    property_address = Column(Text)
    property_city = Column(String(100))
    property_zone = Column(String(100))
    property_description = Column(Text)
    status = Column(String(50), default="draft")  # draft, analyzing, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="properties")
    documents = relationship("Document", back_populates="property", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="property", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Property {self.id}>"