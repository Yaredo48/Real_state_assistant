"""
User model for authentication and profile management.
File: backend/app/models/user.py
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.core.database import Base
from app.core.base import BaseModel


class User(BaseModel):
    """
    User account model.
    Stores user information and authentication data.
    """
    
    __tablename__ = "users"
    
    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile fields
    full_name = Column(String(255))
    phone = Column(String(50))
    company = Column(String(255))
    
    # Role and permissions
    role = Column(String(50), default="user", index=True)  # user, admin, agent
    tier = Column(String(50), default="basic", index=True)  # basic, pro, enterprise
    
    # Credits and usage
    credits_remaining = Column(Integer, default=0)
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    verification_token = Column(String(255), nullable=True)
    
    # Security
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Metadata
    extra_data = Column(JSON, default={})
    
    # Relationships
    properties = relationship("Property", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        """String representation."""
        return f"<User {self.email}>"
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return False
        return True
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == "admin"
    
    @property
    def is_verified(self) -> bool:
        """Check if email is verified."""
        return self.email_verified
    


# Add to User class relationships
analysis_jobs = relationship("AnalysisJob", back_populates="user", cascade="all, delete-orphan")
reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")