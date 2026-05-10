"""
Unit tests for app.services.auth_service.

Tests the business logic layer directly (no HTTP overhead).
Email and Redis are mocked via conftest.py fixtures (autouse=True).
"""

import json
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import auth_service
from app.core.security import verify_password, verify_token


# ─── register_user ─────────────────────────────────────────────────────────────

class TestRegisterUser:

    async def test_creates_user_and_returns_tokens(self, async_session: AsyncSession):
        user, access, refresh = await auth_service.register_user(
            db=async_session,
            email="new@example.com",
            password="password123",
            first_name="Alice",
            last_name="Smith",
            role="teacher",
        )
        assert user.email == "new@example.com"
        assert user.role == "teacher"
        assert user.is_verified is False   # must start unverified
        assert verify_token(access, "access") is not None
        assert verify_token(refresh, "refresh") is not None

    async def test_email_is_normalised_to_lowercase(self, async_session: AsyncSession):
        user, _, _ = await auth_service.register_user(
            db=async_session,
            email="UPPER@EXAMPLE.COM",
            password="password123",
            first_name="Bob",
            last_name="Jones",
            role="student",
        )
        assert user.email == "upper@example.com"

    async def test_password_is_hashed(self, async_session: AsyncSession):
        user, _, _ = await auth_service.register_user(
            db=async_session,
            email="hash@example.com",
            password="plaintext",
            first_name="C",
            last_name="D",
            role="student",
        )
        assert user.hashed_password != "plaintext"
        assert verify_password("plaintext", user.hashed_password)

    async def test_duplicate_email_raises_conflict(
        self, async_session: AsyncSession, test_teacher
    ):
        from app.core.exceptions import ConflictException
        with pytest.raises(ConflictException):
            await auth_service.register_user(
                db=async_session,
                email="teacher@test.com",  # already exists from fixture
                password="password123",
                first_name="X",
                last_name="Y",
                role="teacher",
            )


# ─── authenticate_user ─────────────────────────────────────────────────────────

class TestAuthenticateUser:

    async def test_valid_credentials_return_tokens(
        self, async_session: AsyncSession, test_teacher
    ):
        user, access, refresh = await auth_service.authenticate_user(
            db=async_session,
            email="teacher@test.com",
            password="testpassword123",
        )
        assert user.email == "teacher@test.com"
        assert verify_token(access, "access") is not None
        assert verify_token(refresh, "refresh") is not None

    async def test_wrong_password_raises_auth_error(
        self, async_session: AsyncSession, test_teacher
    ):
        from app.core.exceptions import AuthenticationException
        with pytest.raises(AuthenticationException):
            await auth_service.authenticate_user(
                db=async_session,
                email="teacher@test.com",
                password="wrongpassword",
            )

    async def test_unknown_email_raises_auth_error(self, async_session: AsyncSession):
        from app.core.exceptions import AuthenticationException
        with pytest.raises(AuthenticationException):
            await auth_service.authenticate_user(
                db=async_session,
                email="ghost@test.com",
                password="anypassword",
            )

    async def test_inactive_user_raises_auth_error(
        self, async_session: AsyncSession, test_teacher
    ):
        from app.core.exceptions import AuthenticationException
        test_teacher.is_active = False
        await async_session.commit()

        with pytest.raises(AuthenticationException):
            await auth_service.authenticate_user(
                db=async_session,
                email="teacher@test.com",
                password="testpassword123",
            )

    async def test_login_is_case_insensitive_for_email(
        self, async_session: AsyncSession, test_teacher
    ):
        user, _, _ = await auth_service.authenticate_user(
            db=async_session,
            email="TEACHER@TEST.COM",
            password="testpassword123",
        )
        assert user.email == "teacher@test.com"


# ─── refresh_tokens ────────────────────────────────────────────────────────────

