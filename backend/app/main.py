"""
AI Test Platform - FastAPI Backend

Main application entry point with:
- CORS configuration for frontend
- Router registration
- Startup/shutdown events
- Health check endpoints
- Prometheus metrics instrumentation
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
import os

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RequestLoggingMiddleware, RequestContextMiddleware
from app.api.v1.router import api_router
from app.db.session import engine
from app.db.base import Base

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mentis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Runs on startup and shutdown.
    """
    # Startup
    print("🚀 Starting AI Test Platform API...")
    
    # Create upload directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "materials"), exist_ok=True)
    
    # Create database tables (in production, use Alembic migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database tables created")
    print(f"📁 Upload directory: {settings.UPLOAD_DIR}")
    print("📊 Prometheus metrics available at /metrics")
    print("🛡️ Exception handlers registered")
    
    yield
    
    # Shutdown
    print("👋 Shutting down AI Test Platform API...")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered test generation platform with RAG",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Initialize Prometheus instrumentator
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/health", "/metrics"],
    inprogress_name="mentis_http_requests_inprogress",
    inprogress_labels=True,
)

# Instrument the app and expose /metrics endpoint
instrumentator.instrument(app).expose(app)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestContextMiddleware)

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Register custom exception handlers
register_exception_handlers(app)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Kubernetes"""
    return {
        "status": "healthy",
        "service": "ai-test-platform",
    }
