"""
Pytest Configuration

Shared fixtures and configuration for all tests.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.core.deps import get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User


# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for each test."""
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
    """Create async session for each test."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database dependency."""
    
    async def override_get_db():
        yield async_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_teacher(async_session: AsyncSession) -> User:
    """Create test teacher user."""
    user = User(
        email="teacher@test.com",
        hashed_password=get_password_hash("testpassword123"),
        first_name="Test",
        last_name="Teacher",
        role="teacher",
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_student(async_session: AsyncSession) -> User:
    """Create test student user."""
    user = User(
        email="student@test.com",
        hashed_password=get_password_hash("testpassword123"),
        first_name="Test",
        last_name="Student",
        role="student",
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def teacher_token(test_teacher: User) -> str:
    """Create JWT token for teacher."""
    return create_access_token(subject=str(test_teacher.id))


@pytest_asyncio.fixture
async def student_token(test_student: User) -> str:
    """Create JWT token for student."""
    return create_access_token(subject=str(test_student.id))


@pytest_asyncio.fixture
def teacher_headers(teacher_token: str) -> dict:
    """Headers with teacher authentication."""
    return {"Authorization": f"Bearer {teacher_token}"}


@pytest_asyncio.fixture
def student_headers(student_token: str) -> dict:
    """Headers with student authentication."""
    return {"Authorization": f"Bearer {student_token}"}
