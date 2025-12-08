"""
AI Test Generation Service

Uses OpenAI GPT-4.1 with Assistants API and File Search to generate test questions.
Questions are grounded in document content from OpenAI Vector Store.

This approach:
1. Uses OpenAI's File Search tool (Assistants API)
2. Searches through indexed documents in Vector Store
3. Generates questions based on retrieved content
4. No local RAG or ChromaDB needed
"""

import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from openai import OpenAI

from app.core.config import settings
from app.services.openai_vectorstore import get_vectorstore_service


class AITestGenerator:
    """
    AI-powered test question generator.
    
    Uses RAG (Retrieval-Augmented Generation) to ensure questions
    are based on actual document content, minimizing hallucinations.
    """
    
    # Question type prompts
    QUESTION_TYPE_PROMPTS = {
        "single-choice": """
Generate a single-choice question with 4 options where only one is correct.
Return JSON format:
{
    "text": "question text",
    "options": ["option1", "option2", "option3", "option4"],
    "correctAnswer": 0  // index of correct option (0-3)
}""",
        
        "multiple-choice": """
Generate a multiple-choice question with 4 options where 2-3 are correct.
Return JSON format:
{
    "text": "question text",
    "options": ["option1", "option2", "option3", "option4"],
    "correctAnswers": [0, 2]  // indices of correct options
}""",
        
        "true-false": """
Generate a true/false statement question.
Return JSON format:
{
    "text": "statement text",
    "correctAnswer": true  // or false
}""",
        
        "short-answer": """
Generate a short-answer question requiring a brief response.
Return JSON format:
{
    "text": "question text",
    "expectedKeywords": ["keyword1", "keyword2"]  // expected keywords in answer
}""",
        
        "essay": """
Generate an essay question requiring a detailed response.
Return JSON format:
{
    "text": "question text",
    "rubric": ["criteria1", "criteria2", "criteria3"]  // grading criteria
}""",
        
        "matching": """
Generate a matching question with 4-5 pairs to match.
Return JSON format:
{
    "text": "Match the following items:",
    "pairs": [
        {"left": "term1", "right": "definition1"},
        {"left": "term2", "right": "definition2"}
    ]
}""",
    }
    
    def __init__(self):
        """Initialize AI generator with OpenAI client and Vector Store service."""
        self.openai = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.vs_service = get_vectorstore_service()
    
    def generate_questions(
        self,
        project_id: str,
        document_ids: List[str],
        question_configs: List[Dict[str, Any]],
        topic_hint: Optional[str] = None,
        vector_store_id: Optional[str] = None,
        target_language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Generate test questions based on documents using OpenAI File Search.
        
        Args:
            project_id: Project ID (used to look up vector store if not provided)
            document_ids: List of document IDs (not used anymore - files in vector store)
            question_configs: List of {type, count} configurations
            topic_hint: Optional topic hint for better context retrieval
            vector_store_id: OpenAI Vector Store ID (if known)
            target_language: Language code for generated questions (en, ru, ua, pl)
            
        Returns:
            List of generated question dictionaries
        """
        if not vector_store_id:
            # Get vector store ID from project - this should be passed from endpoint
            raise ValueError("vector_store_id is required for question generation")
        
        # Use the Vector Store service to generate questions with File Search
        all_questions = self.vs_service.generate_questions(
            vector_store_id=vector_store_id,
            question_configs=question_configs,
            topic_hint=topic_hint,
            target_language=target_language,
        )
        
        # Validate and ensure proper formatting
        valid_questions = []
        for q in all_questions:
            if self.validate_question(q):
                valid_questions.append(q)
            else:
                print(f"Invalid question skipped: {q}")
        
        return valid_questions
    
    def generate_questions_direct(
        self,
        context: str,
        question_configs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate questions directly from provided context (without File Search).
        
        This is a fallback method when Vector Store is not available.
        
        Args:
            context: Text content to generate questions from
            question_configs: List of {type, count} configurations
            
        Returns:
            List of generated question dictionaries
        """
        all_questions = []
        
        for config in question_configs:
            question_type = config["type"]
            count = config["count"]
            
            questions = self._generate_questions_of_type(
                context=context,
                question_type=question_type,
                count=count,
            )
            
            all_questions.extend(questions)
        
        return all_questions
    
    def _generate_questions_of_type(
        self,
        context: str,
        question_type: str,
        count: int,
    ) -> List[Dict[str, Any]]:
        """Generate questions of a specific type."""
        type_prompt = self.QUESTION_TYPE_PROMPTS.get(question_type)
        if not type_prompt:
            raise ValueError(f"Unknown question type: {question_type}")
        
        system_prompt = f"""You are an expert educational assessment creator.
Your task is to generate high-quality test questions based ONLY on the provided educational content.

CRITICAL RULES:
1. Questions MUST be based solely on the provided content - do NOT invent or assume information
2. All facts, terms, and concepts must come directly from the source material
3. Questions should test understanding, not just memorization
4. Use clear, unambiguous language
5. Ensure options in multiple-choice questions are plausible but clearly distinguishable
6. Return ONLY valid JSON - no explanations or additional text

{type_prompt}

Generate exactly {count} questions of this type."""

        user_prompt = f"""Based on the following educational content, generate {count} {question_type} question(s).

EDUCATIONAL CONTENT:
---
{context}
---

Return a JSON array of {count} question(s). Each question must be directly based on the content above.
IMPORTANT: Return ONLY the JSON array, nothing else."""

        try:
            response = self.openai.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            
            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Handle both array and object responses
            if isinstance(result, list):
                questions = result
            elif "questions" in result:
                questions = result["questions"]
            else:
                questions = [result]
            
            # Add type and points to each question
            for q in questions:
                q["type"] = question_type
                q["points"] = 1  # Default points
            
            return questions[:count]
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return []
        except Exception as e:
            print(f"Error generating questions: {e}")
            return []
    
    def validate_question(self, question: Dict[str, Any]) -> bool:
        """
        Validate a generated question has required fields.
        
        Args:
            question: Question dictionary to validate
            
        Returns:
            True if valid
        """
        question_type = question.get("type")
        
        if not question.get("text"):
            return False
        
        if question_type == "single-choice":
            return (
                "options" in question and
                len(question["options"]) >= 2 and
                "correctAnswer" in question and
                isinstance(question["correctAnswer"], int) and
                0 <= question["correctAnswer"] < len(question["options"])
            )
        
        elif question_type == "multiple-choice":
            return (
                "options" in question and
                len(question["options"]) >= 2 and
                "correctAnswers" in question and
                isinstance(question["correctAnswers"], list) and
                all(isinstance(i, int) for i in question["correctAnswers"])
            )
        
        elif question_type == "true-false":
            return (
                "correctAnswer" in question and
                isinstance(question["correctAnswer"], bool)
            )
        
        elif question_type == "short-answer":
            return (
                "expectedKeywords" in question and
                isinstance(question["expectedKeywords"], list)
            )
        
        elif question_type == "essay":
            return "rubric" in question
        
        elif question_type == "matching":
            return (
                "pairs" in question and
                isinstance(question["pairs"], list) and
                len(question["pairs"]) >= 2
            )
        
        return False


# Global generator instance
ai_generator: Optional[AITestGenerator] = None


def get_ai_generator() -> AITestGenerator:
    """Get or create AI generator instance."""
    global ai_generator
    if ai_generator is None:
        ai_generator = AITestGenerator()
    return ai_generator
