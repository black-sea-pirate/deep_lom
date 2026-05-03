"""
Auth Service

Business logic for authentication:
- User registration and login
- JWT token lifecycle (access + refresh)
- Password reset via 6-digit code stored in Redis
"""

import json
import random
import string
from typing import Optional, Tuple
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationException, ConflictException, ValidationException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.services.email_service import send_password_reset_code, send_verification_email


# ---------------------------------------------------------------------------
# Redis client (lazy singleton)
# ---------------------------------------------------------------------------

_redis_client: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _redis_client


def _reset_key(email: str) -> str:
    return f"password_reset:{email.lower()}"


def _verify_key(email: str) -> str:
    return f"email_verify:{email.lower()}"


EMAIL_VERIFY_TTL = 900  # 15 minutes


# ---------------------------------------------------------------------------
# User queries
# ---------------------------------------------------------------------------

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str,
) -> Tuple[User, str, str]:
    """
    Create a new user account.

    Returns:
        (user, access_token, refresh_token)

    Raises:
        ConflictException: Email already registered.
    """
    email = email.lower()

    if await get_user_by_email(db, email):
        raise ConflictException(
            message="Пользователь с таким email уже зарегистрирован",
            field="email",
        )

    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send verification code (non-blocking — failure doesn't break registration)
    await _send_verification_code(user.email, user.first_name)

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return user, access_token, refresh_token


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> Tuple[User, str, str]:
    """
    Verify credentials and return tokens.

    Returns:
        (user, access_token, refresh_token)

    Raises:
        AuthenticationException: Wrong credentials or inactive account.
    """
    user = await get_user_by_email(db, email.lower())

    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationException(
            message="Неверный email или пароль",
            details={"field": "credentials"},
        )

    if not user.is_active:
        raise AuthenticationException(
            message="Аккаунт деактивирован",
            details={"field": "account"},
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return user, access_token, refresh_token


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

async def refresh_tokens(
    db: AsyncSession,
    raw_refresh_token: str,
) -> Tuple[str, str]:
    """
    Validate refresh token and issue a new access + refresh token pair
    (token rotation).

    Returns:
        (new_access_token, new_refresh_token)

    Raises:
        AuthenticationException: Token invalid, expired, or user inactive.
    """
    payload = verify_token(raw_refresh_token, token_type="refresh")
    if not payload:
        raise AuthenticationException(
            message="Недействительный refresh token",
            details={"reason": "token_invalid_or_expired"},
        )

    user = await get_user_by_id(db, UUID(payload.sub))
    if not user or not user.is_active:
        raise AuthenticationException(
            message="Пользователь не найден или деактивирован",
            details={"reason": "user_inactive"},
        )

    new_access = create_access_token(subject=str(user.id))
    new_refresh = create_refresh_token(subject=str(user.id))
    return new_access, new_refresh


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def _generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

async def _send_verification_code(email: str, first_name: str) -> None:
    """Generate and store a verification code, then send it by email."""
    redis = await _get_redis()
    code = _generate_code()
    payload = json.dumps({"code": code, "attempts": 0})
    await redis.setex(_verify_key(email), EMAIL_VERIFY_TTL, payload)
    await send_verification_email(email=email, code=code, first_name=first_name)


async def verify_email(db: AsyncSession, user_id: UUID, code: str) -> None:
    """
    Confirm the verification code and mark the user as verified.

    Raises:
        ValidationException: Code wrong, expired, or attempts exceeded.
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValidationException(message="Пользователь не найден.", field="code")

    if user.is_verified:
        return  # already verified — idempotent

    redis = await _get_redis()
    key = _verify_key(user.email)
    raw = await redis.get(key)

    if not raw:
        raise ValidationException(
            message="Код недействителен или истёк. Запросите новый.",
            field="code",
        )

    data = json.loads(raw)

    if data["attempts"] >= settings.PASSWORD_RESET_MAX_ATTEMPTS:
        await redis.delete(key)
        raise ValidationException(
            message="Превышено количество попыток. Запросите новый код.",
            field="code",
        )

    if data["code"] != code:
        data["attempts"] += 1
        ttl = await redis.ttl(key)
        await redis.setex(key, max(ttl, 1), json.dumps(data))
        remaining = settings.PASSWORD_RESET_MAX_ATTEMPTS - data["attempts"]
        raise ValidationException(
            message=f"Неверный код. Осталось попыток: {remaining}.",
            field="code",
        )

    user.is_verified = True
    await db.commit()
    await redis.delete(key)


async def resend_verification(db: AsyncSession, user_id: UUID) -> None:
    """
    Resend a new verification code. Rate-limited: once per minute.

    Raises:
        ValidationException: User already verified or rate limit hit.
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValidationException(message="Пользователь не найден.", field="email")

    if user.is_verified:
        raise ValidationException(
            message="Email уже подтверждён.", field="email"
        )

    redis = await _get_redis()
    key = _verify_key(user.email)
    existing = await redis.get(key)
    if existing:
        ttl = await redis.ttl(key)
        if ttl > EMAIL_VERIFY_TTL - 60:
            raise ValidationException(
                message="Подождите минуту перед повторной отправкой.", field="code"
            )

    await _send_verification_code(user.email, user.first_name)


async def request_password_reset(db: AsyncSession, email: str) -> None:
    """
    Generate a 6-digit reset code, store it in Redis, and send an email.

    Silently succeeds even if email is not registered (prevents user enumeration).
    Rate-limited: one code per minute per email.
    """
    user = await get_user_by_email(db, email.lower())
    if not user:
        return  # silent — don't leak whether email exists

    redis = await _get_redis()
    key = _reset_key(email)

    existing_raw = await redis.get(key)
    if existing_raw:
        existing = json.loads(existing_raw)
        ttl = await redis.ttl(key)
        # Block re-send if a code was issued less than 60 seconds ago
        if ttl > settings.PASSWORD_RESET_CODE_TTL - 60:
            return

    code = _generate_code()
    payload = json.dumps({"code": code, "attempts": 0})
    await redis.setex(key, settings.PASSWORD_RESET_CODE_TTL, payload)

    await send_password_reset_code(
        email=user.email,
        code=code,
        first_name=user.first_name,
    )


async def confirm_password_reset(
    db: AsyncSession,
    email: str,
    code: str,
    new_password: str,
) -> None:
    """
    Verify the code and update the user's password.

    Raises:
        ValidationException: Code is wrong, expired, or attempts exceeded.
    """
    redis = await _get_redis()
    key = _reset_key(email)

    raw = await redis.get(key)
    if not raw:
        raise ValidationException(
            message="Код недействителен или истёк. Запросите новый.",
            field="code",
        )

    data = json.loads(raw)

    if data["attempts"] >= settings.PASSWORD_RESET_MAX_ATTEMPTS:
        await redis.delete(key)
        raise ValidationException(
            message="Превышено количество попыток. Запросите новый код.",
            field="code",
        )

    if data["code"] != code:
        data["attempts"] += 1
        ttl = await redis.ttl(key)
        await redis.setex(key, max(ttl, 1), json.dumps(data))
        remaining = settings.PASSWORD_RESET_MAX_ATTEMPTS - data["attempts"]
        raise ValidationException(
            message=f"Неверный код. Осталось попыток: {remaining}.",
            field="code",
        )

    # Code is correct — update password and delete the key
    user = await get_user_by_email(db, email.lower())
    if not user:
        raise ValidationException(message="Пользователь не найден.", field="email")

    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    await redis.delete(key)
