"""
Test Schemas

Pydantic schemas for tests, questions, and answers.
"""

from datetime import datetime
from typing import Optional, List, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field


# ============== Question Schemas ==============

class QuestionBase(BaseModel):
    """Base question schema"""
    question_type: str = Field(..., alias="type", pattern="^(single-choice|multiple-choice|true-false|short-answer|essay|matching)$")
    text: str = Field(..., min_length=1)
    points: int = Field(default=1, ge=1)


class SingleChoiceQuestionCreate(QuestionBase):
    """Single choice question creation"""
    question_type: str = Field(default="single-choice", alias="type")
    options: List[str] = Field(..., min_length=2, max_length=10)
    correct_answer: int = Field(..., alias="correctAnswer", ge=0)


class MultipleChoiceQuestionCreate(QuestionBase):
    """Multiple choice question creation"""
    question_type: str = Field(default="multiple-choice", alias="type")
    options: List[str] = Field(..., min_length=2, max_length=10)
    correct_answers: List[int] = Field(..., alias="correctAnswers", min_length=1)


class TrueFalseQuestionCreate(QuestionBase):
    """True/False question creation"""
    question_type: str = Field(default="true-false", alias="type")
    correct_answer: bool = Field(..., alias="correctAnswer")


class ShortAnswerQuestionCreate(QuestionBase):
    """Short answer question creation"""
    question_type: str = Field(default="short-answer", alias="type")
    expected_keywords: List[str] = Field(..., alias="expectedKeywords", min_length=1)


class EssayQuestionCreate(QuestionBase):
    """Essay question creation"""
    question_type: str = Field(default="essay", alias="type")
    rubric: List[str] = Field(default=[])


class MatchingPair(BaseModel):
    """Matching pair for matching questions"""
    left: str
    right: str


class MatchingQuestionCreate(QuestionBase):
    """Matching question creation"""
    question_type: str = Field(default="matching", alias="type")
    pairs: List[MatchingPair] = Field(..., min_length=2)


# Union of all question types
QuestionCreate = Union[
    SingleChoiceQuestionCreate,
    MultipleChoiceQuestionCreate,
    TrueFalseQuestionCreate,
    ShortAnswerQuestionCreate,
    EssayQuestionCreate,
    MatchingQuestionCreate,
]


class QuestionResponse(BaseModel):
    """Question response schema - matches frontend Question type"""
    id: UUID
    question_type: str = Field(alias="type")
    text: str
    points: int
    options: Optional[List[str]] = None
    correct_answer: Optional[Any] = Field(None, alias="correctAnswer")
    correct_answers: Optional[List[int]] = Field(None, alias="correctAnswers")
    expected_keywords: Optional[List[str]] = Field(None, alias="expectedKeywords")
    rubric: Optional[List[str]] = None
    pairs: Optional[List[MatchingPair]] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ============== Answer Schemas ==============

class AnswerSubmit(BaseModel):
    """Schema for submitting an answer"""
    question_id: UUID = Field(..., alias="questionId")
    answer: Any  # Type varies by question type
    
    class Config:
        populate_by_name = True


class AnswerResponse(BaseModel):
    """Answer response schema - matches frontend Answer"""
    question_id: UUID = Field(alias="questionId")
    answer: Any
    is_correct: Optional[bool] = Field(None, alias="isCorrect")
    score: Optional[float] = None
    feedback: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ============== Test Schemas ==============

class TestGenerateRequest(BaseModel):
    """Request to generate test from materials"""
    project_id: UUID = Field(..., alias="projectId")
    material_ids: List[UUID] = Field(..., alias="materialIds", min_length=1)
    
    class Config:
        populate_by_name = True


class TestSubmitRequest(BaseModel):
    """Request to submit test answers"""
    answers: List[AnswerSubmit]


class TestSubmitResponse(BaseModel):
    """Response after test submission"""
    test_id: UUID = Field(alias="testId")
    score: float
    max_score: float = Field(alias="maxScore")
    correct_answers: int = Field(alias="correctAnswers")
    total_questions: int = Field(alias="totalQuestions")
    passed: bool
    feedback: Optional[str] = None
    
    class Config:
        populate_by_name = True


class TestResponse(BaseModel):
    """Test response schema - matches frontend Test type"""
    id: UUID
    project_id: UUID = Field(alias="projectId")
    student_id: Optional[UUID] = Field(None, alias="studentId")
    status: str
    score: Optional[float] = None
    max_score: float = Field(alias="maxScore")
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")
    questions: List[QuestionResponse] = []
    answers: List[AnswerResponse] = []
    
    class Config:
        from_attributes = True
        populate_by_name = True


class TestListResponse(BaseModel):
    """Paginated test list response"""
    items: List[TestResponse]
    total: int
    page: int
    size: int
    pages: int


# ============== Student Test Schemas (for taking tests) ==============

class TestForStudent(BaseModel):
    """Test schema for students (without correct answers)"""
    id: UUID
    project_id: UUID = Field(alias="projectId")
    status: str
    max_score: float = Field(alias="maxScore")
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    questions: List["QuestionForStudent"]
    
    class Config:
        populate_by_name = True


class QuestionForStudent(BaseModel):
    """Question schema for students (without correct answers)"""
    id: UUID
    question_type: str = Field(alias="type")
    text: str
    points: int
    options: Optional[List[str]] = None
    # Note: correct answers are NOT included
    
    class Config:
        populate_by_name = True


# ============== Results Schemas ==============

class TestResultResponse(BaseModel):
    """Test result response"""
    test_id: UUID = Field(alias="testId")
    project_title: str = Field(alias="projectTitle")
    score: float
    max_score: float = Field(alias="maxScore")
    percentage: float
    passed: bool
    completed_at: datetime = Field(alias="completedAt")
    answers: List[AnswerResponse]
    
    class Config:
        populate_by_name = True
