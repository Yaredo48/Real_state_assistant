"""
Pydantic schemas for property data.
File: backend/app/schemas/property.py
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from app.schemas.document import DocumentResponse


class PropertyBase(BaseModel):
    """Base property schema."""
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_zone: Optional[str] = None
    property_description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class PropertyCreate(PropertyBase):
    """Schema for creating a property."""
    pass


class PropertyUpdate(PropertyBase):
    """Schema for updating a property."""
    status: Optional[str] = None


class PropertyResponse(PropertyBase):
    """Schema for property response."""
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PropertyDetailResponse(PropertyResponse):
    """Detailed property response with documents."""
    documents: List[DocumentResponse] = []
    
    class Config:
        from_attributes = True