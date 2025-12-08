"""
Authentication Endpoints

Handles user registration, login, logout, and token refresh.
Compatible with frontend auth.service.ts
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_db, get_current_user
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.exceptions import (
    ConflictException,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
)
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    AuthResponse,
    Token,
    TokenWithRefresh,
    RefreshTokenRequest,
    PasswordChange,
)
from app.schemas.common import MessageResponse

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    
    Returns access token and user info on success.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise ConflictException(
            message="Пользователь с таким email уже зарегистрирован",
            field="email",
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Generate token
    access_token = create_access_token(subject=str(user.id))
    
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login user with email and password.
    
    Uses OAuth2PasswordRequestForm for compatibility with frontend FormData.
    Returns access token and user info.
    """
    # Find user by email (OAuth2 uses 'username' field)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationException(
            message="Неверный email или пароль",
            details={"field": "credentials"},
        )
    
    if not user.is_active:
        raise AuthorizationException(
            message="Аккаунт деактивирован",
            resource="user",
        )
    
    # Generate token
    access_token = create_access_token(subject=str(user.id))
    
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
):
    """
    Logout current user.
    
    In a stateless JWT setup, logout is handled client-side by removing the token.
    This endpoint is for consistency with frontend expectations.
    """
    # In production with Redis, you could blacklist the token here
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user info.
    """
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_info(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile (first name, last name).
    """
    # Update fields if provided
    if user_data.first_name is not None:
        current_user.first_name = user_data.first_name
    if user_data.last_name is not None:
        current_user.last_name = user_data.last_name
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    """
    # Verify refresh token
    payload = verify_token(request.refresh_token, token_type="refresh")
    if not payload:
        raise AuthenticationException(
            message="Недействительный refresh token",
            details={"reason": "token_invalid_or_expired"},
        )
    
    # Check if user still exists and is active
    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise AuthenticationException(
            message="Пользователь не найден или деактивирован",
            details={"reason": "user_inactive"},
        )
    
    # Generate new access token
    access_token = create_access_token(subject=str(user.id))
    
    return Token(access_token=access_token)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password for current user.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise ValidationException(
            message="Неверный текущий пароль",
            field="current_password",
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return MessageResponse(message="Password changed successfully")
