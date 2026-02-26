"""
Pydantic schemas for user data validation and serialization.
File: backend/app/schemas/user.py
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
import re


# Shared properties
class UserBase(BaseModel):
    """Base user schema with common attributes."""
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v


# Schema for user creation
class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


# Schema for user update
class UserUpdate(BaseModel):
    """Schema for user profile update."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v


# Schema for login
class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


# Schema for token response
class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""
    sub: str
    exp: int
    type: str


# Schema for password change
class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


# Schema for password reset request
class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


# Schema for password reset
class PasswordReset(BaseModel):
    """Schema for password reset."""
    token: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


# Schema for email verification
class EmailVerification(BaseModel):
    """Schema for email verification."""
    token: str


# Schema for user response (excludes sensitive data)
class UserResponse(UserBase):
    """Schema for user response (what's sent to client)."""
    id: str
    role: str
    tier: str
    credits_remaining: int
    email_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Schema for user profile (includes all user data)
class UserProfile(UserResponse):
    """Schema for full user profile (admin use)."""
    last_login: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    failed_login_attempts: int
    metadata: Dict[str, Any]