"""
Participant Model

Database models for students/participants and groups.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ParticipantGroup(Base):
    """Group of participants/students"""
    
    __tablename__ = "participant_groups"
    
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    teacher = relationship("User", back_populates="participant_groups")
    members = relationship(
        "Participant",
        back_populates="group",
        lazy="dynamic",
    )
    
    @property
    def members_count(self) -> int:
        """Count of members in group"""
        return self.members.count() if self.members else 0
    
    def __repr__(self) -> str:
        return f"<ParticipantGroup {self.name}>"


class Participant(Base):
    """Individual participant/student added by teacher"""
    
    __tablename__ = "participants"
    
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
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participant_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Link to actual student user (if exists)
    student_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Participant info
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Type: individual or group-member
    participant_type: Mapped[str] = mapped_column(
        String(20),
        default="individual",
        nullable=False,
    )
    
    # Confirmation status: pending, confirmed, rejected
    # When teacher adds student, status starts as 'pending'
    # Student must confirm to be 'confirmed'
    confirmation_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="participants")
    student_user = relationship("User", foreign_keys=[student_user_id])
    group = relationship("ParticipantGroup", back_populates="members")
    
    def __repr__(self) -> str:
        return f"<Participant {self.email}>"
