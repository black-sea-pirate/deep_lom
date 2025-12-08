"""
Participant Schemas

Pydantic schemas for participants and groups.
"""

from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ============== Group Schemas ==============

class ParticipantGroupBase(BaseModel):
    """Base group schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ParticipantGroupCreate(ParticipantGroupBase):
    """Schema for creating group"""
    pass


class ParticipantGroupUpdate(BaseModel):
    """Schema for updating group"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class ParticipantGroupResponse(ParticipantGroupBase):
    """Group response schema - matches frontend ParticipantGroup"""
    id: UUID
    teacher_id: UUID = Field(alias="teacherId")
    members_count: int = Field(alias="membersCount")
    created_at: datetime = Field(alias="createdAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ============== Participant Schemas ==============

class ParticipantBase(BaseModel):
    """Base participant schema"""
    email: EmailStr
    first_name: str = Field(..., alias="firstName", min_length=1, max_length=100)
    last_name: str = Field(..., alias="lastName", min_length=1, max_length=100)
    
    class Config:
        populate_by_name = True


class ParticipantCreate(ParticipantBase):
    """Schema for creating participant"""
    group_id: Optional[UUID] = Field(None, alias="groupId")
    participant_type: str = Field(default="individual", alias="type", pattern="^(individual|group-member)$")
    # If true, auto-fill name from database based on email
    auto_fill: bool = Field(default=False, alias="autoFill")


class ParticipantUpdate(BaseModel):
    """Schema for updating participant"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, alias="firstName", min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, alias="lastName", min_length=1, max_length=100)
    group_id: Optional[UUID] = Field(None, alias="groupId")
    
    class Config:
        populate_by_name = True


class ParticipantResponse(ParticipantBase):
    """Participant response schema - matches frontend Participant"""
    id: UUID
    participant_type: str = Field(alias="type")
    group_id: Optional[UUID] = Field(None, alias="groupId")
    confirmation_status: str = Field(default="pending", alias="confirmationStatus")
    student_user_id: Optional[UUID] = Field(None, alias="studentUserId")
    created_at: datetime = Field(alias="createdAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class ParticipantListResponse(BaseModel):
    """Paginated participant list response"""
    items: List[ParticipantResponse]
    total: int
    page: int
    size: int
    pages: int


# ============== Student lookup schemas ==============

class StudentLookupResponse(BaseModel):
    """Response for student lookup by email"""
    found: bool
    email: str
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    user_id: Optional[UUID] = Field(None, alias="userId")
    
    class Config:
        populate_by_name = True


# ============== Contact Request schemas (for student notifications) ==============

class ContactRequestResponse(BaseModel):
    """Contact request notification for student"""
    id: UUID  # participant.id
    teacher_id: UUID = Field(alias="teacherId")
    teacher_name: str = Field(alias="teacherName")
    teacher_email: str = Field(alias="teacherEmail")
    status: str  # pending, confirmed, rejected
    created_at: datetime = Field(alias="createdAt")
    
    class Config:
        populate_by_name = True


class ContactRequestAction(BaseModel):
    """Action on contact request"""
    action: Literal["confirm", "reject"]
