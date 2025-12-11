"""
Project Model

Database model for test projects/courses.
Includes settings for test generation.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Project(Base):
    """Project/Test model - represents a test created by teacher"""
    
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Status: draft, vectorizing, ready, active, completed
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False,
    )
    
    # Vectorization status for project materials
    vectorization_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",  # pending, processing, completed, failed
        nullable=False,
    )
    vectorization_progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100%
    vectorization_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # OpenAI Vector Store ID for this project's vectors
    # Replaces ChromaDB - all vectorization is done by OpenAI
    openai_vector_store_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # OpenAI Assistant ID for test generation with File Search
    openai_assistant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Test settings
    timer_mode: Mapped[str] = mapped_column(String(20), default="total")  # 'total' or 'per_question'
    total_time: Mapped[int] = mapped_column(Integer, default=60)  # minutes (used when timer_mode='total')
    time_per_question: Mapped[int] = mapped_column(Integer, default=60)  # seconds (used when timer_mode='per_question')
    max_students: Mapped[int] = mapped_column(Integer, default=30)
    num_variants: Mapped[int] = mapped_column(Integer, default=1)  # Number of unique test variants
    test_language: Mapped[str] = mapped_column(String(10), default="en")  # Language for generated questions
    
    # Scheduling
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Allowed students (email list as JSON)
    allowed_students: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    teacher = relationship("User", back_populates="projects")
    question_type_configs = relationship(
        "QuestionTypeConfig",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    materials = relationship(
        "Material",
        secondary="project_materials",
        back_populates="projects",
        lazy="selectin",
    )
    tests = relationship(
        "Test",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    questions = relationship(
        "Question",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    def __repr__(self) -> str:
        return f"<Project {self.title} ({self.status})>"


class QuestionTypeConfig(Base):
    """Configuration for question types in a project"""
    
    __tablename__ = "question_type_configs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Question type: single-choice, multiple-choice, true-false, short-answer, essay, matching
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    
    # Relationship
    project = relationship("Project", back_populates="question_type_configs")
    
    def __repr__(self) -> str:
        return f"<QuestionTypeConfig {self.question_type}: {self.count}>"
