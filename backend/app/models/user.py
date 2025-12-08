"""
User Model

Database model for users (teachers and students).
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class User(Base):
    """User model for authentication and authorization"""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="student",
    )  # "teacher" or "student"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
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
    projects = relationship("Project", back_populates="teacher", lazy="dynamic")
    material_folders = relationship("MaterialFolder", back_populates="teacher", lazy="dynamic")
    participant_groups = relationship("ParticipantGroup", back_populates="teacher", lazy="dynamic")
    participants = relationship("Participant", back_populates="teacher", foreign_keys="[Participant.teacher_id]", lazy="dynamic")
    tests = relationship("Test", back_populates="student", lazy="dynamic")
    student_emails = relationship("StudentEmail", back_populates="user", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
