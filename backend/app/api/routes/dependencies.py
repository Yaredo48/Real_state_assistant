"""
FastAPI dependencies for authentication and authorization.
File: backend/app/api/dependencies.py
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/login"
)


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        db: Database session
        token: JWT token
    
    Returns:
        User object
    
    Raises:
        HTTPException 401: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        token_data = TokenPayload(**payload)
        
        # Check token type
        if token_data.type != "access":
            raise credentials_exception
        
        user_id = token_data.sub
        
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is locked"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and verify email is verified.
    
    Args:
        current_user: Authenticated user
    
    Returns:
        User object
    
    Raises:
        HTTPException 403: If email not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    
    return current_user


def require_roles(required_roles: List[str]):
    """
    Dependency factory to require specific user roles.
    
    Args:
        required_roles: List of allowed roles
    
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} not allowed. Required: {required_roles}"
            )
        return current_user
    
    return role_checker


def require_tiers(required_tiers: List[str]):
    """
    Dependency factory to require specific user tiers.
    
    Args:
        required_tiers: List of allowed tiers
    
    Returns:
        Dependency function
    """
    async def tier_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.tier not in required_tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tier {current_user.tier} not allowed. Required: {required_tiers}"
            )
        return current_user
    
    return tier_checker


def require_credits(min_credits: int = 1):
    """
    Dependency factory to require minimum credits.
    
    Args:
        min_credits: Minimum credits required
    
    Returns:
        Dependency function
    """
    async def credit_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.credits_remaining < min_credits:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {min_credits}, Available: {current_user.credits_remaining}"
            )
        return current_user
    
    return credit_checker


def get_optional_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Used for endpoints that work for both authenticated and unauthenticated users.
    
    Args:
        db: Database session
        token: Optional JWT token
    
    Returns:
        User object or None
    """
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        token_data = TokenPayload(**payload)
        
        if token_data.type != "access":
            return None
        
        user_id = token_data.sub
        user = db.query(User).filter(User.id == user_id).first()
        
        if user and user.is_active:
            return user
        
    except JWTError:
        pass
    
    return None