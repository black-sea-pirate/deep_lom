"""
Application Configuration

Environment-based settings using Pydantic Settings.
All sensitive values come from environment variables.
"""

import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Do NOT use env_file in Docker - env vars are passed directly
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=True,
        extra="ignore"
    )
    
    # Project
    PROJECT_NAME: str = "AI Test Platform"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True  # Enable debug mode for detailed error messages
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_test_platform"
    
    @property
    def DATABASE_URL(self) -> str:
        """Async PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync PostgreSQL connection URL (for Alembic)"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    
    @property
    def REDIS_URL(self) -> str:
        """Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    # ChromaDB (Vector Database for RAG)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "materials"
    
    # OpenAI
    OPENAI_API_KEY: str = ""  # Set via environment variable
    OPENAI_MODEL: str = "gpt-4.1"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg"]
    
    # CORS - stored as string, parsed to list
    BACKEND_CORS_ORIGINS: Union[List[str], str] = "http://localhost:5173,http://localhost:3000"
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            # Try JSON first
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Otherwise split by comma
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return v
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"


# Global settings instance
settings = Settings()
