"""
Project Endpoints

CRUD operations for projects with multi-step creation flow:
1. Create project (title, description, group)
2. Add materials (select from uploaded files)
3. Start vectorization (Celery background task)
4. Configure settings (question types, time limits)
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from app.core.deps import get_db, get_current_teacher, get_current_user
from app.core.exceptions import (
    NotFoundException,
    AuthorizationException,
    ValidationException,
)
from app.models.user import User
from app.models.project import Project, QuestionTypeConfig
from app.models.material import Material, project_materials
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectStatusUpdate,
    ProjectSettingsBase,
    ProjectAddMaterials,
    ProjectConfigureSettings,
    VectorizationStatus,
    MaterialInProject,
)
from app.schemas.common import MessageResponse
from app.tasks.document_tasks import vectorize_project_materials

router = APIRouter()


def project_to_response(project: Project) -> ProjectResponse:
    """Convert Project model to response schema"""
    # Build settings from project and question_type_configs
    question_types = [
        {"type": qtc.question_type, "count": qtc.count}
        for qtc in project.question_type_configs
    ] if project.question_type_configs else []
    
    settings = None
    if question_types or project.total_time or project.time_per_question:
        settings = ProjectSettingsBase(
            totalTime=project.total_time,
            timePerQuestion=project.time_per_question,
            questionTypes=question_types,
            maxStudents=project.max_students,
        )
    
    # Convert materials
    materials_list = []
    if project.materials:
        for m in project.materials:
            materials_list.append(MaterialInProject(
                id=m.id,
                fileName=m.file_name,
                originalName=m.original_name,
                fileType=m.file_type,
                fileSize=m.file_size,
            ))
    
    return ProjectResponse(
        id=project.id,
        teacherId=project.teacher_id,
        title=project.title,
        description=project.description,
        groupName=project.group_name,
        status=project.status,
        createdAt=project.created_at,
        settings=settings,
        startTime=project.start_time,
        endTime=project.end_time,
        allowedStudents=project.allowed_students,
        vectorizationStatus=project.vectorization_status,
        vectorizationProgress=project.vectorization_progress,
        openaiVectorStoreId=project.openai_vector_store_id,
        materials=materials_list,
    )


@router.get("", response_model=ProjectListResponse)
async def get_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all projects for current teacher with pagination.
    """
    # Base query
    query = select(Project).where(Project.teacher_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.where(Project.status == status)
    if search:
        query = query.where(Project.title.ilike(f"%{search}%"))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.options(
        selectinload(Project.question_type_configs),
        selectinload(Project.materials),
    )
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        items=[project_to_response(p) for p in projects],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get project by ID.
    """
    query = select(Project).where(Project.id == project_id)
    query = query.options(
        selectinload(Project.question_type_configs),
        selectinload(Project.materials),
    )
    
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    # Check access (teacher owns it or student is allowed)
    if current_user.role == "teacher" and project.teacher_id != current_user.id:
        raise AuthorizationException(
            message="You don't have access to this project",
            resource=f"project:{project_id}",
        )
    
    return project_to_response(project)


# ============== Step 1: Create Project ==============

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Create a new project with basic info.
    
    After this, use:
    - POST /projects/{id}/materials to add materials (Step 2)
    - POST /projects/{id}/vectorize to start vectorization (Step 3)
    - PUT /projects/{id}/settings to configure test settings (Step 4)
    """
    # Create project with basic info only
    project = Project(
        teacher_id=current_user.id,
        title=project_data.title,
        description=project_data.description,
        group_name=project_data.group_name,
        status="draft",
        vectorization_status="pending",
    )
    
    db.add(project)
    await db.commit()
    
    # Reload with relationships
    query = select(Project).where(Project.id == project.id)
    query = query.options(
        selectinload(Project.question_type_configs),
        selectinload(Project.materials),
    )
    result = await db.execute(query)
    project = result.scalar_one()
    
    return project_to_response(project)


# ============== Step 2: Add Materials ==============

@router.post("/{project_id}/materials", response_model=ProjectResponse)
async def add_materials_to_project(
    project_id: UUID,
    materials_data: ProjectAddMaterials,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Add materials to project for vectorization.
    
    Materials must be previously uploaded by the teacher.
    This replaces any existing materials linked to the project.
    """
    # Get project
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    # Verify all materials exist and belong to teacher
    materials_query = select(Material).where(
        Material.id.in_(materials_data.material_ids),
        Material.teacher_id == current_user.id,
    )
    materials_result = await db.execute(materials_query)
    materials = materials_result.scalars().all()
    
    if len(materials) != len(materials_data.material_ids):
        found_ids = {str(m.id) for m in materials}
        missing_ids = [str(mid) for mid in materials_data.material_ids if str(mid) not in found_ids]
        raise ValidationException(
            message=f"Some materials not found or don't belong to you",
            field="material_ids",
            details={"missing_ids": missing_ids},
        )
    
    # Clear existing project-material links
    await db.execute(
        project_materials.delete().where(project_materials.c.project_id == project_id)
    )
    
    # Add new links
    for material in materials:
        await db.execute(
            project_materials.insert().values(
                project_id=project_id,
                material_id=material.id,
                is_vectorized=0,  # pending
            )
        )
    
    # Reset vectorization status
    project.vectorization_status = "pending"
    project.vectorization_progress = 0
    project.vectorization_error = None
    
    await db.commit()
    
    # Reload project
    query = select(Project).where(Project.id == project_id)
    query = query.options(
        selectinload(Project.question_type_configs),
        selectinload(Project.materials),
    )
    result = await db.execute(query)
    project = result.scalar_one()
    
    return project_to_response(project)


# ============== Step 3: Start Vectorization ==============

@router.post("/{project_id}/vectorize", response_model=VectorizationStatus)
async def start_vectorization(
    project_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Start vectorization of project materials.
    
    This is a background task. Poll GET /projects/{id}/vectorization-status
    to check progress.
    """
    # Get project with materials
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    query = query.options(selectinload(Project.materials))
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    if not project.materials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No materials linked to project. Add materials first.",
        )
    
    if project.vectorization_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vectorization already in progress",
        )
    
    # Update status to processing
    project.vectorization_status = "processing"
    project.vectorization_progress = 0
    project.vectorization_error = None
    project.status = "vectorizing"
    await db.commit()
    
    # Start Celery task
    material_ids = [str(m.id) for m in project.materials]
    vectorize_project_materials.delay(str(project_id), material_ids)
    
    return VectorizationStatus(
        status="processing",
        progress=0,
        materialsTotal=len(project.materials),
        materialsProcessed=0,
    )


