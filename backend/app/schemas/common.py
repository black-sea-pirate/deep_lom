"""
Common Schemas

Shared schemas for pagination, errors, etc.
"""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
