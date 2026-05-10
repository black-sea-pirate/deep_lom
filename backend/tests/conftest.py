"""
Pytest Configuration

Shared fixtures for all tests:
- In-memory SQLite database (fast, no external deps)
- Mocked email service (no real Resend calls)
- Fake Redis (no real Redis needed)
- Pre-built teacher / student users
"""

import asyncio
import pytest
import pytest_asyncio
import fakeredis
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.core.deps import get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
import app.services.auth_service as _auth_svc_module

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ─── Event loop ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ─── Database ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


# ─── Fake Redis (replaces real Redis in auth_service) ─────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def fake_redis():
    """
    Inject a fake in-memory Redis into auth_service before every test.
    autouse=True means every test gets this automatically.
    """
    redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    _auth_svc_module._redis_client = redis
    yield redis
    await redis.aclose()
    _auth_svc_module._redis_client = None


# ─── Mock email (no real Resend calls) ────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_email():
    """
    Patch both email functions to no-ops for every test.
    autouse=True means every test gets this automatically.
    """
    with (
        patch("app.services.auth_service.send_verification_email", new=AsyncMock()),
        patch("app.services.auth_service.send_password_reset_code", new=AsyncMock()),
    ):
        yield


# ─── HTTP test client ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ─── Pre-built users ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_teacher(async_session: AsyncSession) -> User:
    user = User(
        email="teacher@test.com",
        hashed_password=get_password_hash("testpassword123"),
        first_name="Test",
        last_name="Teacher",
        role="teacher",
        is_active=True,
        is_verified=True,   # verified — can use all endpoints
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_student(async_session: AsyncSession) -> User:
    user = User(
        email="student@test.com",
        hashed_password=get_password_hash("testpassword123"),
        first_name="Test",
        last_name="Student",
        role="student",
        is_active=True,
        is_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user(async_session: AsyncSession) -> User:
    """User that registered but hasn't verified their email yet."""
    user = User(
        email="unverified@test.com",
        hashed_password=get_password_hash("testpassword123"),
        first_name="Unverified",
        last_name="User",
        role="student",
        is_active=True,
        is_verified=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


# ─── Auth tokens and headers ───────────────────────────────────────────────────

@pytest_asyncio.fixture
async def teacher_token(test_teacher: User) -> str:
    return create_access_token(subject=str(test_teacher.id))


@pytest_asyncio.fixture
async def student_token(test_student: User) -> str:
    return create_access_token(subject=str(test_student.id))


@pytest.fixture
def teacher_headers(teacher_token: str) -> dict:
    return {"Authorization": f"Bearer {teacher_token}"}


@pytest.fixture
def student_headers(student_token: str) -> dict:
    return {"Authorization": f"Bearer {student_token}"}
