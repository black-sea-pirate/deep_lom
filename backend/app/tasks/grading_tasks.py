"""
AI Grading Tasks

Celery tasks for asynchronous AI grading of written responses.
"""

import asyncio
from typing import Dict, Any, Optional
from uuid import UUID

from app.celery_app import celery_app
from app.services.ai_grading import get_grading_service
from app.db.session import sync_session_maker
from app.models.test import Answer, Question, Test
from app.models.project import Project
from sqlalchemy import select


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="grade_written_answer")
def grade_written_answer(
    self,
    answer_id: str,
    question_id: str,
    project_id: str,
):
    """
    Grade a single written answer (essay or short-answer) using AI.
    
    Args:
        answer_id: UUID of the answer to grade
        question_id: UUID of the question
        project_id: UUID of the project (for Vector Store access)
    """
    grading_service = get_grading_service()
    
    try:
        self.update_state(state="GRADING", meta={"answer_id": answer_id})
        
        with sync_session_maker() as session:
            # Get answer, question, and project
            answer = session.execute(
                select(Answer).where(Answer.id == answer_id)
            ).scalar_one_or_none()
            
            if not answer:
                raise ValueError(f"Answer not found: {answer_id}")
            
            question = session.execute(
                select(Question).where(Question.id == question_id)
            ).scalar_one_or_none()
            
            if not question:
                raise ValueError(f"Question not found: {question_id}")
            
            project = session.execute(
                select(Project).where(Project.id == project_id)
            ).scalar_one_or_none()
            
            # Update status to in_progress
            answer.grading_status = "in_progress"
            session.commit()
            
            # Get vector store ID for RAG context
            vector_store_id = project.openai_vector_store_id if project else None
            
            # Grade based on question type
            if question.question_type == "matching":
                # Grade matching question
                grading_result = run_async(grading_service.grade_matching(
                    student_pairs=answer.answer or [],
                    correct_pairs=question.matching_pairs or [],
                    max_points=question.points,
                ))
            else:
                # Grade essay or short-answer
                grading_result = run_async(grading_service.grade_answer(
                    question_type=question.question_type,
                    question_text=question.text,
                    student_answer=str(answer.answer) if answer.answer else "",
                    expected_keywords=question.expected_keywords,
                    rubric=question.rubric,
                    vector_store_id=vector_store_id,
                    max_points=question.points,
                ))
            
            # Update answer with grading results
            answer.score = grading_result.get("score", 0)
            answer.feedback = grading_result.get("overallFeedback", "")
            answer.ai_grading_details = grading_result
            answer.graded_by = grading_result.get("gradedBy", "ai")
            answer.grading_status = "completed" if grading_result.get("success") else "failed"
            
            # Determine if answer is "correct" (for stats)
            # Consider >= 60% as "correct" for written answers
            percentage = grading_result.get("percentage", 0)
            answer.is_correct = percentage >= 60
            
            session.commit()
            
            return {
                "success": True,
                "answer_id": answer_id,
                "score": answer.score,
                "graded_by": answer.graded_by,
            }
            
    except Exception as e:
        # Mark as failed
        try:
            with sync_session_maker() as session:
                answer = session.execute(
                    select(Answer).where(Answer.id == answer_id)
                ).scalar_one_or_none()
                
                if answer:
                    answer.grading_status = "failed"
                    answer.graded_by = "pending_manual_review"
                    answer.feedback = f"Auto-grading failed: {str(e)}"
                    session.commit()
        except:
            pass
        
        raise


@celery_app.task(bind=True, name="grade_test_written_answers")
def grade_test_written_answers(
    self,
    test_id: str,
):
    """
    Grade all written answers (essay, short-answer, matching) in a test.
    
    This is called after a student submits their test.
    Grades are computed in background and test score is updated.
    
    Args:
        test_id: UUID of the submitted test
    """
    try:
        self.update_state(state="PROCESSING", meta={"test_id": test_id, "step": "loading"})
        
        with sync_session_maker() as session:
            # Get test with answers
            test = session.execute(
                select(Test).where(Test.id == test_id)
            ).scalar_one_or_none()
            
            if not test:
                raise ValueError(f"Test not found: {test_id}")
            
            project_id = str(test.project_id)
            
            # Get answers that need AI grading
            answers = session.execute(
                select(Answer)
                .join(Question, Answer.question_id == Question.id)
                .where(
                    Answer.test_id == test_id,
                    Question.question_type.in_(["essay", "short-answer", "matching"]),
                )
            ).scalars().all()
            
            if not answers:
                return {"success": True, "message": "No written answers to grade", "test_id": test_id}
            
            total_answers = len(answers)
            graded_count = 0
            
            # Grade each answer
            for answer in answers:
                try:
                    self.update_state(
                        state="GRADING",
                        meta={
                            "test_id": test_id,
                            "progress": f"{graded_count + 1}/{total_answers}",
                        }
                    )
                    
                    # Get question for this answer
                    question = session.execute(
                        select(Question).where(Question.id == answer.question_id)
                    ).scalar_one_or_none()
                    
                    if not question:
                        continue
                    
                    # Get project for Vector Store
                    project = session.execute(
                        select(Project).where(Project.id == project_id)
                    ).scalar_one_or_none()
                    
                    vector_store_id = project.openai_vector_store_id if project else None
                    
                    grading_service = get_grading_service()
                    
                    # Update status
                    answer.grading_status = "in_progress"
                    session.commit()
                    
                    # Grade based on type
                    if question.question_type == "matching":
                        grading_result = run_async(grading_service.grade_matching(
                            student_pairs=answer.answer or [],
                            correct_pairs=question.matching_pairs or [],
                            max_points=question.points,
                        ))
                    else:
                        grading_result = run_async(grading_service.grade_answer(
                            question_type=question.question_type,
                            question_text=question.text,
                            student_answer=str(answer.answer) if answer.answer else "",
                            expected_keywords=question.expected_keywords,
                            rubric=question.rubric,
                            vector_store_id=vector_store_id,
                            max_points=question.points,
                        ))
                    
                    # Update answer
                    answer.score = grading_result.get("score", 0)
                    answer.feedback = grading_result.get("overallFeedback", "")
                    answer.ai_grading_details = grading_result
                    answer.graded_by = grading_result.get("gradedBy", "ai")
                    answer.grading_status = "completed" if grading_result.get("success") else "failed"
                    answer.is_correct = grading_result.get("percentage", 0) >= 60
                    
                    session.commit()
                    graded_count += 1
                    
                except Exception as e:
                    print(f"[AI_GRADING] Error grading answer {answer.id}: {e}")
                    answer.grading_status = "failed"
                    answer.graded_by = "pending_manual_review"
                    session.commit()
            
            # Recalculate test score after all AI grading
            all_answers = session.execute(
                select(Answer).where(Answer.test_id == test_id)
            ).scalars().all()
            
            total_score = sum(a.score or 0 for a in all_answers)
            test.score = total_score
            
            # Update test status to "graded" if it was "completed"
            if test.status == "completed":
                test.status = "graded"
            
            session.commit()
            
            return {
                "success": True,
                "test_id": test_id,
                "graded_answers": graded_count,
                "total_written_answers": total_answers,
                "final_score": total_score,
            }
            
    except Exception as e:
        raise
