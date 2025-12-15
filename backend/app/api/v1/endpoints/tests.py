"""
Test Endpoints

Test generation, submission, and results.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.deps import get_db, get_current_teacher, get_current_student, get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.material import Material
from app.models.test import Test, Question, Answer
from app.schemas.test import (
    TestGenerateRequest,
    TestSubmitRequest,
    TestSubmitResponse,
    TestResponse,
    TestListResponse,
    TestForStudent,
    QuestionForStudent,
    QuestionResponse,
    AnswerResponse,
    TestResultResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter()


# ============== Test Generation ==============

@router.post("/generate", response_model=MessageResponse)
async def generate_test(
    request: TestGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate test questions from materials using AI.
    
    This is an async operation - questions are generated in background.
    Frontend should poll for project questions or use WebSocket for updates.
    """
    # Verify project ownership
    project_result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.teacher_id == current_user.id,
        ).options(selectinload(Project.question_type_configs))
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Verify materials exist
    materials_result = await db.execute(
        select(Material).where(
            Material.id.in_(request.material_ids),
            Material.teacher_id == current_user.id,
        )
    )
    materials = materials_result.scalars().all()
    
    if len(materials) != len(request.material_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some materials not found",
        )
    
    # Add background task for AI generation
    # In production, this would be a Celery task
    # background_tasks.add_task(
    #     generate_questions_task,
    #     project_id=str(project.id),
    #     material_ids=[str(m.id) for m in materials],
    #     question_configs=project.question_type_configs,
    # )
    
    # For now, return success and let Celery handle it
    return MessageResponse(
        message="Test generation started. Questions will be available shortly.",
        success=True,
    )


# ============== Teacher Test Management ==============

