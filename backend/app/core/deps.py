"""
FastAPI Dependencies

Reusable dependencies for:
- Database sessions
- Current user authentication
- Role-based access control
"""

from typing import AsyncGenerator, Optional, TYPE_CHECKING
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session_maker
from app.core.security import verify_token

if TYPE_CHECKING:
    from app.models.user import User


# OAuth2 scheme for JWT token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.
    Yields an async session and ensures cleanup.
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Get current authenticated user from JWT token.
    
    Raises:
        HTTPException 401: If token is invalid or user not found
    """
    from app.models.user import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise credentials_exception
    
    # Get user from database
    user_id = payload.sub
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def get_current_active_user(
    current_user = Depends(get_current_user),
):
    """
    Get current active user.
    Alias for get_current_user with explicit active check.
    """
    return current_user


async def get_current_teacher(
    current_user = Depends(get_current_user),
):
    """
    Get current user with teacher role.
    
    Raises:
        HTTPException 403: If user is not a teacher
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
        )
    return current_user


async def get_current_student(
    current_user = Depends(get_current_user),
):
    """
    Get current user with student role.
    
    Raises:
        HTTPException 403: If user is not a student
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )
    return current_user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[str]:
    """
    Optional user dependency - doesn't raise if no token.
    Returns user_id if token valid, None otherwise.
    """
    if not token:
        return None
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        return None
    
    return payload.sub
