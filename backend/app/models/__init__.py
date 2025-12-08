"""
Models Package

Import all models here for easy access and to ensure they are registered with Base.
"""

from app.db.base import Base

# Import all models to register them with Base metadata
from app.models.user import User
from app.models.project import Project, QuestionTypeConfig
from app.models.material import Material, MaterialFolder
from app.models.participant import Participant, ParticipantGroup
from app.models.test import Test, Question, Answer
from app.models.student_email import StudentEmail

__all__ = [
    "Base",
    "User",
    "Project",
    "QuestionTypeConfig",
    "Material",
    "MaterialFolder",
    "Participant",
    "ParticipantGroup",
    "Test",
    "Question",
    "Answer",
    "StudentEmail",
]
