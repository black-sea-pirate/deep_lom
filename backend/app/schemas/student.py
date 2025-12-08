"""
Student Schemas

Pydantic schemas for student-specific features.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ============== Email Management ==============

class StudentEmailBase(BaseModel):
    """Base student email schema"""
    email: EmailStr
    institution: Optional[str] = Field(None, max_length=255)


class StudentEmailCreate(StudentEmailBase):
    """Schema for adding student email"""
    pass


class StudentEmailResponse(StudentEmailBase):
    """Student email response"""
    id: UUID
    is_primary: bool = Field(alias="isPrimary")
    created_at: datetime = Field(alias="createdAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ============== Statistics ==============

class StudentStatistics(BaseModel):
    """Student statistics - matches frontend StudentStatistics"""
    total_tests: int = Field(alias="totalTests")
    completed_tests: int = Field(alias="completedTests")
    average_score: float = Field(alias="averageScore")
    
    class Config:
        populate_by_name = True


class CompletedTestInfo(BaseModel):
    """Info about completed test"""
    id: UUID
    title: str
    group_name: Optional[str] = Field(None, alias="groupName")
    score: float
    max_score: float = Field(alias="maxScore")
    completed_at: datetime = Field(alias="completedAt")
    
    class Config:
        populate_by_name = True


class UpcomingTestInfo(BaseModel):
    """Info about upcoming test"""
    id: str
    project_id: str = Field(alias="projectId")
    title: str
    group_name: Optional[str] = Field(None, alias="groupName")
    start_time: Optional[datetime] = Field(None, alias="startTime")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    duration: int
    status: str  # "scheduled", "available", "started"
    
    class Config:
        populate_by_name = True


class StudentStatisticsDetailed(StudentStatistics):
    """Detailed student statistics with test history"""
    test_history: List[CompletedTestInfo] = Field(alias="testHistory")
    
    class Config:
        populate_by_name = True


# ============== Lobby ==============

class LobbyStudent(BaseModel):
    """Student in lobby - matches frontend LobbyStudent"""
    id: UUID
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    email: str
    status: str  # "waiting" or "ready"
    joined_at: datetime = Field(alias="joinedAt")
    
    class Config:
        populate_by_name = True


class LobbyStatus(BaseModel):
    """Lobby status response"""
    project_id: UUID = Field(alias="projectId")
    project_title: str = Field(alias="projectTitle")
    students: List[LobbyStudent]
    total_students: int = Field(alias="totalStudents")
    ready_students: int = Field(alias="readyStudents")
    can_start: bool = Field(alias="canStart")
