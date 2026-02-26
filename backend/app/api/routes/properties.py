"""
Property management routes.
File: backend/app/api/routes/properties.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyDetailResponse
)
from app.models.property import Property
from app.models.user import User
from app.api.routes.dependencies import get_current_active_user

router = APIRouter()


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    property_in: PropertyCreate
):
    """
    Create a new property.
    """
    property = Property(
        user_id=current_user.id,
        **property_in.dict()
    )
    
    db.add(property)
    db.commit()
    db.refresh(property)
    
    return property


@router.get("/", response_model=List[PropertyResponse])
async def list_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None
):
    """
    List properties for the current user.
    """
    query = db.query(Property).filter(Property.user_id == current_user.id)
    
    if status:
        query = query.filter(Property.status == status)
    
    properties = query.order_by(Property.created_at.desc()).offset(skip).limit(limit).all()
    return properties


@router.get("/{property_id}", response_model=PropertyDetailResponse)
async def get_property(
    property_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get property details by ID.
    """
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.user_id == current_user.id
    ).first()
    
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    return property


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_in: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update property details.
    """
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.user_id == current_user.id
    ).first()
    
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    # Update fields
    update_data = property_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property, field, value)
    
    db.commit()
    db.refresh(property)
    
    return property


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a property and all associated documents.
    """
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.user_id == current_user.id
    ).first()
    
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    db.delete(property)
    db.commit()


@router.post("/{property_id}/analyze", response_model=dict)
async def analyze_property(
    property_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_credits(1))
):
    """
    Start analysis for a property (consumes 1 credit).
    """
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.user_id == current_user.id
    ).first()
    
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    # Check if property has documents
    if not property.documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property has no documents to analyze"
        )
    
    # Deduct credit
    current_user.credits_remaining -= 1
    db.commit()
    
    # Update property status
    property.status = "analyzing"
    db.commit()
    
    # Queue analysis task (to be implemented in Sprint 4)
    # task_id = await task_queue.add_task(...)
    
    return {
        "message": "Analysis started",
        "property_id": str(property_id),
        "document_count": len(property.documents)
    }