"""
Test Generation Tasks

Celery tasks for AI test generation.
Uses sync database sessions to avoid event loop issues.
"""

from typing import List, Dict, Any
from uuid import UUID

from app.celery_app import celery_app
from app.services.ai_generator import get_ai_generator
from app.db.session import sync_session_maker
from app.models.test import Question
from app.models.project import Project
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload


@celery_app.task(bind=True, name="generate_test_questions")
def generate_test_questions(
    self,
    project_id: str,
    material_ids: List[str],
    num_variants: int = 1,
):
    """
    Generate test questions from materials using AI.
    
    This task:
    1. Gets project configuration (question types, counts)
    2. Generates N unique variants of tests using OpenAI Assistants API
    3. Saves questions to database with variant numbers
    
    Args:
        project_id: UUID of the project
        material_ids: List of material UUIDs to use as source
        num_variants: Number of unique test variants to generate (default: 1)
    """
    try:
        self.update_state(state="PROCESSING", meta={"step": "loading_config"})
        
        # Get project config using sync session
        with sync_session_maker() as session:
            project = session.execute(
                select(Project)
                .where(Project.id == project_id)
                .options(selectinload(Project.question_type_configs))
            ).scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project not found: {project_id}")
            
            # Build question configs
            question_configs = [
                {"type": qtc.question_type, "count": qtc.count}
                for qtc in project.question_type_configs
            ]
            
            if not question_configs:
                raise ValueError("No question type configurations found")
            
            # Use project.num_variants if set, otherwise use parameter or default to 1
            if num_variants == 1 and hasattr(project, 'num_variants') and project.num_variants:
                num_variants = project.num_variants
            
            # Get test language (default to English)
            test_language = getattr(project, 'test_language', 'en') or 'en'
            
            # Get vector store ID
            vector_store_id = project.openai_vector_store_id
            project_title = project.title
        
        if not vector_store_id:
            raise ValueError("Project has no Vector Store. Run vectorization first.")
        
        # Generate questions using OpenAI Vector Store
        generator = get_ai_generator()
        all_questions = []
        total_questions = 0
        
        # Generate N unique variants
        for variant_num in range(1, num_variants + 1):
            self.update_state(
                state="PROCESSING",
                meta={
                    "step": "generating",
                    "variant": variant_num,
                    "total_variants": num_variants,
                },
            )
            
            # Generate questions for this variant
            questions = generator.generate_questions(
                project_id=project_id,
                document_ids=material_ids,
                question_configs=question_configs,
                topic_hint=f"{project_title} (Variant {variant_num})",
                vector_store_id=vector_store_id,
                target_language=test_language,
            )
            
            if questions:
                # Add variant number to each question
                for q in questions:
                    q["variant_number"] = variant_num
                all_questions.extend(questions)
                total_questions += len(questions)
        
        if not all_questions:
            raise ValueError("No questions generated")
        
        self.update_state(
            state="PROCESSING",
            meta={"step": "saving", "questions": total_questions, "variants": num_variants},
        )
        
        # Save questions to database using sync session
        with sync_session_maker() as session:
            # Delete existing questions for this project
            session.execute(
                delete(Question).where(Question.project_id == project_id)
            )
            
            # Add new questions with variant numbers
            for i, q_data in enumerate(all_questions):
                # Handle correctAnswer - use explicit None check because 0 is a valid value
                correct_answer = q_data.get("correctAnswer")
                if correct_answer is None:
                    correct_answer = q_data.get("correctAnswers")
                
                question = Question(
                    project_id=UUID(project_id),
                    question_type=q_data["type"],
                    text=q_data["text"],
                    points=q_data.get("points", 1),
                    options=q_data.get("options"),
                    correct_answer=correct_answer,
                    expected_keywords=q_data.get("expectedKeywords"),
                    rubric=q_data.get("rubric"),
                    matching_pairs=q_data.get("pairs"),
                    variant_number=q_data.get("variant_number", 1),
                    order=i % (total_questions // num_variants) if num_variants > 0 else i,
                )
                session.add(question)
            
            # Update project status
            project = session.execute(
                select(Project).where(Project.id == project_id)
            ).scalar_one()
            project.status = "ready"
            
            session.commit()
        
        return {
            "status": "success",
            "project_id": project_id,
            "questions_generated": total_questions,
            "variants_generated": num_variants,
        }
        
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)},
        )
        raise


@celery_app.task(name="check_generation_status")
def check_generation_status(task_id: str) -> Dict[str, Any]:
    """
    Check the status of a generation task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task status and metadata
    """
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "meta": result.info if not result.ready() else None,
    }
