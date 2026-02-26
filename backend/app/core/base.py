"""
Base classes and utilities for all models.
File: backend/app/core/base.py
"""

from sqlalchemy import Column, DateTime, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from datetime import datetime

from app.core.database import Base


class BaseModel(Base):
    """
    Abstract base model with common fields.
    All database models should inherit from this.
    """
    
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def dict(self):
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TimestampMixin:
    """Mixin for timestamp fields."""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    def soft_delete(self):
        """Mark record as deleted."""
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore soft-deleted record."""
        self.deleted_at = None
    
    @property
    def is_deleted(self):
        """Check if record is deleted."""
        return self.deleted_at is not None