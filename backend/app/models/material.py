"""
Material Model

Database models for educational materials (files) and folders.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


# Many-to-many association table: projects <-> materials
project_materials = Table(
    "project_materials",
    Base.metadata,
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True),
    Column("is_vectorized", Integer, default=0),  # 0 = pending, 1 = processing, 2 = done, -1 = error
    Column("created_at", DateTime, default=datetime.utcnow),
)


class MaterialFolder(Base):
    """Folder for organizing materials"""
    
    __tablename__ = "material_folders"
    
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
    teacher = relationship("User", back_populates="material_folders")
    materials = relationship(
        "Material",
        back_populates="folder",
        lazy="dynamic",
    )
    
    @property
    def materials_count(self) -> int:
        """Count of materials in folder"""
        return self.materials.count() if self.materials else 0
    
    def __repr__(self) -> str:
        return f"<MaterialFolder {self.name}>"


class Material(Base):
    """Educational material file"""
    
    __tablename__ = "materials"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("material_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # File info
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, txt, etc.
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes
    
    # OpenAI File ID - file is stored in OpenAI, not locally
    openai_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    
    # Relationships
    folder = relationship("MaterialFolder", back_populates="materials")
    projects = relationship(
        "Project",
        secondary=project_materials,
        back_populates="materials",
    )
    
    def __repr__(self) -> str:
        return f"<Material {self.original_name}>"
