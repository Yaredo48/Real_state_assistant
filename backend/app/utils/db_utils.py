"""
Database utility functions for common operations.
"""

from sqlalchemy.orm import Session
from typing import Optional, Type, TypeVar, List, Any
from uuid import UUID

# Generic type for models
ModelType = TypeVar("ModelType")


def get_by_id(db: Session, model: Type[ModelType], id: UUID) -> Optional[ModelType]:
    """Get a record by ID."""
    return db.query(model).filter(model.id == id).first()


def get_all(
    db: Session, 
    model: Type[ModelType], 
    skip: int = 0, 
    limit: int = 100,
    **filters
) -> List[ModelType]:
    """Get all records with optional filters."""
    query = db.query(model)
    
    # Apply filters
    for key, value in filters.items():
        if hasattr(model, key) and value is not None:
            query = query.filter(getattr(model, key) == value)
    
    return query.offset(skip).limit(limit).all()


def create(db: Session, model: Type[ModelType], **kwargs) -> ModelType:
    """Create a new record."""
    db_obj = model(**kwargs)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update(db: Session, db_obj: ModelType, **kwargs) -> ModelType:
    """Update an existing record."""
    for key, value in kwargs.items():
        if hasattr(db_obj, key) and value is not None:
            setattr(db_obj, key, value)
    
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(db: Session, db_obj: ModelType) -> bool:
    """Delete a record."""
    db.delete(db_obj)
    db.commit()
    return True


def soft_delete(db: Session, db_obj: ModelType) -> bool:
    """Soft delete by setting deleted_at."""
    if hasattr(db_obj, "deleted_at"):
        from datetime import datetime
        setattr(db_obj, "deleted_at", datetime.utcnow())
        db.commit()
        return True
    return False


def exists(db: Session, model: Type[ModelType], **filters) -> bool:
    """Check if a record exists with given filters."""
    query = db.query(model)
    for key, value in filters.items():
        if hasattr(model, key):
            query = query.filter(getattr(model, key) == value)
    return query.first() is not None


def count(db: Session, model: Type[ModelType], **filters) -> int:
    """Count records with optional filters."""
    query = db.query(model)
    for key, value in filters.items():
        if hasattr(model, key) and value is not None:
            query = query.filter(getattr(model, key) == value)
    return query.count()