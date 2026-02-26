"""
Authentication routes for user registration, login, and token management.
File: backend/app/api/routes/auth.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import jwt, JWTError
from typing import Any

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    generate_verification_token,
    generate_password_reset_token,
    verify_password_reset_token
)
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    EmailVerification
)
from app.models.user import User
from app.api.routes.dependencies import get_current_user, get_current_active_user
from app.core.config import settings

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate
) -> Any:
    """
    Register a new user.
    
    Args:
        db: Database session
        user_in: User registration data
    
    Returns:
        Created user
    """
    # Check if user exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    # Create new user
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        phone=user_in.phone,
        company=user_in.company,
        verification_token=generate_verification_token(),
        credits_remaining=5  # Give 5 free credits on registration
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # TODO: Send verification email
    
    return user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login.
    
    Args:
        request: FastAPI request object
        db: Database session
        form_data: OAuth2 form data
    
    Returns:
        Access and refresh tokens
    """
    # Get user by email
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Check if user exists and password is correct
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Please reset your password or contact support."
        )
    
    # Update login info
    user.last_login = datetime.utcnow()
    user.last_login_ip = request.client.host
    user.failed_login_attempts = 0
    db.commit()
    
    # Create tokens
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token.
    
    Args:
        request: FastAPI request with refresh token in Authorization header
        db: Database session
    
    Returns:
        New access and refresh tokens
    """
    # Get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication header"
        )
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Decode token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        return {
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer"
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Logout user (client-side only, token becomes invalid after expiry).
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.put("/me/password")
async def change_password(
    *,
    db: Session = Depends(get_db),
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Change user password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/password-reset/request")
async def request_password_reset(
    *,
    db: Session = Depends(get_db),
    reset_data: PasswordResetRequest
) -> Any:
    """
    Request password reset.
    """
    # Get user
    user = db.query(User).filter(User.email == reset_data.email).first()
    if user:
        # Generate reset token
        reset_token = generate_password_reset_token(user.email)
        
        # TODO: Send reset email
        pass
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    *,
    db: Session = Depends(get_db),
    reset_data: PasswordReset
) -> Any:
    """
    Confirm password reset with token.
    """
    # Verify token
    email = verify_password_reset_token(reset_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Update password
    user.password_hash = get_password_hash(reset_data.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    
    return {"message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(
    *,
    db: Session = Depends(get_db),
    verification_data: EmailVerification
) -> Any:
    """
    Verify user email with token.
    """
    # Get user by verification token
    user = db.query(User).filter(
        User.verification_token == verification_data.token
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    # Mark email as verified
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    user.verification_token = None
    db.commit()
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Resend verification email.
    """
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Generate new token
    current_user.verification_token = generate_verification_token()
    db.commit()
    
    # TODO: Send verification email
    
    return {"message": "Verification email sent"}