@router.get("/project/{project_id}", response_model=TestListResponse)
async def get_project_tests(
    project_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all test attempts for a project (teacher view).
    """
    # Verify project ownership
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.teacher_id == current_user.id,
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Build query
    query = select(Test).where(Test.project_id == project_id)
    if status:
        query = query.where(Test.status == status)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.options(selectinload(Test.answers))
    query = query.order_by(Test.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    tests = result.scalars().all()
    
    # Get questions for project
    questions_result = await db.execute(
        select(Question).where(Question.project_id == project_id).order_by(Question.order)
    )
    questions = questions_result.scalars().all()
    
    return TestListResponse(
        items=[
            TestResponse(
                id=t.id,
                projectId=t.project_id,
                studentId=t.student_id,
                status=t.status,
                score=t.score,
                maxScore=t.max_score,
                startedAt=t.started_at,
                completedAt=t.completed_at,
                questions=[
                    QuestionResponse(
                        id=q.id,
                        type=q.question_type,
                        text=q.text,
                        points=q.points,
                        options=q.options,
                        correctAnswer=q.correct_answer,
                        expectedKeywords=q.expected_keywords,
                        rubric=q.rubric,
                        pairs=q.matching_pairs,
                    )
                    for q in questions
                ],
                answers=[
                    AnswerResponse(
                        questionId=a.question_id,
                        answer=a.answer,
                        isCorrect=a.is_correct,
                        score=a.score,
                        feedback=a.feedback,
                    )
                    for a in t.answers
                ],
            )
            for t in tests
        ],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/{test_id}", response_model=TestResponse)
async def get_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get test by ID with questions and answers.
    """
    query = select(Test).where(Test.id == test_id)
    query = query.options(selectinload(Test.answers))
    
    result = await db.execute(query)
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    # Check access
    if current_user.role == "student" and test.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Get questions
    questions_result = await db.execute(
        select(Question).where(Question.project_id == test.project_id).order_by(Question.order)
    )
    questions = questions_result.scalars().all()
    
    return TestResponse(
        id=test.id,
        projectId=test.project_id,
        studentId=test.student_id,
        status=test.status,
        score=test.score,
        maxScore=test.max_score,
        startedAt=test.started_at,
        completedAt=test.completed_at,
        questions=[
            QuestionResponse(
                id=q.id,
                type=q.question_type,
                text=q.text,
                points=q.points,
                options=q.options,
                correctAnswer=q.correct_answer if current_user.role == "teacher" else None,
                expectedKeywords=q.expected_keywords if current_user.role == "teacher" else None,
                rubric=q.rubric,
                pairs=q.matching_pairs,
            )
            for q in questions
        ],
        answers=[
            AnswerResponse(
                questionId=a.question_id,
                answer=a.answer,
                isCorrect=a.is_correct,
                score=a.score,
                feedback=a.feedback,
            )
            for a in test.answers
        ],
    )


# ============== Student Test Taking ==============

@router.post("/{test_id}/start", response_model=TestForStudent)
async def start_test(
    test_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a test attempt for current student.
    """
    # Get test
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    if test.student_id and test.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This test belongs to another student",
        )
    
    if test.status not in ["pending", "in-progress"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test cannot be started",
        )
    
    # Update test
    test.student_id = current_user.id
    test.status = "in-progress"
    test.started_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(test)
    
    # Get questions (without correct answers)
    questions_result = await db.execute(
        select(Question).where(Question.project_id == test.project_id).order_by(Question.order)
    )
    questions = questions_result.scalars().all()
    
    return TestForStudent(
        id=test.id,
        projectId=test.project_id,
        status=test.status,
        maxScore=test.max_score,
        startedAt=test.started_at,
        questions=[
            QuestionForStudent(
                id=q.id,
                type=q.question_type,
                text=q.text,
                points=q.points,
                options=q.options,
            )
            for q in questions
        ],
    )


@router.post("/{test_id}/submit", response_model=TestSubmitResponse)
async def submit_test(
    test_id: UUID,
    submission: TestSubmitRequest,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit test answers and get results.
    """
    # Get test
    result = await db.execute(
        select(Test).where(
            Test.id == test_id,
            Test.student_id == current_user.id,
        )
    )
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    if test.status != "in-progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test is not in progress",
        )
    
    # Get questions
    questions_result = await db.execute(
        select(Question).where(Question.project_id == test.project_id)
    )
    questions = {str(q.id): q for q in questions_result.scalars().all()}
    
    # Grade answers
    total_score = 0
    correct_count = 0
    
    for submitted_answer in submission.answers:
        question = questions.get(str(submitted_answer.question_id))
        if not question:
            continue
        
        # Grade based on question type
        is_correct = False
        score = 0
        feedback = None
        
        if question.question_type == "single-choice":
            is_correct = submitted_answer.answer == question.correct_answer
            score = question.points if is_correct else 0
            
        elif question.question_type == "multiple-choice":
            correct_set = set(question.correct_answer or [])
            answer_set = set(submitted_answer.answer or [])
            is_correct = correct_set == answer_set
            # Partial credit
            if is_correct:
                score = question.points
            elif answer_set & correct_set:
                score = question.points * len(answer_set & correct_set) / len(correct_set)
                
        elif question.question_type == "true-false":
            is_correct = submitted_answer.answer == question.correct_answer
            score = question.points if is_correct else 0
            
        elif question.question_type == "short-answer":
            # Check keywords
            answer_lower = str(submitted_answer.answer).lower()
            keywords = question.expected_keywords or []
            matched = sum(1 for kw in keywords if kw.lower() in answer_lower)
            is_correct = matched == len(keywords)
            score = question.points * matched / len(keywords) if keywords else 0
            
        elif question.question_type == "matching":
            # Check pairs
            correct_pairs = question.matching_pairs or []
            answer_pairs = submitted_answer.answer or []
            matched = sum(1 for cp in correct_pairs if cp in answer_pairs)
            is_correct = matched == len(correct_pairs)
            score = question.points * matched / len(correct_pairs) if correct_pairs else 0
            
        elif question.question_type == "essay":
            # Essays need AI or manual grading
            score = 0
            feedback = "Awaiting AI grading"
            grading_status = "pending"
            graded_by = "pending"
        
        if is_correct:
            correct_count += 1
        total_score += score
        
        # Determine grading status for this answer
        if question.question_type == "essay":
            answer_grading_status = "pending"
            answer_graded_by = "pending"
        else:
            # Objective questions are auto-graded
            answer_grading_status = "completed"
            answer_graded_by = "system"
        
        # Save answer
        answer = Answer(
            test_id=test.id,
            question_id=submitted_answer.question_id,
            answer=submitted_answer.answer,
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            grading_status=answer_grading_status,
            graded_by=answer_graded_by,
        )
        db.add(answer)
    
    # Update test
    test.status = "completed"
    test.completed_at = datetime.utcnow()
    test.score = total_score
    
    await db.commit()
    
    # Calculate if passed (>= 60%)
    passed = (total_score / test.max_score * 100) >= 60 if test.max_score > 0 else False
    
    return TestSubmitResponse(
        testId=test.id,
        score=total_score,
        maxScore=test.max_score,
        correctAnswers=correct_count,
        totalQuestions=len(questions),
        passed=passed,
    )


@router.get("/{test_id}/results", response_model=TestResultResponse)
async def get_test_results(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed test results.
    """
    # Get test with project
    result = await db.execute(
        select(Test).where(Test.id == test_id).options(selectinload(Test.answers))
    )
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    # Check access
    if current_user.role == "student" and test.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Get project title
    project_result = await db.execute(
        select(Project.title).where(Project.id == test.project_id)
    )
    project_title = project_result.scalar_one_or_none() or "Unknown"
    
    percentage = (test.score / test.max_score * 100) if test.max_score > 0 else 0
    
    return TestResultResponse(
        testId=test.id,
        projectTitle=project_title,
        score=test.score or 0,
        maxScore=test.max_score,
        percentage=percentage,
        passed=percentage >= 60,
        completedAt=test.completed_at or datetime.utcnow(),
        answers=[
            AnswerResponse(
                questionId=a.question_id,
                answer=a.answer,
                isCorrect=a.is_correct,
                score=a.score,
                feedback=a.feedback,
            )
            for a in test.answers
        ],
    )


@router.get("/{test_id}/details")
async def get_test_details_for_teacher(
    test_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed test information for teacher review.
    Includes all answers with questions and grading details.
    """
    # Get test with student
    result = await db.execute(
        select(Test)
        .where(Test.id == test_id)
        .options(selectinload(Test.answers), selectinload(Test.student))
    )
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    # Verify teacher owns this project
    project_result = await db.execute(
        select(Project).where(
            Project.id == test.project_id,
            Project.teacher_id == current_user.id,
        )
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Get questions for this test variant
    questions_result = await db.execute(
        select(Question).where(
            Question.project_id == test.project_id,
            Question.variant_number == test.variant_number,
        )
    )
    questions = {str(q.id): q for q in questions_result.scalars().all()}
    
    # Build detailed answers
    answers_detail = []
    for answer in test.answers:
        question = questions.get(str(answer.question_id))
        if not question:
            continue
        
        answers_detail.append({
            "questionId": str(answer.question_id),
            "questionText": question.text,
            "questionType": question.question_type,
            "options": question.options or [],
            "correctAnswer": question.correct_answer,
            "studentAnswer": answer.answer,
            "isCorrect": answer.is_correct,
            "score": answer.score,
            "maxScore": question.points,
            "feedback": answer.feedback,
            "gradingStatus": answer.grading_status,
            "gradedBy": answer.graded_by,
        })
    
    # Sort by question order if available
    # answers_detail.sort(key=lambda x: questions.get(x["questionId"], Question()).order)
    
    return {
        "testId": str(test.id),
        "projectId": str(test.project_id),
        "projectTitle": project.title,
        "studentId": str(test.student_id) if test.student_id else None,
        "studentEmail": test.student.email if test.student else None,
        "studentName": f"{test.student.first_name or ''} {test.student.last_name or ''}".strip() if test.student else None,
        "status": test.status,
        "score": test.score,
        "maxScore": test.max_score,
        "variantNumber": test.variant_number,
        "startedAt": test.started_at.isoformat() if test.started_at else None,
        "completedAt": test.completed_at.isoformat() if test.completed_at else None,
        "answers": answers_detail,
    }