class TestRefreshTokens:

    async def test_valid_refresh_token_returns_new_pair(
        self, async_session: AsyncSession, test_teacher
    ):
        from app.core.security import create_refresh_token
        raw = create_refresh_token(subject=str(test_teacher.id))

        new_access, new_refresh = await auth_service.refresh_tokens(async_session, raw)
        assert verify_token(new_access, "access") is not None
        assert verify_token(new_refresh, "refresh") is not None

    async def test_access_token_rejected_as_refresh(
        self, async_session: AsyncSession, test_teacher
    ):
        from app.core.exceptions import AuthenticationException
        from app.core.security import create_access_token
        access = create_access_token(subject=str(test_teacher.id))

        with pytest.raises(AuthenticationException):
            await auth_service.refresh_tokens(async_session, access)

    async def test_garbage_token_raises_auth_error(self, async_session: AsyncSession):
        from app.core.exceptions import AuthenticationException
        with pytest.raises(AuthenticationException):
            await auth_service.refresh_tokens(async_session, "not.a.jwt")


# ─── verify_email ──────────────────────────────────────────────────────────────

class TestVerifyEmail:

    async def test_correct_code_marks_verified(
        self,
        async_session: AsyncSession,
        unverified_user,
        fake_redis,
    ):
        key = f"email_verify:{unverified_user.email}"
        await fake_redis.setex(key, 900, json.dumps({"code": "123456", "attempts": 0}))

        await auth_service.verify_email(async_session, unverified_user.id, "123456")

        await async_session.refresh(unverified_user)
        assert unverified_user.is_verified is True
        assert await fake_redis.get(key) is None  # code consumed

    async def test_wrong_code_raises_and_increments_attempts(
        self,
        async_session: AsyncSession,
        unverified_user,
        fake_redis,
    ):
        from app.core.exceptions import ValidationException
        key = f"email_verify:{unverified_user.email}"
        await fake_redis.setex(key, 900, json.dumps({"code": "999999", "attempts": 0}))

        with pytest.raises(ValidationException):
            await auth_service.verify_email(async_session, unverified_user.id, "000000")

        stored = json.loads(await fake_redis.get(key))
        assert stored["attempts"] == 1

    async def test_no_key_in_redis_raises(
        self, async_session: AsyncSession, unverified_user
    ):
        from app.core.exceptions import ValidationException
        with pytest.raises(ValidationException):
            await auth_service.verify_email(async_session, unverified_user.id, "123456")

    async def test_already_verified_is_idempotent(
        self, async_session: AsyncSession, test_teacher
    ):
        # Should not raise even without Redis key
        await auth_service.verify_email(async_session, test_teacher.id, "anything")
        await async_session.refresh(test_teacher)
        assert test_teacher.is_verified is True


# ─── confirm_password_reset ────────────────────────────────────────────────────

class TestConfirmPasswordReset:

    async def test_correct_code_changes_password(
        self, async_session: AsyncSession, test_teacher, fake_redis
    ):
        key = "password_reset:teacher@test.com"
        await fake_redis.setex(key, 600, json.dumps({"code": "777777", "attempts": 0}))

        await auth_service.confirm_password_reset(
            async_session, "teacher@test.com", "777777", "newpassword"
        )

        await async_session.refresh(test_teacher)
        assert verify_password("newpassword", test_teacher.hashed_password)
        assert await fake_redis.get(key) is None

    async def test_wrong_code_raises_and_tracks_attempts(
        self, async_session: AsyncSession, test_teacher, fake_redis
    ):
        from app.core.exceptions import ValidationException
        key = "password_reset:teacher@test.com"
        await fake_redis.setex(key, 600, json.dumps({"code": "111111", "attempts": 0}))

        with pytest.raises(ValidationException):
            await auth_service.confirm_password_reset(
                async_session, "teacher@test.com", "000000", "newpassword"
            )

        stored = json.loads(await fake_redis.get(key))
        assert stored["attempts"] == 1

    async def test_max_attempts_deletes_key(
        self, async_session: AsyncSession, test_teacher, fake_redis
    ):
        from app.core.exceptions import ValidationException
        key = "password_reset:teacher@test.com"
        await fake_redis.setex(key, 600, json.dumps({"code": "111111", "attempts": 5}))

        with pytest.raises(ValidationException):
            await auth_service.confirm_password_reset(
                async_session, "teacher@test.com", "111111", "newpassword"
            )

        assert await fake_redis.get(key) is None

    async def test_expired_key_raises(self, async_session: AsyncSession, test_teacher):
        from app.core.exceptions import ValidationException
        # No key in Redis → simulates expiry
        with pytest.raises(ValidationException):
            await auth_service.confirm_password_reset(
                async_session, "teacher@test.com", "123456", "newpassword"
            )
