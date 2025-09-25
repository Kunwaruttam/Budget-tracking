from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid
from src.core.database import get_db
from src.core.security import (
    verify_password, hash_password, create_access_token, 
    create_email_verification_token, verify_email_token, validate_password_strength,
    create_password_reset_token, verify_password_reset_token
)
from src.core.settings import settings
from src.core.email import email_service
from .models import User
from .schemas import (
    UserCreate, UserLogin, UserResponse, Token, 
    EmailVerificationRequest, ResendVerificationRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
)
from .dependencies import get_active_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=dict)
def register(
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user and send verification email."""
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered"
        )
    
    # Validate password strength
    is_valid, message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Create new user (unverified)
    hashed_password = hash_password(user_data.password)
    db_user = User(
        id=str(uuid.uuid4()),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email.lower(),
        hashed_password=hashed_password,
        is_verified=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Send verification email in background
    verification_token = create_email_verification_token(db_user.email)
    background_tasks.add_task(
        email_service.send_verification_email,
        db_user.email,
        db_user.first_name,
        verification_token
    )
    
    return {
        "message": "Registration successful! Please check your email to verify your account.",
        "email": db_user.email
    }

@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token."""
    # Find user
    user = db.query(User).filter(User.email == user_credentials.email.lower()).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account has been deactivated. Please contact support."
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please verify your email address before logging in."
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Update last login
    from sqlalchemy import func
    user.last_login = func.now()
    db.commit()
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user
    }

@router.post("/verify-email")
def verify_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify user email address."""
    email = verify_email_token(verification_data.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        return {"message": "Email address is already verified"}
    
    # Mark user as verified
    user.is_verified = True
    db.commit()
    
    return {"message": "Email address verified successfully! You can now log in."}

@router.post("/resend-verification")
def resend_verification(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Resend email verification."""
    user = db.query(User).filter(User.email == request.email.lower()).first()
    
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email address is registered, a verification email has been sent."}
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already verified"
        )
    
    # Send new verification email
    verification_token = create_email_verification_token(user.email)
    background_tasks.add_task(
        email_service.send_verification_email,
        user.email,
        user.first_name,
        verification_token
    )
    
    return {"message": "Verification email sent successfully!"}

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_active_user)):
    """Get current user information."""
    return current_user

@router.post("/logout")
def logout():
    """Logout user (client should discard token)."""
    return {"message": "Successfully logged out"}

@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset."""
    user = db.query(User).filter(User.email == request.email.lower()).first()
    
    # Always return success message for security (don't reveal if email exists)
    if not user:
        return {"message": "If the email address is registered, a password reset email has been sent."}
    
    if not user.is_active:
        return {"message": "If the email address is registered, a password reset email has been sent."}
    
    # Send password reset email
    reset_token = create_password_reset_token(user.email)
    background_tasks.add_task(
        email_service.send_password_reset_email,
        user.email,
        user.first_name,
        reset_token
    )
    
    return {"message": "If the email address is registered, a password reset email has been sent."}

@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password with token."""
    email = verify_password_reset_token(request.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account has been deactivated. Please contact support."
        )
    
    # Validate new password strength
    is_valid, message = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Update password
    user.hashed_password = hash_password(request.new_password)
    db.commit()
    
    return {"message": "Password reset successfully! You can now log in with your new password."}

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Change user password (requires current password)."""
    
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check if new password is different from current password
    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Validate new password strength
    is_valid, message = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Update password
    current_user.hashed_password = hash_password(request.new_password)
    db.commit()
    
    return {
        "success": True,
        "message": "Password changed successfully!"
    }