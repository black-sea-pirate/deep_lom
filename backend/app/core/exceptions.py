"""
Exception Handlers

Global exception handlers for comprehensive error reporting.
Provides detailed error responses for debugging while hiding
sensitive information in production.
"""

import traceback
import logging
from typing import Any, Dict, Optional
from datetime import datetime
from uuid import uuid4

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

# Configure logger
logger = logging.getLogger("mentis.errors")


class AppException(Exception):
    """
    Base application exception with structured error info.
    """
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationException(AppException):
    """Validation error with field details"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, **(details or {})},
        )


class AuthenticationException(AppException):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication required", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            status_code=401,
            details=details,
        )


class AuthorizationException(AppException):
    """Authorization/permission denied"""
    def __init__(self, message: str = "Permission denied", resource: Optional[str] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details={"resource": resource} if resource else {},
        )


class NotFoundException(AppException):
    """Resource not found"""
    def __init__(self, resource: str = "Resource", resource_id: Optional[str] = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": resource_id},
        )


class ConflictException(AppException):
    """Resource conflict (already exists, etc.)"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details={"field": field} if field else {},
        )


class RateLimitException(AppException):
    """Rate limit exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            code="RATE_LIMIT",
            status_code=429,
            details={"retry_after": retry_after},
        )


class ExternalServiceException(AppException):
    """External service error (AI, ChromaDB, etc.)"""
    def __init__(self, service: str, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"{service} error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service, **(details or {})},
        )


class FileProcessingException(AppException):
    """File processing error"""
    def __init__(self, message: str, filename: Optional[str] = None):
        super().__init__(
            message=message,
            code="FILE_PROCESSING_ERROR",
            status_code=400,
            details={"filename": filename} if filename else {},
        )


def create_error_response(
    error_id: str,
    message: str,
    code: str,
    status_code: int,
    details: Optional[Dict] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    include_debug: bool = False,
    traceback_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create standardized error response.
    """
    response = {
        "error": {
            "id": error_id,
            "code": code,
            "message": message,
            "status": status_code,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    if path:
        response["error"]["path"] = path
    
    if method:
        response["error"]["method"] = method
    
    # Include debug info only in development
    if include_debug and traceback_str:
        response["error"]["debug"] = {
            "traceback": traceback_str.split("\n")[-10:],  # Last 10 lines
        }
    
    return response


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions.
    """
    error_id = str(uuid4())[:8]
    
    logger.error(
        f"[{error_id}] AppException: {exc.code} - {exc.message}",
        extra={
            "error_id": error_id,
            "code": exc.code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details,
        }
    )
    
    response = create_error_response(
        error_id=error_id,
        message=exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTPExceptions with enhanced details.
    """
    error_id = str(uuid4())[:8]
    
    # Map status codes to error codes
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    
    logger.warning(
        f"[{error_id}] HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "error_id": error_id,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    response = create_error_response(
        error_id=error_id,
        message=str(exc.detail) if exc.detail else "An error occurred",
        code=code,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic/FastAPI validation errors with detailed field info.
    """
    error_id = str(uuid4())[:8]
    
    # Parse validation errors into readable format
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        errors.append({
            "field": field_path or "body",
            "message": error["msg"],
            "type": error["type"],
            "input": str(error.get("input", ""))[:100],  # Truncate for safety
        })
    
    logger.warning(
        f"[{error_id}] ValidationError: {len(errors)} errors",
        extra={
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
        }
    )
    
    response = create_error_response(
        error_id=error_id,
        message="Validation failed",
        code="VALIDATION_ERROR",
        status_code=422,
        details={"errors": errors},
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=422,
        content=response,
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database errors with appropriate messages.
    """
    error_id = str(uuid4())[:8]
    is_debug = settings.DEBUG
    
    # Determine error type
    if isinstance(exc, IntegrityError):
        # Parse constraint violations
        message = "Database constraint violation"
        code = "DB_CONSTRAINT_ERROR"
        status_code = 409
        
        error_str = str(exc.orig) if exc.orig else str(exc)
        if "unique" in error_str.lower() or "duplicate" in error_str.lower():
            message = "A record with this value already exists"
            code = "DUPLICATE_ENTRY"
        elif "foreign key" in error_str.lower():
            message = "Referenced record does not exist"
            code = "FOREIGN_KEY_ERROR"
        elif "not null" in error_str.lower():
            message = "Required field is missing"
            code = "NULL_CONSTRAINT_ERROR"
    else:
        message = "Database error occurred"
        code = "DB_ERROR"
        status_code = 500
    
    logger.error(
        f"[{error_id}] SQLAlchemyError: {code} - {str(exc)[:200]}",
        extra={
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )
    
    response = create_error_response(
        error_id=error_id,
        message=message,
        code=code,
        status_code=status_code,
        path=request.url.path,
        method=request.method,
        include_debug=is_debug,
        traceback_str=traceback.format_exc() if is_debug else None,
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with full logging.
    """
    error_id = str(uuid4())[:8]
    is_debug = settings.DEBUG
    
    logger.error(
        f"[{error_id}] Unhandled Exception: {type(exc).__name__} - {str(exc)[:200]}",
        extra={
            "error_id": error_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )
    
    # In production, hide internal details
    if is_debug:
        message = f"{type(exc).__name__}: {str(exc)}"
    else:
        message = "An unexpected error occurred. Please try again later."
    
    response = create_error_response(
        error_id=error_id,
        message=message,
        code="INTERNAL_ERROR",
        status_code=500,
        details={"error_id": error_id},
        path=request.url.path,
        method=request.method,
        include_debug=is_debug,
        traceback_str=traceback.format_exc() if is_debug else None,
    )
    
    return JSONResponse(
        status_code=500,
        content=response,
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    """
    # Custom application exceptions
    app.add_exception_handler(AppException, app_exception_handler)
    
    # HTTP exceptions (FastAPI and Starlette)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # Database errors
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered")