@router.get("/{project_id}/vectorization-status", response_model=VectorizationStatus)
async def get_vectorization_status(
    project_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current vectorization status and progress.
    
    Poll this endpoint to show loading indicator to user.
    """
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    query = query.options(selectinload(Project.materials))
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Count processed materials
    processed_query = select(func.count()).select_from(project_materials).where(
        project_materials.c.project_id == project_id,
        project_materials.c.is_vectorized == 2,  # done
    )
    processed_result = await db.execute(processed_query)
    processed_count = processed_result.scalar() or 0
    
    return VectorizationStatus(
        status=project.vectorization_status,
        progress=project.vectorization_progress,
        error=project.vectorization_error,
        materialsTotal=len(project.materials) if project.materials else 0,
        materialsProcessed=processed_count,
    )


# ============== Step 4: Configure Settings ==============

@router.put("/{project_id}/settings", response_model=ProjectResponse)
async def configure_project_settings(
    project_id: UUID,
    settings_data: ProjectConfigureSettings,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 4: Configure test settings after vectorization is complete.
    
    This step should only be called after vectorization is completed.
    """
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    query = query.options(selectinload(Project.question_type_configs))
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Warning if vectorization not complete (but allow anyway)
    if project.vectorization_status != "completed":
        # Just a warning, don't block - user might want to configure anyway
        pass
    
    # Update settings
    project.total_time = settings_data.settings.total_time
    project.time_per_question = settings_data.settings.time_per_question
    project.max_students = settings_data.settings.max_students
    project.num_variants = settings_data.settings.num_variants
    project.test_language = settings_data.settings.test_language
    
    # Strip timezone info for TIMESTAMP WITHOUT TIME ZONE columns
    if settings_data.start_time:
        start_time = settings_data.start_time
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        project.start_time = start_time
    if settings_data.end_time:
        end_time = settings_data.end_time
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
        project.end_time = end_time
    
    # Update status to ready if vectorization is complete
    if project.vectorization_status == "completed":
        project.status = "ready"
    
    # Update question type configs
    # Delete existing
    for qtc in project.question_type_configs:
        await db.delete(qtc)
    
    # Create new
    for qt_config in settings_data.settings.question_types:
        qtc = QuestionTypeConfig(
            project_id=project.id,
            question_type=qt_config.type,
            count=qt_config.count,
        )
        db.add(qtc)
    
    await db.commit()
    
    # Reload
    query = select(Project).where(Project.id == project_id)
    query = query.options(
        selectinload(Project.question_type_configs),
        selectinload(Project.materials),
    )
    result = await db.execute(query)
    project = result.scalar_one()
    
    return project_to_response(project)


# ============== Step 5: Generate Tests ==============

@router.post("/{project_id}/generate-tests")
async def generate_tests(
    project_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 5: Start AI test generation for project.
    
    This creates a background task that:
    1. Retrieves content from vectorized materials
    2. Generates questions using AI
    3. Saves questions to database
    
    Returns a job ID to track progress.
    """
    from app.tasks.test_tasks import generate_test_questions
    
    # Get project with materials
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    query = query.options(
        selectinload(Project.materials),
        selectinload(Project.question_type_configs),
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    if not project.materials:
        raise ValidationException(
            message="No materials linked to project. Add materials first.",
            field="materials",
        )
    
    if not project.question_type_configs:
        raise ValidationException(
            message="No question types configured. Configure settings first.",
            field="question_type_configs",
        )
    
    # Start Celery task
    material_ids = [str(m.id) for m in project.materials]
    task = generate_test_questions.delay(str(project_id), material_ids)
    
    # Update project status
    project.status = "generating"
    await db.commit()
    
    return {
        "jobId": task.id,
        "status": "processing",
        "message": "Test generation started",
    }


@router.get("/{project_id}/generate-tests/{job_id}")
async def get_generation_status(
    project_id: UUID,
    job_id: str,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Check test generation job status.
    """
    from celery.result import AsyncResult
    from app.celery_app import celery_app
    
    # Verify project ownership
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    # Get task result
    task_result = AsyncResult(job_id, app=celery_app)
    
    status_map = {
        "PENDING": "pending",
        "STARTED": "processing",
        "PROCESSING": "processing",
        "SUCCESS": "completed",
        "FAILURE": "failed",
    }
    
    response = {
        "status": status_map.get(task_result.status, "unknown"),
        "progress": 0,
    }
    
    if task_result.info:
        if isinstance(task_result.info, dict):
            response["progress"] = task_result.info.get("progress", 0)
            response["step"] = task_result.info.get("step")
            if task_result.info.get("error"):
                response["message"] = task_result.info.get("error")
            if task_result.info.get("questions_generated"):
                response["questionsGenerated"] = task_result.info.get("questions_generated")
    
    if task_result.status == "SUCCESS" and isinstance(task_result.result, dict):
        response["questionsGenerated"] = task_result.result.get("questions_generated", 0)
    
    if task_result.status == "FAILURE":
        response["message"] = str(task_result.result) if task_result.result else "Generation failed"
    
    return response


# ============== General Updates ==============

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Update project general info.
    """
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    query = query.options(
        selectinload(Project.question_type_configs),
        selectinload(Project.materials),
    )
    
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Update fields
    if project_data.title is not None:
        project.title = project_data.title
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.group_name is not None:
        project.group_name = project_data.group_name
    if project_data.status is not None:
        project.status = project_data.status
    if project_data.start_time is not None:
        # Strip timezone info for TIMESTAMP WITHOUT TIME ZONE column
        start_time = project_data.start_time
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        project.start_time = start_time
    if project_data.end_time is not None:
        # Strip timezone info for TIMESTAMP WITHOUT TIME ZONE column
        end_time = project_data.end_time
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
        project.end_time = end_time
    
    # Update settings if provided
    if project_data.settings:
        project.total_time = project_data.settings.total_time
        project.time_per_question = project_data.settings.time_per_question
        project.max_students = project_data.settings.max_students
        
        # Update question type configs
        for qtc in project.question_type_configs:
            await db.delete(qtc)
        
        for qt_config in project_data.settings.question_types:
            qtc = QuestionTypeConfig(
                project_id=project.id,
                question_type=qt_config.type,
                count=qt_config.count,
            )
            db.add(qtc)
    
    await db.commit()
    await db.refresh(project)
    
    return project_to_response(project)


@router.patch("/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: UUID,
    status_data: ProjectStatusUpdate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Update project status only.
    """
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    query = query.options(
        selectinload(Project.question_type_configs),
        selectinload(Project.materials),
    )
    
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    project.status = status_data.status
    await db.commit()
    await db.refresh(project)
    
    return project_to_response(project)


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete project by ID.
    Also removes project-material links and OpenAI Vector Store.
    """
    from app.services.openai_vectorstore import get_vectorstore_service
    
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Delete OpenAI Vector Store if exists
    if project.openai_vector_store_id:
        try:
            vs_service = get_vectorstore_service()
            vs_service.delete_vector_store(project.openai_vector_store_id)
        except Exception as e:
            print(f"Warning: Failed to delete Vector Store from OpenAI: {e}")
    
    # Delete OpenAI Assistant if exists
    if project.openai_assistant_id:
        try:
            vs_service = get_vectorstore_service()
            vs_service.cleanup_assistant(project.openai_assistant_id)
        except Exception as e:
            print(f"Warning: Failed to delete Assistant from OpenAI: {e}")
    
    await db.delete(project)
    await db.commit()
    
    return MessageResponse(message="Project deleted successfully")


# ============== Questions CRUD ==============

@router.get("/{project_id}/questions")
async def get_project_questions(
    project_id: UUID,
    variant: Optional[int] = Query(None, description="Filter by variant number"),
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all questions for a project.
    Optionally filter by variant number.
    """
    from app.models.test import Question
    
    # Verify project ownership
    project_query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    # Get questions with optional variant filter
    questions_query = select(Question).where(
        Question.project_id == project_id
    )
    
    if variant is not None:
        questions_query = questions_query.where(Question.variant_number == variant)
    
    questions_query = questions_query.order_by(Question.variant_number, Question.order)
    
    result = await db.execute(questions_query)
    questions = result.scalars().all()
    
    # Get unique variants count
    variants_query = select(Question.variant_number).where(
        Question.project_id == project_id
    ).distinct().order_by(Question.variant_number)
    variants_result = await db.execute(variants_query)
    unique_variants = [v[0] for v in variants_result.fetchall()]
    
    return {
        "questions": [
            {
                "id": str(q.id),
                "questionType": q.question_type,
                "text": q.text,
                "points": q.points,
                "options": q.options,
                "correctAnswer": q.correct_answer,
                "expectedKeywords": q.expected_keywords,
                "order": q.order,
                "variantNumber": q.variant_number,
            }
            for q in questions
        ],
        "variants": unique_variants,
        "totalVariants": len(unique_variants),
    }


@router.post("/{project_id}/questions")
async def create_question(
    project_id: UUID,
    question_data: dict,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new question for a project.
    """
    from app.models.test import Question
    
    # Verify project ownership
    project_query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    # Create question
    question = Question(
        project_id=project_id,
        question_type=question_data.get("questionType", "single-choice"),
        text=question_data.get("text", ""),
        points=question_data.get("points", 1),
        options=question_data.get("options"),
        correct_answer=question_data.get("correctAnswer"),
        expected_keywords=question_data.get("expectedKeywords"),
        order=question_data.get("order", 0),
    )
    
    db.add(question)
    await db.commit()
    await db.refresh(question)
    
    return {
        "id": str(question.id),
        "questionType": question.question_type,
        "text": question.text,
        "points": question.points,
        "options": question.options,
        "correctAnswer": question.correct_answer,
        "expectedKeywords": question.expected_keywords,
        "order": question.order,
    }


@router.put("/{project_id}/questions/{question_id}")
async def update_question(
    project_id: UUID,
    question_id: UUID,
    question_data: dict,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing question.
    """
    from app.models.test import Question
    
    # Verify project ownership
    project_query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    # Get question
    question_query = select(Question).where(
        Question.id == question_id,
        Question.project_id == project_id,
    )
    question_result = await db.execute(question_query)
    question = question_result.scalar_one_or_none()
    
    if not question:
        raise NotFoundException(resource="Question", resource_id=str(question_id))
    
    # Update fields
    if "questionType" in question_data:
        question.question_type = question_data["questionType"]
    if "text" in question_data:
        question.text = question_data["text"]
    if "points" in question_data:
        question.points = question_data["points"]
    if "options" in question_data:
        question.options = question_data["options"]
    if "correctAnswer" in question_data:
        question.correct_answer = question_data["correctAnswer"]
    if "expectedKeywords" in question_data:
        question.expected_keywords = question_data["expectedKeywords"]
    if "order" in question_data:
        question.order = question_data["order"]
    
    await db.commit()
    await db.refresh(question)
    
    return {
        "id": str(question.id),
        "questionType": question.question_type,
        "text": question.text,
        "points": question.points,
        "options": question.options,
        "correctAnswer": question.correct_answer,
        "expectedKeywords": question.expected_keywords,
        "order": question.order,
    }


@router.delete("/{project_id}/questions/{question_id}")
async def delete_question(
    project_id: UUID,
    question_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a question.
    """
    from app.models.test import Question
    
    # Verify project ownership
    project_query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    # Get question
    question_query = select(Question).where(
        Question.id == question_id,
        Question.project_id == project_id,
    )
    question_result = await db.execute(question_query)
    question = question_result.scalar_one_or_none()
    
    if not question:
        raise NotFoundException(resource="Question", resource_id=str(question_id))
    
    await db.delete(question)
    await db.commit()
    
    return {"message": "Question deleted successfully"}


# ==================== Project Students Management ====================

@router.get("/{project_id}/students", response_model=List[str])
async def get_project_students(
    project_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of allowed students for a project.
    """
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    return project.allowed_students or []


@router.post("/{project_id}/students")
async def add_student_to_project(
    project_id: UUID,
    student_data: dict,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a student email to project's allowed students list.
    
    Body: {"email": "student@example.com"}
    """
    email = student_data.get("email", "").strip().lower()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required",
        )
    
    # Validate email format
    import re
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format",
        )
    
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    # Initialize if None
    if project.allowed_students is None:
        project.allowed_students = []
    
    # Check if already in list
    if email in project.allowed_students:
        return {"message": "Student already added", "students": project.allowed_students}
    
    # Add student
    project.allowed_students = project.allowed_students + [email]
    await db.commit()
    await db.refresh(project)
    
    return {"message": "Student added successfully", "students": project.allowed_students}


@router.delete("/{project_id}/students/{email}")
async def remove_student_from_project(
    project_id: UUID,
    email: str,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a student email from project's allowed students list.
    """
    email = email.strip().lower()
    
    query = select(Project).where(
        Project.id == project_id,
        Project.teacher_id == current_user.id,
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundException(resource="Project", resource_id=str(project_id))
    
    if not project.allowed_students or email not in project.allowed_students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in project",
        )
    
    project.allowed_students = [e for e in project.allowed_students if e != email]
    await db.commit()
    await db.refresh(project)
    
    return {"message": "Student removed successfully", "students": project.allowed_students}
