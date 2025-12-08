"""
Test Models

Database models for tests, questions, and answers.
Supports multiple question types.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Test(Base):
    """Student test attempt"""
    
    __tablename__ = "tests"
    
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
    student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Test state
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )  # pending, in-progress, completed, graded
    
    # Which variant of test this student received
    variant_number: Mapped[int] = mapped_column(Integer, default=1)
    
    # Scoring
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_score: Mapped[float] = mapped_column(Float, default=100.0)
    
    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    project = relationship("Project", back_populates="tests")
    student = relationship("User", back_populates="tests")
    answers = relationship(
        "Answer",
        back_populates="test",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Test {self.id} ({self.status})>"


class Question(Base):
    """
    Generated question for a project.
    Supports multiple types: single-choice, multiple-choice, true-false,
    short-answer, essay, matching.
    """
    
    __tablename__ = "questions"
    
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
    
    # Question type
    question_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # single-choice, multiple-choice, true-false, short-answer, essay, matching
    
    # Variant number (for generating multiple unique test variants)
    # Each variant has the same structure but different questions
    variant_number: Mapped[int] = mapped_column(Integer, default=1, index=True)
    
    # Question content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=1)
    
    # Options for choice questions (JSON array of strings)
    options: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Correct answer(s) - structure depends on question type
    # single-choice: int (index)
    # multiple-choice: list of ints
    # true-false: bool
    # short-answer: list of keywords
    # essay: rubric list
    # matching: list of pairs
    correct_answer: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    # For matching questions - pairs data
    matching_pairs: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    
    # For essay questions - rubric
    rubric: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # For short answer - expected keywords
    expected_keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Order in test
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    project = relationship("Project", back_populates="questions")
    answers = relationship(
        "Answer",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    def __repr__(self) -> str:
        return f"<Question {self.question_type}: {self.text[:50]}...>"


class Answer(Base):
    """Student answer to a question"""
    
    __tablename__ = "answers"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Student's answer (JSON - type depends on question type)
    answer: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    # Grading
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    answered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    test = relationship("Test", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    
    def __repr__(self) -> str:
        return f"<Answer {self.id} (correct: {self.is_correct})>"
