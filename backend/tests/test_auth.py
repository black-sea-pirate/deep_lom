"""
Authentication endpoint tests.

Covers: register, login, cookie-based refresh, /me, logout,
        change-password, email verification, password reset.
"""

import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import create_refresh_token
import app.services.auth_service as _auth_svc_module


# ─── Registration ──────────────────────────────────────────────────────────────

class TestRegister:
    async def test_success_returns_token_and_sets_cookie(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "secure123",
            "first_name": "New",
            "last_name": "User",
            "role": "teacher",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "new@test.com"
        assert data["user"]["role"] == "teacher"
        # refresh token must be in an httpOnly cookie, NOT in the body
        assert "refresh_token" not in data
        assert "refresh_token" in resp.cookies

    async def test_duplicate_email_returns_409(self, client: AsyncClient, test_teacher):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "teacher@test.com",
            "password": "secure123",
            "first_name": "Another",
            "last_name": "Teacher",
            "role": "teacher",
        })
        assert resp.status_code == 409

    async def test_invalid_email_returns_422(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "secure123",
            "first_name": "X",
            "last_name": "Y",
            "role": "student",
        })
        assert resp.status_code == 422

    async def test_short_password_returns_422(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "x@test.com",
            "password": "123",
            "first_name": "X",
            "last_name": "Y",
            "role": "student",
        })
        assert resp.status_code == 422

    async def test_invalid_role_returns_422(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "x@test.com",
            "password": "secure123",
            "first_name": "X",
            "last_name": "Y",
            "role": "admin",
        })
        assert resp.status_code == 422

    async def test_new_user_is_not_verified(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "fresh@test.com",
            "password": "secure123",
            "first_name": "Fresh",
            "last_name": "User",
            "role": "student",
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["isVerified"] is False


# ─── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_success_returns_token_and_sets_cookie(
        self, client: AsyncClient, test_teacher
    ):
        resp = await client.post("/api/v1/auth/login", data={
            "username": "teacher@test.com",
            "password": "testpassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "teacher@test.com"
        assert "refresh_token" not in data
        assert "refresh_token" in resp.cookies

    async def test_wrong_password_returns_401(self, client: AsyncClient, test_teacher):
        resp = await client.post("/api/v1/auth/login", data={
            "username": "teacher@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    async def test_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", data={
            "username": "nobody@test.com",
            "password": "anypassword",
        })
        assert resp.status_code == 401

    async def test_inactive_user_returns_401(
        self, client: AsyncClient, async_session: AsyncSession, test_teacher
    ):
        test_teacher.is_active = False
        await async_session.commit()

        resp = await client.post("/api/v1/auth/login", data={
            "username": "teacher@test.com",
            "password": "testpassword123",
        })
        assert resp.status_code == 401


# ─── Cookie-based token refresh ────────────────────────────────────────────────

class TestTokenRefresh:
    async def test_refresh_with_valid_cookie_returns_new_token(
        self, client: AsyncClient, test_teacher
    ):
        # Login first to get the cookie
        login = await client.post("/api/v1/auth/login", data={
            "username": "teacher@test.com",
            "password": "testpassword123",
        })
        assert login.status_code == 200

        # httpx keeps cookies from previous response automatically
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        # Rotation: a new refresh cookie must be set
        assert "refresh_token" in resp.cookies

    async def test_refresh_without_cookie_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    async def test_refresh_with_invalid_cookie_returns_401(self, client: AsyncClient):
        client.cookies.set("refresh_token", "this.is.not.valid")
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401


# ─── Current user ──────────────────────────────────────────────────────────────

class TestMe:
    async def test_returns_user_info(
        self, client: AsyncClient, teacher_headers, test_teacher
    ):
        resp = await client.get("/api/v1/auth/me", headers=teacher_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "teacher@test.com"
        assert data["role"] == "teacher"
        assert "isVerified" in data

    async def test_no_token_returns_401(self, client: AsyncClient):
        assert (await client.get("/api/v1/auth/me")).status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer totally.fake.token"},
        )
        assert resp.status_code == 401


# ─── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    async def test_clears_refresh_cookie(
        self, client: AsyncClient, teacher_headers
    ):
        resp = await client.post("/api/v1/auth/logout", headers=teacher_headers)
        assert resp.status_code == 200
        # Cookie should be deleted (empty value or absent)
        cookie_val = resp.cookies.get("refresh_token", "")
        assert cookie_val == ""


# ─── Change password ───────────────────────────────────────────────────────────

class TestChangePassword:
    async def test_success(self, client: AsyncClient, teacher_headers):
        resp = await client.post(
            "/api/v1/auth/change-password",
            headers=teacher_headers,
            json={"current_password": "testpassword123", "new_password": "newpass456"},
        )
        assert resp.status_code == 200

    async def test_wrong_current_password_returns_422(
        self, client: AsyncClient, teacher_headers
    ):
        resp = await client.post(
            "/api/v1/auth/change-password",
            headers=teacher_headers,
            json={"current_password": "wrongpass", "new_password": "newpass456"},
        )
        assert resp.status_code == 422  # ValidationException


# ─── Email verification ────────────────────────────────────────────────────────

class TestEmailVerification:
    async def test_correct_code_marks_user_verified(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        unverified_user: User,
        fake_redis,
    ):
        # Plant the code directly in fake Redis
        key = f"email_verify:{unverified_user.email}"
        await fake_redis.setex(key, 900, json.dumps({"code": "123456", "attempts": 0}))

        token = create_refresh_token(subject=str(unverified_user.id))
        # We need an access token for this user
        from app.core.security import create_access_token
        access = create_access_token(subject=str(unverified_user.id))

        resp = await client.post(
            "/api/v1/auth/verify-email",
            headers={"Authorization": f"Bearer {access}"},
            json={"code": "123456"},
        )
        assert resp.status_code == 200

        await async_session.refresh(unverified_user)
        assert unverified_user.is_verified is True
        # Code must be consumed
        assert await fake_redis.get(key) is None

    async def test_wrong_code_returns_422_and_increments_attempts(
        self,
        client: AsyncClient,
        unverified_user: User,
        fake_redis,
    ):
        key = f"email_verify:{unverified_user.email}"
        await fake_redis.setex(key, 900, json.dumps({"code": "999999", "attempts": 0}))

        from app.core.security import create_access_token
        access = create_access_token(subject=str(unverified_user.id))

        resp = await client.post(
            "/api/v1/auth/verify-email",
            headers={"Authorization": f"Bearer {access}"},
            json={"code": "000000"},
        )
        assert resp.status_code == 422  # ValidationException
        stored = json.loads(await fake_redis.get(key))
        assert stored["attempts"] == 1

    async def test_expired_code_returns_422(
        self, client: AsyncClient, unverified_user: User
    ):
        # No Redis key planted — simulates expiry
        from app.core.security import create_access_token
        access = create_access_token(subject=str(unverified_user.id))

        resp = await client.post(
            "/api/v1/auth/verify-email",
            headers={"Authorization": f"Bearer {access}"},
            json={"code": "123456"},
        )
        assert resp.status_code == 422  # ValidationException


# ─── Password reset ────────────────────────────────────────────────────────────

class TestPasswordReset:
    async def test_request_for_unknown_email_returns_200(self, client: AsyncClient):
        # Must NOT leak whether email exists
        resp = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "ghost@test.com"},
        )
        assert resp.status_code == 200

    async def test_request_for_known_email_sends_code(
        self, client: AsyncClient, test_teacher, fake_redis
    ):
        resp = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "teacher@test.com"},
        )
        assert resp.status_code == 200
        # A code must have been stored in Redis
        key = f"password_reset:teacher@test.com"
        raw = await fake_redis.get(key)
        assert raw is not None
        data = json.loads(raw)
        assert len(data["code"]) == 6
        assert data["code"].isdigit()

    async def test_confirm_correct_code_changes_password(
        self,
        client: AsyncClient,
        test_teacher: User,
        fake_redis,
        async_session: AsyncSession,
    ):
        key = "password_reset:teacher@test.com"
        await fake_redis.setex(key, 600, json.dumps({"code": "555555", "attempts": 0}))

        resp = await client.post("/api/v1/auth/password-reset/confirm", json={
            "email": "teacher@test.com",
            "code": "555555",
            "new_password": "brandnewpass",
        })
        assert resp.status_code == 200
        # Code must be consumed
        assert await fake_redis.get(key) is None
        # Login with new password must succeed
        login = await client.post("/api/v1/auth/login", data={
            "username": "teacher@test.com",
            "password": "brandnewpass",
        })
        assert login.status_code == 200

    async def test_confirm_wrong_code_returns_422(
        self, client: AsyncClient, test_teacher, fake_redis
    ):
        key = "password_reset:teacher@test.com"
        await fake_redis.setex(key, 600, json.dumps({"code": "111111", "attempts": 0}))

        resp = await client.post("/api/v1/auth/password-reset/confirm", json={
            "email": "teacher@test.com",
            "code": "999999",
            "new_password": "brandnewpass",
        })
        assert resp.status_code == 422  # ValidationException

    async def test_confirm_max_attempts_locks_code(
        self, client: AsyncClient, test_teacher, fake_redis
    ):
        key = "password_reset:teacher@test.com"
        # Plant code that is already at max attempts
        await fake_redis.setex(key, 600, json.dumps({"code": "111111", "attempts": 5}))

        resp = await client.post("/api/v1/auth/password-reset/confirm", json={
            "email": "teacher@test.com",
            "code": "111111",
            "new_password": "newpass",
        })
        assert resp.status_code == 422  # ValidationException — max attempts
        # Key must be deleted after lockout
        assert await fake_redis.get(key) is None
