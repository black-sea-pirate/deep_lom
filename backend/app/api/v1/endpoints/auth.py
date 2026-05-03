"""
Authentication Endpoints

Thin HTTP layer — all business logic lives in app.services.auth_service.
Refresh token is stored in an httpOnly cookie; access token is returned in the body.
"""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.core.exceptions import AuthenticationException, ValidationException
from app.core.security import verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    AuthResponse,
    Token,
    PasswordChange,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerifyRequest,
)
from app.schemas.common import MessageResponse
from app.services import auth_service

router = APIRouter()

# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

COOKIE_NAME = "refresh_token"
COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600  # seconds


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,   # False in local dev, True in production
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/api/v1/auth",         # Cookie sent only to auth routes
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/api/v1/auth")


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=AuthResponse)
async def register(
    response: Response,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    user, access_token, refresh_token = await auth_service.register_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
    )
    _set_refresh_cookie(response, refresh_token)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=AuthResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user, access_token, refresh_token = await auth_service.authenticate_user(
        db=db,
        email=form_data.username,
        password=form_data.password,
    )
    _set_refresh_cookie(response, refresh_token)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
):
    _clear_refresh_cookie(response)
    return MessageResponse(message="Successfully logged out")


# ---------------------------------------------------------------------------
# Token refresh (reads cookie, no body required)
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(COOKIE_NAME)
    if not raw_token:
        raise AuthenticationException(
            message="Refresh token отсутствует",
            details={"reason": "no_cookie"},
        )

    new_access, new_refresh = await auth_service.refresh_tokens(db, raw_token)
    _set_refresh_cookie(response, new_refresh)
    return Token(access_token=new_access)


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_data.first_name is not None:
        current_user.first_name = user_data.first_name
    if user_data.last_name is not None:
        current_user.last_name = user_data.last_name
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise ValidationException(
            message="Неверный текущий пароль",
            field="current_password",
        )
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    return MessageResponse(message="Password changed successfully")


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    data: EmailVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify email with 6-digit code. Requires valid access token."""
    await auth_service.verify_email(db, current_user.id, data.code)
    return MessageResponse(message="Email подтверждён.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resend verification code. Rate-limited: once per minute."""
    await auth_service.resend_verification(db, current_user.id)
    return MessageResponse(message="Код отправлен повторно.")


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a 6-digit reset code to the user's email.
    Always returns 200 to prevent user enumeration.
    """
    await auth_service.request_password_reset(db, data.email)
    return MessageResponse(message="Если email зарегистрирован, код отправлен.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify the 6-digit code and set the new password.
    """
    await auth_service.confirm_password_reset(
        db=db,
        email=data.email,
        code=data.code,
        new_password=data.new_password,
    )
    return MessageResponse(message="Пароль успешно изменён.")
