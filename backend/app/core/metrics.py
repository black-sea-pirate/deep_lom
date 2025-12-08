"""
Custom Prometheus Metrics for Mentis AI Test Platform.

Business-specific metrics for monitoring:
- Test generation performance
- User activity
- Document processing
- AI model usage
"""

from prometheus_client import Counter, Histogram, Gauge, Info

# =============================================================================
# Application Info
# =============================================================================
app_info = Info(
    "mentis_app",
    "Application information"
)
app_info.info({
    "version": "1.0.0",
    "name": "Mentis AI Test Platform",
    "python_version": "3.11"
})

# =============================================================================
# Test Generation Metrics
# =============================================================================
tests_generated_total = Counter(
    "mentis_tests_generated_total",
    "Total number of tests generated",
    ["project_id", "question_type", "difficulty"]
)

test_generation_duration_seconds = Histogram(
    "mentis_test_generation_duration_seconds",
    "Time spent generating a test",
    ["question_count"],
    buckets=(5, 10, 30, 60, 120, 300, 600, 1200)
)

ai_tokens_used_total = Counter(
    "mentis_ai_tokens_used_total",
    "Total AI tokens consumed",
    ["model", "operation"]
)

# =============================================================================
# User Activity Metrics
# =============================================================================
active_users_gauge = Gauge(
    "mentis_active_users",
    "Number of currently active users",
    ["role"]
)

user_registrations_total = Counter(
    "mentis_user_registrations_total",
    "Total user registrations",
    ["role"]
)

user_logins_total = Counter(
    "mentis_user_logins_total",
    "Total user login attempts",
    ["status"]  # success, failed
)

# =============================================================================
# Project Metrics
# =============================================================================
projects_created_total = Counter(
    "mentis_projects_created_total",
    "Total projects created"
)

projects_active_gauge = Gauge(
    "mentis_projects_active",
    "Number of currently active projects"
)

# =============================================================================
# Test Session Metrics
# =============================================================================
test_sessions_total = Counter(
    "mentis_test_sessions_total",
    "Total test sessions",
    ["status"]  # started, completed, abandoned
)

test_completion_duration_seconds = Histogram(
    "mentis_test_completion_duration_seconds",
    "Time taken to complete a test",
    buckets=(60, 120, 300, 600, 900, 1200, 1800, 3600)
)

test_scores_histogram = Histogram(
    "mentis_test_scores",
    "Distribution of test scores",
    buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
)

# =============================================================================
# Document Processing Metrics
# =============================================================================
documents_processed_total = Counter(
    "mentis_documents_processed_total",
    "Total documents processed",
    ["file_type", "status"]  # status: success, failed
)

document_processing_duration_seconds = Histogram(
    "mentis_document_processing_duration_seconds",
    "Time spent processing documents",
    ["file_type"],
    buckets=(1, 5, 10, 30, 60, 120, 300)
)

document_pages_processed_total = Counter(
    "mentis_document_pages_processed_total",
    "Total document pages processed"
)

# =============================================================================
# RAG/Vector Store Metrics
# =============================================================================
rag_queries_total = Counter(
    "mentis_rag_queries_total",
    "Total RAG queries performed"
)

rag_query_duration_seconds = Histogram(
    "mentis_rag_query_duration_seconds",
    "Time spent on RAG queries",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10)
)

vector_embeddings_created_total = Counter(
    "mentis_vector_embeddings_created_total",
    "Total vector embeddings created"
)

# =============================================================================
# WebSocket Metrics
# =============================================================================
websocket_connections_active = Gauge(
    "mentis_websocket_connections_active",
    "Number of active WebSocket connections",
    ["lobby_id"]
)

lobby_participants_gauge = Gauge(
    "mentis_lobby_participants",
    "Number of participants in active lobbies",
    ["lobby_id", "status"]  # status: waiting, ready, testing
)

# =============================================================================
# Celery Task Metrics
# =============================================================================
celery_tasks_total = Counter(
    "mentis_celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"]  # status: started, success, failed
)

celery_task_duration_seconds = Histogram(
    "mentis_celery_task_duration_seconds",
    "Celery task execution time",
    ["task_name"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

# =============================================================================
# Error Metrics
# =============================================================================
errors_total = Counter(
    "mentis_errors_total",
    "Total application errors",
    ["error_type", "endpoint"]
)

openai_errors_total = Counter(
    "mentis_openai_errors_total",
    "Total OpenAI API errors",
    ["error_type"]
)


# =============================================================================
# Helper Functions
# =============================================================================
def record_test_generated(
    project_id: str,
    question_type: str,
    difficulty: str,
    duration_seconds: float,
    question_count: int
):
    """Record test generation metrics."""
    tests_generated_total.labels(
        project_id=project_id,
        question_type=question_type,
        difficulty=difficulty
    ).inc()
    
    test_generation_duration_seconds.labels(
        question_count=str(question_count)
    ).observe(duration_seconds)


def record_document_processed(
    file_type: str,
    success: bool,
    duration_seconds: float,
    pages: int = 0
):
    """Record document processing metrics."""
    status = "success" if success else "failed"
    documents_processed_total.labels(
        file_type=file_type,
        status=status
    ).inc()
    
    if success:
        document_processing_duration_seconds.labels(
            file_type=file_type
        ).observe(duration_seconds)
        
        if pages > 0:
            document_pages_processed_total.inc(pages)


def record_test_session(
    status: str,
    duration_seconds: float = None,
    score: float = None
):
    """Record test session metrics."""
    test_sessions_total.labels(status=status).inc()
    
    if status == "completed":
        if duration_seconds:
            test_completion_duration_seconds.observe(duration_seconds)
        if score is not None:
            test_scores_histogram.observe(score)


def record_user_login(success: bool):
    """Record user login attempt."""
    status = "success" if success else "failed"
    user_logins_total.labels(status=status).inc()


def record_celery_task(
    task_name: str,
    status: str,
    duration_seconds: float = None
):
    """Record Celery task execution."""
    celery_tasks_total.labels(
        task_name=task_name,
        status=status
    ).inc()
    
    if duration_seconds and status in ("success", "failed"):
        celery_task_duration_seconds.labels(
            task_name=task_name
        ).observe(duration_seconds)
