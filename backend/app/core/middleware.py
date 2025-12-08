"""
Request Logging Middleware

Logs all incoming requests with:
- Request ID for tracing
- Request method and path
- Processing time
- Response status code
- Error details if applicable
"""

import time
import logging
from uuid import uuid4
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("mentis.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests with timing and context.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid4())[:8]
        
        # Add request ID to request state for use in handlers
        request.state.request_id = request_id
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Request info
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        
        # Skip logging for health checks and metrics
        if path in ["/health", "/metrics", "/favicon.ico"]:
            return await call_next(request)
        
        # Log request start
        logger.info(
            f"[{request_id}] --> {method} {path}{'?' + query if query else ''} from {client_ip}"
        )
        
        # Process request and measure time
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000  # ms
            
            # Log response
            status_code = response.status_code
            log_level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR
            
            logger.log(
                log_level,
                f"[{request_id}] <-- {method} {path} {status_code} ({process_time:.2f}ms)"
            )
            
            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            
            return response
            
        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000
            
            logger.error(
                f"[{request_id}] <-- {method} {path} ERROR ({process_time:.2f}ms): {type(e).__name__}: {str(e)[:100]}"
            )
            
            raise


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add useful context to request state.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Add timestamp
        request.state.request_time = time.time()
        
        # Add user agent info
        request.state.user_agent = request.headers.get("user-agent", "unknown")
        
        # Add accept language for i18n
        request.state.accept_language = request.headers.get("accept-language", "en")
        
        return await call_next(request)
