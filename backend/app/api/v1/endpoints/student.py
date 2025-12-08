"""
Student Endpoints

Student-specific features: email management, statistics.
"""

from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.deps import get_db, get_current_student
from app.core.security import verify_password, get_password_hash
from app.models.user import User
from app.models.test import Test
from app.models.project import Project
from app.models.student_email import StudentEmail
from app.schemas.student import (
    StudentEmailCreate,
    StudentEmailResponse,
    StudentStatistics,
    StudentStatisticsDetailed,
    CompletedTestInfo,
    UpcomingTestInfo,
)
from app.schemas.user import PasswordChange
from app.schemas.common import MessageResponse

router = APIRouter()


# ============== Email Management ==============

@router.get("/emails", response_model=list[StudentEmailResponse])
async def get_student_emails(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all emails for current student.
    """
    # Include primary email from user account
    result = await db.execute(
        select(StudentEmail).where(StudentEmail.user_id == current_user.id)
    )
    additional_emails = result.scalars().all()
    
    # Build response with primary email first
    emails = [
        StudentEmailResponse(
            id=current_user.id,
            email=current_user.email,
            isPrimary=True,
            institution="Primary Account",
            createdAt=current_user.created_at,
        )
    ]
    
    for email in additional_emails:
        emails.append(
            StudentEmailResponse(
                id=email.id,
                email=email.email,
                isPrimary=email.is_primary,
                institution=email.institution,
                createdAt=email.created_at,
            )
        )
    
    return emails


@router.post("/emails", response_model=StudentEmailResponse, status_code=status.HTTP_201_CREATED)
async def add_student_email(
    email_data: StudentEmailCreate,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new email to student account.
    """
    # Check if email already exists
    existing = await db.execute(
        select(StudentEmail).where(StudentEmail.email == email_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use",
        )
    
    # Also check main user emails
    existing_user = await db.execute(
        select(User).where(User.email == email_data.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use",
        )
    
    email = StudentEmail(
        user_id=current_user.id,
        email=email_data.email,
        institution=email_data.institution,
        is_primary=False,
    )
    
    db.add(email)
    await db.commit()
    await db.refresh(email)
    
    return StudentEmailResponse(
        id=email.id,
        email=email.email,
        isPrimary=email.is_primary,
        institution=email.institution,
        createdAt=email.created_at,
    )


@router.delete("/emails/{email_id}", response_model=MessageResponse)
async def delete_student_email(
    email_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an email from student account.
    Cannot delete primary email.
    """
    # Cannot delete primary email (user's main email)
    if email_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete primary email",
        )
    
    result = await db.execute(
        select(StudentEmail).where(
            StudentEmail.id == email_id,
            StudentEmail.user_id == current_user.id,
        )
    )
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    await db.delete(email)
    await db.commit()
    
    return MessageResponse(message="Email removed successfully")


@router.patch("/emails/{email_id}/primary", response_model=MessageResponse)
async def set_primary_email(
    email_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Set an email as primary.
    This swaps the current primary email.
    """
    # Get the email to make primary
    result = await db.execute(
        select(StudentEmail).where(
            StudentEmail.id == email_id,
            StudentEmail.user_id == current_user.id,
        )
    )
    new_primary = result.scalar_one_or_none()
    
    if not new_primary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    # Swap emails
    old_primary_email = current_user.email
    current_user.email = new_primary.email
    new_primary.email = old_primary_email
    new_primary.is_primary = False
    
    await db.commit()
    
    return MessageResponse(message="Primary email changed successfully")


# ============== Password Change ==============

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password for current student.
    """
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return MessageResponse(message="Password changed successfully")


# ============== Statistics ==============

@router.get("/statistics", response_model=StudentStatistics)
async def get_student_statistics(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics for current student.
    """
    # Count total tests
    total_query = select(func.count()).where(Test.student_id == current_user.id)
    total_result = await db.execute(total_query)
    total_tests = total_result.scalar() or 0
    
    # Count completed tests
    completed_query = select(func.count()).where(
        Test.student_id == current_user.id,
        Test.status == "completed",
    )
    completed_result = await db.execute(completed_query)
    completed_tests = completed_result.scalar() or 0
    
    # Calculate average score
    avg_query = select(func.avg(Test.score / Test.max_score * 100)).where(
        Test.student_id == current_user.id,
        Test.status == "completed",
        Test.max_score > 0,
    )
    avg_result = await db.execute(avg_query)
    average_score = avg_result.scalar() or 0
    
    return StudentStatistics(
        totalTests=total_tests,
        completedTests=completed_tests,
        averageScore=round(average_score, 1),
    )


@router.get("/tests/completed", response_model=list[CompletedTestInfo])
async def get_completed_tests(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of completed tests for current student.
    """
    result = await db.execute(
        select(Test, Project.title, Project.group_name)
        .join(Project, Test.project_id == Project.id)
        .where(
            Test.student_id == current_user.id,
            Test.status == "completed",
        )
        .order_by(Test.completed_at.desc())
    )
    
    tests = []
    for test, title, group_name in result.all():
        tests.append(
            CompletedTestInfo(
                id=test.id,
                title=title,
                groupName=group_name,
                score=test.score or 0,
                maxScore=test.max_score,
                completedAt=test.completed_at,
            )
        )
    
    return tests


@router.get("/tests/upcoming", response_model=list[UpcomingTestInfo])
async def get_upcoming_tests(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of upcoming tests for current student.
    Based on projects where student is allowed (by email).
    Shows tests that are:
    - status=active (teacher manually activated), OR
    - status=ready with scheduled time (shows as scheduled until start_time)
    """
    # Get all student emails
    student_emails = [current_user.email]
    emails_result = await db.execute(
        select(StudentEmail.email).where(StudentEmail.user_id == current_user.id)
    )
    for row in emails_result.all():
        student_emails.append(row[0])
    
    now = datetime.utcnow()
    
    # Find projects that are ready or active and where student is allowed
    result = await db.execute(
        select(Project)
        .where(
            Project.status.in_(["ready", "active"]),
            or_(
                Project.end_time.is_(None),
                Project.end_time > now,
            ),
        )
        .order_by(Project.start_time.asc().nullsfirst())
    )
    
    projects = result.scalars().all()
    upcoming = []
    
    for project in projects:
        # Check if student email is in allowed list
        allowed = project.allowed_students or []
        
        # Student sees project ONLY if their email is explicitly added
        # If allowed_students is empty - don't show project to student
        if not allowed:
            continue
        
        is_allowed = any(email.lower() in [a.lower() for a in allowed] for email in student_emails)
        
        if not is_allowed:
            continue
        
        # Check if student hasn't completed this project yet
        existing_test = await db.execute(
            select(Test).where(
                Test.project_id == project.id,
                Test.student_id == current_user.id,
                Test.status == "completed",
            )
        )
        if existing_test.scalar_one_or_none():
            continue
        
        # Determine test status for display
        # "available" - student can start the test now
        # "scheduled" - test is scheduled but not yet available
        test_status = "scheduled"
        
        if project.status == "active":
            # Teacher manually activated - test is available
            test_status = "available"
        elif project.status == "ready":
            # Scheduled test - check if start time has passed
            if project.start_time and project.start_time <= now:
                test_status = "available"
            elif not project.start_time:
                # No start_time set but status is ready - this shouldn't happen normally
                # but treat as scheduled (waiting for teacher to activate)
                test_status = "scheduled"
        
        upcoming.append(
            UpcomingTestInfo(
                id=str(project.id),
                projectId=str(project.id),
                title=project.title,
                groupName=project.group_name,
                startTime=project.start_time,
                endTime=project.end_time,
                duration=project.total_time or 60,
                status=test_status,
            )
        )
    
    return upcoming


# ============== Test Taking ==============

@router.post("/tests/{project_id}/start")
async def start_test_for_student(
    project_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a test for the given project.
    Creates a new Test record for the student.
    Assigns a random variant if multiple variants exist.
    """
    from app.models.test import Question
    import random
    
    # Get the project
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check if student is allowed
    student_emails = [current_user.email.lower()]
    emails_result = await db.execute(
        select(StudentEmail.email).where(StudentEmail.user_id == current_user.id)
    )
    for row in emails_result.all():
        student_emails.append(row[0].lower())
    
    allowed = [e.lower() for e in (project.allowed_students or [])]
    if not any(email in allowed for email in student_emails):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to take this test",
        )
    
    # Check if test is accessible
    now = datetime.utcnow()
    
    # Test is accessible only if:
    # 1. status is "active" (teacher manually activated), OR
    # 2. status is "ready" AND current time is within start_time/end_time window
    if project.status == "active":
        # Manually activated - check end_time if set
        if project.end_time and project.end_time < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This test has ended",
            )
    elif project.status == "ready":
        # Scheduled test - check time window
        if project.start_time and project.start_time > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This test has not started yet",
            )
        if project.end_time and project.end_time < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This test has ended",
            )
        # If start_time passed, auto-activate is assumed
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This test is not currently available",
        )
    
    # Check if student already has an in-progress or completed test
    existing_test = await db.execute(
        select(Test).where(
            Test.project_id == project_id,
            Test.student_id == current_user.id,
        )
    )
    existing = existing_test.scalar_one_or_none()
    
    if existing:
        if existing.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already completed this test",
            )
        # Return existing in-progress test with the same variant
        if existing.status == "in-progress":
            # Get questions for this test's variant
            questions_result = await db.execute(
                select(Question)
                .where(
                    Question.project_id == project_id,
                    Question.variant_number == existing.variant_number
                )
                .order_by(Question.order)
            )
            questions = questions_result.scalars().all()
            
            return {
                "id": str(existing.id),
                "projectId": str(project_id),
                "status": existing.status,
                "startedAt": existing.started_at,
                "maxScore": existing.max_score,
                "variantNumber": existing.variant_number,
                "questions": [
                    {
                        "id": str(q.id),
                        "type": q.question_type,
                        "text": q.text,
                        "points": q.points,
                        "options": q.options,
                    }
                    for q in questions
                ],
                "answers": [],
            }
    
    # Get available variants for this project
    variants_result = await db.execute(
        select(Question.variant_number)
        .where(Question.project_id == project_id)
        .distinct()
    )
    available_variants = [v[0] for v in variants_result.fetchall()]
    
    if not available_variants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This test has no questions yet",
        )
    
    # Randomly assign a variant to the student
    assigned_variant = random.choice(available_variants)
    
    # Get questions for the assigned variant only
    questions_result = await db.execute(
        select(Question)
        .where(
            Question.project_id == project_id,
            Question.variant_number == assigned_variant
        )
        .order_by(Question.order)
    )
    questions = questions_result.scalars().all()
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This test has no questions yet",
        )
    
    # Calculate max score for this variant
    max_score = sum(q.points for q in questions)
    
    # Create new test with assigned variant
    new_test = Test(
        project_id=project_id,
        student_id=current_user.id,
        status="in-progress",
        started_at=datetime.utcnow(),
        max_score=max_score,
        score=0,
        variant_number=assigned_variant,
    )
    
    db.add(new_test)
    await db.commit()
    await db.refresh(new_test)
    
    return {
        "id": str(new_test.id),
        "projectId": str(project_id),
        "status": new_test.status,
        "startedAt": new_test.started_at,
        "maxScore": max_score,
        "variantNumber": assigned_variant,
        "questions": [
            {
                "id": str(q.id),
                "type": q.question_type,
                "text": q.text,
                "points": q.points,
                "options": q.options,
            }
            for q in questions
        ],
        "answers": [],
    }


@router.get("/tests/{test_id}")
async def get_student_test(
    test_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Get test details for student.
    """
    from app.models.test import Question, Answer
    
    # Get test
    test_result = await db.execute(
        select(Test).where(
            Test.id == test_id,
            Test.student_id == current_user.id,
        )
    )
    test = test_result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    # Get questions for the student's assigned variant only
    questions_result = await db.execute(
        select(Question)
        .where(
            Question.project_id == test.project_id,
            Question.variant_number == test.variant_number
        )
        .order_by(Question.order)
    )
    questions = questions_result.scalars().all()
    
    # Get answers
    answers_result = await db.execute(
        select(Answer).where(Answer.test_id == test_id)
    )
    answers = answers_result.scalars().all()
    
    return {
        "id": str(test.id),
        "projectId": str(test.project_id),
        "status": test.status,
        "startedAt": test.started_at,
        "completedAt": test.completed_at,
        "maxScore": test.max_score,
        "score": test.score,
        "questions": [
            {
                "id": str(q.id),
                "type": q.question_type,
                "text": q.text,
                "points": q.points,
                "options": q.options,
            }
            for q in questions
        ],
        "answers": [
            {
                "questionId": str(a.question_id),
                "answer": a.answer,
                "isCorrect": a.is_correct,
                "score": a.score,
            }
            for a in answers
        ],
    }


@router.post("/tests/{test_id}/answers")
async def submit_answer(
    test_id: UUID,
    answer_data: dict,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit an answer for a question.
    """
    from app.models.test import Question, Answer
    
    # Get test
    test_result = await db.execute(
        select(Test).where(
            Test.id == test_id,
            Test.student_id == current_user.id,
            Test.status == "in-progress",
        )
    )
    test = test_result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found or already completed",
        )
    
    question_id = answer_data.get("questionId")
    answer_value = answer_data.get("answer")
    
    if not question_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="questionId is required",
        )
    
    # Get question
    question_result = await db.execute(
        select(Question).where(Question.id == question_id)
    )
    question = question_result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
    
    # Check/create answer
    existing_answer = await db.execute(
        select(Answer).where(
            Answer.test_id == test_id,
            Answer.question_id == question_id,
        )
    )
    answer = existing_answer.scalar_one_or_none()
    
    if answer:
        answer.answer = answer_value
    else:
        answer = Answer(
            test_id=test_id,
            question_id=question_id,
            answer=answer_value,
        )
        db.add(answer)
    
    await db.commit()
    await db.refresh(answer)
    
    return {
        "questionId": str(answer.question_id),
        "answer": answer.answer,
    }


@router.post("/tests/{test_id}/submit")
async def submit_test(
    test_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit the entire test for grading.
    """
    from app.models.test import Question, Answer
    
    # Get test
    test_result = await db.execute(
        select(Test).where(
            Test.id == test_id,
            Test.student_id == current_user.id,
        )
    )
    test = test_result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    if test.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test already completed",
        )
    
    # Get questions for the student's variant ONLY
    questions_result = await db.execute(
        select(Question).where(
            Question.project_id == test.project_id,
            Question.variant_number == test.variant_number
        )
    )
    questions = {str(q.id): q for q in questions_result.scalars().all()}
    
    answers_result = await db.execute(
        select(Answer).where(Answer.test_id == test_id)
    )
    answers = answers_result.scalars().all()
    
    # Grade answers
    total_score = 0
    correct_count = 0
    
    print(f"[GRADING] Test {test_id}, Variant {test.variant_number}")
    print(f"[GRADING] Total questions in variant: {len(questions)}")
    print(f"[GRADING] Total answers submitted: {len(answers)}")
    
    for answer in answers:
        question = questions.get(str(answer.question_id))
        if not question:
            print(f"[GRADING] Question {answer.question_id} not found in variant questions")
            continue
        
        is_correct = False
        score = 0
        
        print(f"[GRADING] Question: {question.question_type}, Correct: {question.correct_answer}, Student: {answer.answer}")
        
        # Simple grading based on question type
        if question.question_type == "single-choice":
            correct_answer = question.correct_answer
            student_answer = answer.answer
            
            # Handle different formats
            try:
                # Both could be ints, strings, or strings representing ints
                if isinstance(correct_answer, int):
                    correct_int = correct_answer
                elif isinstance(correct_answer, str) and correct_answer.isdigit():
                    correct_int = int(correct_answer)
                else:
                    correct_int = None
                    
                if isinstance(student_answer, int):
                    student_int = student_answer
                elif isinstance(student_answer, str) and student_answer.isdigit():
                    student_int = int(student_answer)
                else:
                    student_int = None
                
                if correct_int is not None and student_int is not None:
                    is_correct = student_int == correct_int
                else:
                    # Fallback to string comparison
                    is_correct = str(student_answer) == str(correct_answer)
            except (ValueError, TypeError):
                is_correct = str(student_answer) == str(correct_answer)
                
            if is_correct:
                score = question.points
                correct_count += 1
        
        elif question.question_type == "true-false":
            # Handle various representations of true/false
            student_str = str(answer.answer).lower()
            correct_str = str(question.correct_answer).lower()
            
            # Normalize to boolean comparison
            student_bool = student_str in ['true', '1', 'yes']
            correct_bool = correct_str in ['true', '1', 'yes']
            
            is_correct = student_bool == correct_bool
            if is_correct:
                score = question.points
                correct_count += 1
        
        elif question.question_type == "multiple-choice":
            correct_answers = question.correct_answer if isinstance(question.correct_answer, list) else []
            student_answers = answer.answer if isinstance(answer.answer, list) else []
            # Convert to sets of strings for comparison
            correct_set = set(str(x) for x in correct_answers)
            student_set = set(str(x) for x in student_answers)
            is_correct = correct_set == student_set
            if is_correct:
                score = question.points
                correct_count += 1
        
        else:
            # For short-answer, essay, matching - manual review needed
            score = 0
        
        print(f"[GRADING] Result: is_correct={is_correct}, score={score}")
        
        answer.is_correct = is_correct
        answer.score = score
        total_score += score
    
    # Calculate correct max_score from the variant's questions
    correct_max_score = sum(q.points for q in questions.values())
    
    print(f"[GRADING] FINAL: total_score={total_score}, correct_count={correct_count}, max_score={correct_max_score}")
    
    # Update test
    test.status = "completed"
    test.completed_at = datetime.utcnow()
    test.score = total_score
    test.max_score = correct_max_score  # Fix max_score if it was wrong
    
    await db.commit()
    
    return {
        "testId": str(test.id),
        "score": total_score,
        "maxScore": correct_max_score,
        "correctAnswers": correct_count,
        "totalQuestions": len(questions),
        "passed": total_score >= (correct_max_score * 0.6) if correct_max_score > 0 else False,
    }


@router.get("/tests/{test_id}/results")
async def get_test_results(
    test_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Get test results after completion.
    """
    from app.models.test import Question, Answer
    
    # Get test
    test_result = await db.execute(
        select(Test).where(
            Test.id == test_id,
            Test.student_id == current_user.id,
        )
    )
    test = test_result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    # Get project info
    project_result = await db.execute(
        select(Project).where(Project.id == test.project_id)
    )
    project = project_result.scalar_one_or_none()
    
    # Get questions for the student's variant ONLY
    questions_result = await db.execute(
        select(Question)
        .where(
            Question.project_id == test.project_id,
            Question.variant_number == test.variant_number
        )
        .order_by(Question.order)
    )
    questions = questions_result.scalars().all()
    
    # Get answers
    answers_result = await db.execute(
        select(Answer).where(Answer.test_id == test_id)
    )
    answers = {str(a.question_id): a for a in answers_result.scalars().all()}
    
    return {
        "id": str(test.id),
        "projectId": str(test.project_id),
        "projectTitle": project.title if project else "Unknown",
        "status": test.status,
        "startedAt": test.started_at,
        "completedAt": test.completed_at,
        "score": test.score,
        "maxScore": test.max_score,
        "passed": test.score >= (test.max_score * 0.6) if test.max_score > 0 else False,
        "questions": [
            {
                "id": str(q.id),
                "type": q.question_type,
                "text": q.text,
                "points": q.points,
                "options": q.options,
                "correctAnswer": q.correct_answer,  # Show correct answer in results
                "studentAnswer": answers.get(str(q.id)).answer if str(q.id) in answers else None,
                "isCorrect": answers.get(str(q.id)).is_correct if str(q.id) in answers else False,
                "score": answers.get(str(q.id)).score if str(q.id) in answers else 0,
            }
            for q in questions
        ],
    }


# ============== Contact Requests (Notifications) ==============

@router.get("/contact-requests")
async def get_contact_requests(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all contact requests from teachers for the current student.
    These are participants records where student_user_id matches current user.
    """
    from app.models.participant import Participant
    
    # Get all student emails
    student_emails = [current_user.email.lower()]
    emails_result = await db.execute(
        select(StudentEmail.email).where(StudentEmail.user_id == current_user.id)
    )
    for row in emails_result.all():
        student_emails.append(row[0].lower())
    
    # Find participants that match student's emails
    result = await db.execute(
        select(Participant, User)
        .join(User, Participant.teacher_id == User.id)
        .where(
            or_(
                Participant.student_user_id == current_user.id,
                Participant.email.in_(student_emails),
            )
        )
        .order_by(Participant.created_at.desc())
    )
    
    requests = []
    for participant, teacher in result.all():
        requests.append({
            "id": str(participant.id),
            "teacherId": str(teacher.id),
            "teacherName": f"{teacher.first_name} {teacher.last_name}",
            "teacherEmail": teacher.email,
            "status": participant.confirmation_status,
            "createdAt": participant.created_at,
        })
    
    return requests


@router.post("/contact-requests/{request_id}/confirm")
async def confirm_contact_request(
    request_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm a contact request from a teacher.
    """
    from app.models.participant import Participant
    
    # Get all student emails
    student_emails = [current_user.email.lower()]
    emails_result = await db.execute(
        select(StudentEmail.email).where(StudentEmail.user_id == current_user.id)
    )
    for row in emails_result.all():
        student_emails.append(row[0].lower())
    
    # Find the participant record
    result = await db.execute(
        select(Participant).where(
            Participant.id == request_id,
            or_(
                Participant.student_user_id == current_user.id,
                Participant.email.in_(student_emails),
            )
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact request not found",
        )
    
    if participant.confirmation_status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already confirmed",
        )
    
    participant.confirmation_status = "confirmed"
    participant.student_user_id = current_user.id
    
    await db.commit()
    
    return {"message": "Contact request confirmed", "status": "confirmed"}


@router.post("/contact-requests/{request_id}/reject")
async def reject_contact_request(
    request_id: UUID,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Reject a contact request from a teacher.
    """
    from app.models.participant import Participant
    
    # Get all student emails
    student_emails = [current_user.email.lower()]
    emails_result = await db.execute(
        select(StudentEmail.email).where(StudentEmail.user_id == current_user.id)
    )
    for row in emails_result.all():
        student_emails.append(row[0].lower())
    
    # Find the participant record
    result = await db.execute(
        select(Participant).where(
            Participant.id == request_id,
            or_(
                Participant.student_user_id == current_user.id,
                Participant.email.in_(student_emails),
            )
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact request not found",
        )
    
    participant.confirmation_status = "rejected"
    
    await db.commit()
    
    return {"message": "Contact request rejected", "status": "rejected"}


@router.get("/contact-requests/count")
async def get_pending_contact_requests_count(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Get count of pending contact requests.
    """
    from app.models.participant import Participant
    
    # Get all student emails
    student_emails = [current_user.email.lower()]
    emails_result = await db.execute(
        select(StudentEmail.email).where(StudentEmail.user_id == current_user.id)
    )
    for row in emails_result.all():
        student_emails.append(row[0].lower())
    
    # Count pending requests
    result = await db.execute(
        select(func.count()).select_from(Participant).where(
            or_(
                Participant.student_user_id == current_user.id,
                Participant.email.in_(student_emails),
            ),
            Participant.confirmation_status == "pending",
        )
    )
    count = result.scalar() or 0
    
    return {"count": count}