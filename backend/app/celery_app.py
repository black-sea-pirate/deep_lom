"""
Celery Configuration

Background task processing for:
- Document vectorization
- Test generation
"""

from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "ai_test_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.test_tasks",
        "app.tasks.grading_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Task routes - use task names as defined in @celery_app.task(name=...)
celery_app.conf.task_routes = {
    # Document tasks
    "vectorize_project_materials": {"queue": "documents"},
    "process_document": {"queue": "documents"},
    "delete_document_vectors": {"queue": "documents"},
    "delete_project_collection": {"queue": "documents"},
    # Test tasks
    "generate_test_questions": {"queue": "tests"},
    "check_generation_status": {"queue": "tests"},
    # Grading tasks
    "grade_written_answer": {"queue": "tests"},
    "grade_test_written_answers": {"queue": "tests"},
}
