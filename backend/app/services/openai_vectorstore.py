"""
OpenAI Vector Store Service

Handles all interactions with OpenAI's Vector Store API:
- File uploads to OpenAI
- Vector Store creation and management
- File Search for RAG
- Test generation with Assistants API

This replaces local ChromaDB vectorization - all heavy lifting
is done by OpenAI servers.
"""

import os
import time
from typing import List, Optional, Dict, Any
from openai import OpenAI

from app.core.config import settings


class OpenAIVectorStoreService:
    """
    Service for managing OpenAI Vector Stores and File Search.
    
    Each project gets its own Vector Store to ensure data isolation.
    Files are uploaded directly to OpenAI - no local processing needed.
    """
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._assistants_cache: Dict[str, str] = {}  # vector_store_id -> assistant_id
    
    # ==================== File Operations ====================
    
    def upload_file(self, file_path: str, filename: str) -> str:
        """
        Upload a file to OpenAI Files API.
        
        Args:
            file_path: Local path to the file
            filename: Original filename for display
            
        Returns:
            OpenAI file ID (e.g., "file-abc123")
        """
        with open(file_path, "rb") as f:
            response = self.client.files.create(
                file=f,
                purpose="assistants",  # Required for Vector Store
            )
        
        return response.id
    
    def upload_file_bytes(self, file_bytes: bytes, filename: str) -> str:
        """
        Upload file bytes directly to OpenAI Files API.
        
        Args:
            file_bytes: File content as bytes
            filename: Original filename
            
        Returns:
            OpenAI file ID
        """
        # OpenAI SDK expects a file-like object with a name
        import io
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = filename
        
        response = self.client.files.create(
            file=file_obj,
            purpose="assistants",
        )
        
        return response.id
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from OpenAI.
        
        Args:
            file_id: OpenAI file ID
            
        Returns:
            True if deleted successfully
        """
        try:
            self.client.files.delete(file_id)
            return True
        except Exception as e:
            print(f"Error deleting file {file_id}: {e}")
            return False
    
    def get_file_status(self, file_id: str) -> Dict[str, Any]:
        """
        Get file status from OpenAI.
        
        Args:
            file_id: OpenAI file ID
            
        Returns:
            File metadata including status
        """
        file = self.client.files.retrieve(file_id)
        return {
            "id": file.id,
            "filename": file.filename,
            "bytes": file.bytes,
            "status": file.status,
            "purpose": file.purpose,
        }
    
    # ==================== Vector Store Operations ====================
    
    def create_vector_store(self, name: str, project_id: str) -> str:
        """
        Create a new Vector Store for a project.
        
        Args:
            name: Human-readable name (project title)
            project_id: Project UUID for identification
            
        Returns:
            Vector Store ID (e.g., "vs_abc123")
        """
        response = self.client.vector_stores.create(
            name=f"Mentis Project: {name}",
            metadata={
                "project_id": project_id,
                "platform": "mentis",
            },
        )
        
        return response.id
    
    def delete_vector_store(self, vector_store_id: str) -> bool:
        """
        Delete a Vector Store and all its files.
        
        Args:
            vector_store_id: Vector Store ID
            
        Returns:
            True if deleted successfully
        """
        try:
            self.client.vector_stores.delete(vector_store_id)
            return True
        except Exception as e:
            print(f"Error deleting vector store {vector_store_id}: {e}")
            return False
    
    def add_file_to_vector_store(
        self, 
        vector_store_id: str, 
        file_id: str,
        wait_for_completion: bool = True,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Add a file to a Vector Store for indexing.
        
        OpenAI will automatically:
        - Parse the file (PDF, DOCX, TXT, etc.)
        - Chunk the content
        - Create embeddings
        - Build search index
        
        Args:
            vector_store_id: Target Vector Store ID
            file_id: OpenAI file ID to add
            wait_for_completion: Wait for indexing to complete
            timeout: Max seconds to wait
            
        Returns:
            File status in vector store
        """
        # Add file to vector store
        print(f"Adding file {file_id} to vector store {vector_store_id}...")
        vs_file = self.client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
        )
        print(f"Initial file status: {vs_file.status}")
        
        if not wait_for_completion:
            return {
                "id": vs_file.id,
                "status": vs_file.status,
            }
        
        # Poll for completion
        start_time = time.time()
        while vs_file.status in ["in_progress", "queued"]:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"File indexing timed out after {timeout}s")
            
            print(f"File {file_id} status: {vs_file.status} (elapsed: {elapsed:.1f}s)")
            time.sleep(2)
            vs_file = self.client.vector_stores.files.retrieve(
                vector_store_id=vector_store_id,
                file_id=file_id,
            )
        
        print(f"Final file status: {vs_file.status}, last_error: {vs_file.last_error}")
        
        # Check if file indexing failed
        if vs_file.status in ["failed", "cancelled"]:
            error_msg = vs_file.last_error if vs_file.last_error else "Unknown error"
            raise ValueError(f"File indexing {vs_file.status}: {error_msg}")
        
        return {
            "id": vs_file.id,
            "status": vs_file.status,
            "last_error": vs_file.last_error,
        }
    
    def remove_file_from_vector_store(
        self, 
        vector_store_id: str, 
        file_id: str
    ) -> bool:
        """
        Remove a file from a Vector Store.
        
        Args:
            vector_store_id: Vector Store ID
            file_id: File ID to remove
            
        Returns:
            True if removed successfully
        """
        try:
            self.client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=file_id,
            )
            return True
        except Exception as e:
            print(f"Error removing file from vector store: {e}")
            return False
    
    def get_vector_store_status(self, vector_store_id: str) -> Dict[str, Any]:
        """
        Get Vector Store status and file counts.
        
        Args:
            vector_store_id: Vector Store ID
            
        Returns:
            Status information
        """
        vs = self.client.vector_stores.retrieve(vector_store_id)
        return {
            "id": vs.id,
            "name": vs.name,
            "status": vs.status,
            "file_counts": {
                "in_progress": vs.file_counts.in_progress,
                "completed": vs.file_counts.completed,
                "failed": vs.file_counts.failed,
                "cancelled": vs.file_counts.cancelled,
                "total": vs.file_counts.total,
            },
            "usage_bytes": vs.usage_bytes,
        }
    
    def list_vector_store_files(self, vector_store_id: str) -> List[Dict[str, Any]]:
        """
        List all files in a Vector Store.
        
        Args:
            vector_store_id: Vector Store ID
            
        Returns:
            List of files with their status
        """
        files = self.client.vector_stores.files.list(
            vector_store_id=vector_store_id
        )
        
        return [
            {
                "id": f.id,
                "status": f.status,
                "last_error": f.last_error,
            }
            for f in files.data
        ]
    
    # ==================== Test Generation ====================
    
    def generate_questions(
        self,
        vector_store_id: str,
        question_configs: List[Dict[str, Any]],
        topic_hint: Optional[str] = None,
        target_language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Generate test questions using File Search over the Vector Store.
        
        Uses a two-step approach:
        1. First, retrieve content from documents using file_search
        2. Then, generate questions based on retrieved content
        
        Args:
            vector_store_id: Vector Store ID with indexed materials
            question_configs: List of {type, count} configurations
            topic_hint: Optional topic for context
            target_language: Language code for generated questions (en, ru, ua, pl)
            
        Returns:
            List of generated question dictionaries
        """
        # First, verify the vector store has indexed files
        vs_status = self.get_vector_store_status(vector_store_id)
        print(f"Vector Store status: {vs_status}")
        
        if vs_status["file_counts"]["completed"] == 0:
            raise ValueError(f"Vector Store has no indexed files. Status: {vs_status}")
        
        # List files in vector store for debugging
        vs_files = self.list_vector_store_files(vector_store_id)
        print(f"Files in Vector Store: {vs_files}")
        
        # STEP 1: Retrieve document content using file_search
        print("Step 1: Retrieving document content...")
        document_content = self._retrieve_document_content(vector_store_id)
        print(f"Retrieved content length: {len(document_content)} chars")
        print(f"Content preview: {document_content[:500]}...")
        
        if not document_content or len(document_content) < 100:
            raise ValueError("Could not retrieve document content from Vector Store")
        
        # STEP 2: Generate questions based on retrieved content
        print(f"Step 2: Generating questions from content in {target_language}...")
        questions = self._generate_questions_from_content(
            content=document_content,
            question_configs=question_configs,
            target_language=target_language,
        )
        
        return questions
    
    def _retrieve_document_content(self, vector_store_id: str) -> str:
        """
        Retrieve document content using file_search.
        
        Creates a temporary assistant to search and summarize document content.
        """
        # Create assistant for content retrieval
        assistant = self.client.beta.assistants.create(
            name="Mentis Content Retriever",
            instructions="""You are a document content extractor. Your ONLY job is to:
1. Use file_search to read ALL content from the attached documents
2. Return the COMPLETE text content you find
3. Do NOT summarize or modify - just extract the raw text
4. Include ALL details, facts, procedures, and information from the documents""",
            model=settings.OPENAI_MODEL,
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            },
        )
        
        try:
            # Create thread and request content extraction
            thread = self.client.beta.threads.create()
            
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content="""Search through ALL attached documents and extract their COMPLETE content.
                
I need you to:
1. Use file_search to find ALL text in the documents
2. Return EVERYTHING you find - every paragraph, every instruction, every detail
3. Do NOT skip or summarize anything
4. Include technical terms, commands, URLs, and specific procedures exactly as written

Return the full document content as plain text.""",
            )
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id,
            )
            
            # Wait for completion
            while run.status in ["queued", "in_progress"]:
                time.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id,
                )
            
            # Check run steps for file_search usage
            run_steps = self.client.beta.threads.runs.steps.list(
                thread_id=thread.id,
                run_id=run.id,
            )
            for step in run_steps.data:
                print(f"Content retrieval step: {step.type} - {step.status}")
                if step.type == "tool_calls" and step.step_details:
                    for tool_call in step.step_details.tool_calls:
                        print(f"  Tool used: {tool_call.type}")
                        if hasattr(tool_call, 'file_search') and tool_call.file_search:
                            print(f"  File search results count: {len(tool_call.file_search.results) if tool_call.file_search.results else 0}")
            
            if run.status != "completed":
                raise Exception(f"Content retrieval failed: {run.status}")
            
            # Get the response
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc",
                limit=1,
            )
            
            if not messages.data:
                raise Exception("No response from content retriever")
            
            content = messages.data[0].content[0].text.value
            
            # Cleanup
            self.client.beta.threads.delete(thread.id)
            
            return content
            
        finally:
            # Always cleanup assistant
            self.client.beta.assistants.delete(assistant.id)
    
    def _generate_questions_from_content(
        self,
        content: str,
        question_configs: List[Dict[str, Any]],
        target_language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Generate questions using standard chat completion (no file_search needed).
        
        This is more reliable because we've already extracted the content.
        
        Args:
            content: Document content to generate questions from
            question_configs: List of {type, count} configurations
            target_language: Language code for generated questions (en, ru, ua, pl)
        """
        # Language name mapping for prompts
        language_names = {
            "en": "English",
            "ru": "Russian (Русский)",
            "ua": "Ukrainian (Українська)",
            "pl": "Polish (Polski)",
        }
        lang_name = language_names.get(target_language, "English")
        
        # Question type instructions
        type_instructions = {
            "single-choice": """Single Choice: 4 options, only 1 correct.
Format: {"type": "single-choice", "text": "...", "options": ["A", "B", "C", "D"], "correctAnswer": 0, "points": 1}""",
            
            "multiple-choice": """Multiple Choice: 4 options, 2-3 correct.
Format: {"type": "multiple-choice", "text": "...", "options": ["A", "B", "C", "D"], "correctAnswers": [0, 2], "points": 1}""",
            
            "true-false": """True/False: Statement that is either true or false.
Format: {"type": "true-false", "text": "...", "correctAnswer": true, "points": 1}""",
            
            "short-answer": """Short Answer: Brief text response expected.
Format: {"type": "short-answer", "text": "...", "expectedKeywords": ["keyword1", "keyword2"], "points": 1}""",
            
            "essay": """Essay: Detailed response with evaluation criteria.
Format: {"type": "essay", "text": "...", "rubric": ["criterion1", "criterion2"], "points": 1}""",
            
            "matching": """Matching: Pairs to match together.
Format: {"type": "matching", "text": "Match the following:", "pairs": [{"left": "term", "right": "definition"}, ...], "points": 1}""",
        }
        
        # Build requirements
        requirements = []
        for config in question_configs:
            q_type = config["type"]
            count = config["count"]
            if q_type in type_instructions:
                requirements.append(f"- {count}x {q_type}")
        
        requirements_text = "\n".join(requirements)
        
        # Build type formats
        formats_text = "\n\n".join([
            type_instructions[c["type"]] 
            for c in question_configs 
            if c["type"] in type_instructions
        ])
        
        system_prompt = f"""You are an expert educational assessment creator.
Your task is to generate test questions based STRICTLY on the provided document content.

CRITICAL RULES:
1. ONLY use information from the provided document content
2. Do NOT invent facts, procedures, or details not mentioned in the content
3. Do NOT use general knowledge - stick to what's in the document
4. Questions must test understanding of the SPECIFIC content provided
5. If the document mentions specific tools (like Cockpit), use those - not alternatives (like SSH)
6. Return ONLY valid JSON array - no explanations
7. ALL question text, options, and answers MUST be in {lang_name}
8. Translate any technical content from the document into {lang_name} for the questions"""

        user_prompt = f"""Based on the following DOCUMENT CONTENT, generate test questions.
IMPORTANT: Generate ALL questions and answers in {lang_name} language, even if the source document is in a different language.

=== DOCUMENT CONTENT START ===
{content}
=== DOCUMENT CONTENT END ===

REQUIRED QUESTIONS:
{requirements_text}

FORMAT FOR EACH TYPE:
{formats_text}

Generate questions ONLY about what is mentioned in the document above.
Write ALL question text, options, and answers in {lang_name}.
Return a JSON array of questions. No markdown, no explanations."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=4000,
            )
            
            response_text = response.choices[0].message.content
            print(f"Generation response (first 500 chars): {response_text[:500]}")
            
            return self._parse_questions_response(response_text)
            
        except Exception as e:
            print(f"Error generating questions: {e}")
            raise
    
    def _parse_questions_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse the assistant's response into question objects."""
        import json
        import re
        
        # Try to extract JSON from the response
        # Sometimes the response might have markdown code blocks
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            json_text = json_match.group()
        else:
            json_text = response_text
        
        try:
            questions = json.loads(json_text)
            if isinstance(questions, list):
                return questions
            elif isinstance(questions, dict) and "questions" in questions:
                return questions["questions"]
            else:
                return [questions]
        except json.JSONDecodeError as e:
            print(f"Failed to parse questions JSON: {e}")
            print(f"Response text: {response_text[:500]}")
            return []
    
    def cleanup_assistant(self, assistant_id: str) -> bool:
        """
        Delete an assistant when no longer needed.
        
        Args:
            assistant_id: Assistant ID to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            self.client.beta.assistants.delete(assistant_id)
            # Remove from cache
            self._assistants_cache = {
                k: v for k, v in self._assistants_cache.items() 
                if v != assistant_id
            }
            return True
        except Exception as e:
            print(f"Error deleting assistant {assistant_id}: {e}")
            return False


# Global service instance
_vectorstore_service: Optional[OpenAIVectorStoreService] = None


def get_vectorstore_service() -> OpenAIVectorStoreService:
    """Get or create the Vector Store service instance."""
    global _vectorstore_service
    if _vectorstore_service is None:
        _vectorstore_service = OpenAIVectorStoreService()
    return _vectorstore_service
