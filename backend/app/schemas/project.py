"""
Project Schemas

Pydantic schemas for project-related requests and responses.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# ============== Question Type Config ==============

class QuestionTypeConfigBase(BaseModel):
    """Base schema for question type configuration"""
    type: str = Field(..., pattern="^(single-choice|multiple-choice|true-false|short-answer|essay|matching)$")
    count: int = Field(default=5, ge=1, le=50)


class QuestionTypeConfigCreate(QuestionTypeConfigBase):
    """Schema for creating question type config"""
    pass


class QuestionTypeConfigResponse(QuestionTypeConfigBase):
    """Response schema for question type config"""
    id: UUID
    
    class Config:
        from_attributes = True


# ============== Project Settings ==============

class ProjectSettingsBase(BaseModel):
    """Project settings schema - matches frontend ProjectSettings"""
    timer_mode: str = Field(default="total", alias="timerMode", pattern="^(total|per_question)$")  # 'total' or 'per_question'
    total_time: int = Field(default=60, alias="totalTime", ge=1, le=480)  # minutes (used when timerMode='total')
    time_per_question: int = Field(default=60, alias="timePerQuestion", ge=10, le=600)  # seconds (used when timerMode='per_question')
    question_types: List[QuestionTypeConfigBase] = Field(default=[], alias="questionTypes")
    max_students: int = Field(default=30, alias="maxStudents", ge=1, le=500)
    num_variants: int = Field(default=1, alias="numVariants", ge=1, le=30)  # Number of unique test variants
    test_language: str = Field(default="en", alias="testLanguage")  # Language for generated questions (en, ru, ua, pl)
    
    class Config:
        populate_by_name = True


# ============== Vectorization ==============

class VectorizationStatus(BaseModel):
    """Vectorization status response"""
    status: str = Field(..., description="pending, processing, completed, failed")
    progress: int = Field(default=0, ge=0, le=100)
    error: Optional[str] = None
    materials_total: int = Field(default=0, alias="materialsTotal")
    materials_processed: int = Field(default=0, alias="materialsProcessed")
    
    class Config:
        populate_by_name = True


class VectorizeRequest(BaseModel):
    """Request to start vectorization"""
    material_ids: List[UUID] = Field(..., alias="materialIds", min_length=1)
    
    class Config:
        populate_by_name = True


# ============== Project Schemas ==============

class ProjectBase(BaseModel):
    """Base project schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    group_name: Optional[str] = Field(None, alias="groupName", max_length=100)


class ProjectCreate(ProjectBase):
    """Schema for creating a project - Step 1 (Project Info only)"""
    # Materials are added in Step 2 via /projects/{id}/materials endpoint
    
    class Config:
        populate_by_name = True


class ProjectAddMaterials(BaseModel):
    """Schema for adding materials to project - Step 2"""
    material_ids: List[UUID] = Field(..., alias="materialIds", min_length=1)
    
    class Config:
        populate_by_name = True


class ProjectConfigureSettings(BaseModel):
    """Schema for configuring project settings - Step 4 (after vectorization)"""
    settings: ProjectSettingsBase
    start_time: Optional[datetime] = Field(None, alias="startTime")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    
    class Config:
        populate_by_name = True


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    group_name: Optional[str] = Field(None, alias="groupName", max_length=100)
    status: Optional[str] = Field(None, pattern="^(draft|vectorizing|ready|active|completed)$")
    start_time: Optional[datetime] = Field(None, alias="startTime")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    settings: Optional[ProjectSettingsBase] = None
    
    class Config:
        populate_by_name = True


class ProjectStatusUpdate(BaseModel):
    """Schema for updating project status"""
    status: str = Field(..., pattern="^(draft|vectorizing|ready|active|completed)$")


class MaterialInProject(BaseModel):
    """Material info within project response"""
    id: UUID
    file_name: str = Field(alias="fileName")
    original_name: str = Field(alias="originalName")
    file_type: str = Field(alias="fileType")
    file_size: int = Field(alias="fileSize")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class ProjectResponse(ProjectBase):
    """Project response schema - matches frontend Project type"""
    id: UUID
    teacher_id: UUID = Field(alias="teacherId")
    status: str
    created_at: datetime = Field(alias="createdAt")
    settings: Optional[ProjectSettingsBase] = None
    start_time: Optional[datetime] = Field(None, alias="startTime")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    allowed_students: Optional[List[str]] = Field(None, alias="allowedStudents")
    
    # Vectorization info
    vectorization_status: str = Field(default="pending", alias="vectorizationStatus")
    vectorization_progress: int = Field(default=0, alias="vectorizationProgress")
    
    # OpenAI Vector Store ID (indicates materials are indexed)
    openai_vector_store_id: Optional[str] = Field(None, alias="openaiVectorStoreId")
    
    # Materials linked to project
    materials: List[MaterialInProject] = Field(default=[])
    
    class Config:
        from_attributes = True
        populate_by_name = True


class ProjectListResponse(BaseModel):
    """Paginated project list response"""
    items: List[ProjectResponse]
    total: int
    page: int
    size: int
    pages: int


# ============== Project Students ==============

class ProjectStudent(BaseModel):
    """Allowed student profile for Lobby"""

    email: str
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    confirmation_status: Optional[str] = Field(
        None, alias="confirmationStatus", description="pending|confirmed|rejected|contact_requested|unlinked"
    )
    participant_id: Optional[UUID] = Field(None, alias="participantId")

    class Config:
        populate_by_name = True
        from_attributes = True
