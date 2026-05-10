"""
Question Regeneration Service

Regenerates a single existing question using the project's Vector Store (RAG).
Uses the same two-step approach as primary generation:
  Step 1 — retrieve relevant content via file_search (targeted or topic-avoiding)
  Step 2 — generate one question of the same type via chat completion

Standalone module — does not modify openai_vectorstore.py.
"""
import json
import re
import time
import random
from typing import Optional, Dict, Any

from openai import OpenAI

from app.core.config import settings


PRESET_INSTRUCTIONS: Dict[str, str] = {
    "rephrase": "Rephrase the question using different wording while testing the same concept from the document.",
    "harder": "Create a more challenging question on the same topic, requiring deeper understanding or analysis.",
    "easier": "Create a simpler, more straightforward question on the same topic.",
    "different_topic": "Generate a question from a COMPLETELY DIFFERENT section of the document, avoiding the current topic entirely.",
}

QUESTION_TYPE_FORMATS: Dict[str, str] = {
    "single-choice": '{"type": "single-choice", "text": "...", "options": ["A", "B", "C", "D"], "correctAnswer": 0, "points": 1}',
    "multiple-choice": '{"type": "multiple-choice", "text": "...", "options": ["A", "B", "C", "D"], "correctAnswers": [0, 2], "points": 1}',
    "true-false": '{"type": "true-false", "text": "...", "correctAnswer": true, "points": 1}',
    "short-answer": '{"type": "short-answer", "text": "...", "expectedKeywords": ["keyword1", "keyword2"], "points": 1}',
    "essay": '{"type": "essay", "text": "...", "rubric": ["criterion1", "criterion2"], "points": 1}',
    "matching": '{"type": "matching", "text": "Match the following:", "pairs": [{"left": "term", "right": "definition"}], "points": 1}',
}

LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "ru": "Russian (Русский)",
    "ua": "Ukrainian (Українська)",
    "pl": "Polish (Polski)",
}


def regenerate_question(
    vector_store_id: str,
    existing_question: Dict[str, Any],
    preset: Optional[str] = None,
    custom_instruction: Optional[str] = None,
    target_language: str = "en",
) -> Dict[str, Any]:
    """
    Regenerate a single question using the project's Vector Store.

    Returns the new question dict (preview only — not saved to DB).
    Caller is responsible for saving via PUT /questions/{id}.
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    question_type = existing_question.get("questionType", "single-choice")
    existing_text = existing_question.get("text", "")
    points = existing_question.get("points", 1)

    avoid_topic = preset == "different_topic"
    instruction = _resolve_instruction(preset, custom_instruction)

    document_content = _retrieve_content(
        client=client,
        vector_store_id=vector_store_id,
        existing_question_text=existing_text,
        avoid_topic=avoid_topic,
    )

    if not document_content or len(document_content) < 50:
        raise ValueError("Could not retrieve content from Vector Store")

    return _generate_one_question(
        client=client,
        content=document_content,
        question_type=question_type,
        instruction=instruction,
        existing_question_text=existing_text,
        target_language=target_language,
        points=points,
    )


# ==================== Private helpers ====================


def _resolve_instruction(preset: Optional[str], custom_instruction: Optional[str]) -> str:
    if custom_instruction and custom_instruction.strip():
        return custom_instruction.strip()
    return PRESET_INSTRUCTIONS.get(preset or "rephrase", PRESET_INSTRUCTIONS["rephrase"])


def _retrieve_content(
    client: OpenAI,
    vector_store_id: str,
    existing_question_text: str,
    avoid_topic: bool,
) -> str:
    """Step 1: Retrieve relevant content from Vector Store using file_search."""
    if avoid_topic:
        search_message = (
            f'Search for content from a DIFFERENT section of the document.\n'
            f'CRITICAL: Do NOT return content related to: "{existing_question_text[:150]}"\n'
            f'Find information about OTHER subjects or concepts and return that text.'
        )
    else:
        search_message = (
            f'Find and extract content from the document related to this topic: '
            f'"{existing_question_text[:150]}"\n'
            f'Return detailed information: facts, definitions, explanations.'
        )

    assistant = client.beta.assistants.create(
        name="Mentis Question Regenerator",
        instructions=(
            "You are a document content extractor. "
            "Use file_search to find and return relevant content from the attached documents. "
            "Return the raw text content you find without summarising."
        ),
        model=settings.OPENAI_MODEL,
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
    )

    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=search_message,
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        while run.status in ["queued", "in_progress"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
            )

        if run.status != "completed":
            raise ValueError(f"Content retrieval failed with status: {run.status}")

        messages = client.beta.threads.messages.list(
            thread_id=thread.id,
            order="desc",
            limit=1,
        )

        if not messages.data:
            raise ValueError("No response received from content retriever")

        content = messages.data[0].content[0].text.value
        client.beta.threads.delete(thread.id)
        return content

    finally:
        client.beta.assistants.delete(assistant.id)


def _generate_one_question(
    client: OpenAI,
    content: str,
    question_type: str,
    instruction: str,
    existing_question_text: str,
    target_language: str,
    points: int,
) -> Dict[str, Any]:
    """Step 2: Generate a single question via chat completion."""
    lang_name = LANGUAGE_NAMES.get(target_language, "English")
    format_example = QUESTION_TYPE_FORMATS.get(question_type, QUESTION_TYPE_FORMATS["single-choice"])

    system_prompt = (
        f'You are an expert educational assessment creator.\n'
        f'Generate exactly ONE test question of type "{question_type}" from the provided document content.\n\n'
        f'RULES:\n'
        f'1. Use ONLY information from the provided document content\n'
        f'2. Keep the question type as: {question_type}\n'
        f'3. ALL text must be in {lang_name}\n'
        f'4. Do NOT generate a question similar to: "{existing_question_text[:150]}"\n'
        f'5. Return ONLY a single valid JSON object — no array, no markdown\n'
        f'6. The "points" field must be {points}\n'
        f'7. RANDOMIZE the position of the correct answer (not always index 0)\n\n'
        f'Teacher instruction: {instruction}'
    )

    user_prompt = (
        f'=== DOCUMENT CONTENT ===\n{content}\n=== END ===\n\n'
        f'Generate ONE {question_type} question using this exact format:\n'
        f'{format_example}\n\n'
        f'Return only the JSON object.'
    )

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=1000,
    )

    response_text = response.choices[0].message.content
    return _parse_single_question(response_text, question_type, points)


def _parse_single_question(response_text: str, question_type: str, points: int) -> Dict[str, Any]:
    """Parse AI response into a normalised question dict ready for the frontend."""
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if not json_match:
        raise ValueError(f"No JSON found in response: {response_text[:200]}")

    question = json.loads(json_match.group())
    question["type"] = question_type
    question["points"] = question.get("points", points)

    question = _normalize_question(question)
    question = _shuffle_options(question)

    return {
        "questionType": question.get("type", question_type),
        "text": question.get("text", ""),
        "points": question.get("points", points),
        "options": question.get("options"),
        "correctAnswer": question.get("correctAnswer"),
        "expectedKeywords": question.get("expectedKeywords"),
        "pairs": question.get("pairs"),
    }


def _normalize_question(q: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure correctAnswer is in the correct format for each question type."""
    q_type = q.get("type", "")

    if q_type == "single-choice":
        correct = q.get("correctAnswer")
        if correct is None:
            correct = q.get("correctAnswers")
            if isinstance(correct, list) and correct:
                correct = correct[0]
        if isinstance(correct, str):
            if correct.isdigit():
                correct = int(correct)
            elif q.get("options"):
                for i, opt in enumerate(q["options"]):
                    if opt.lower().strip() == correct.lower().strip():
                        correct = i
                        break
        q["correctAnswer"] = correct if isinstance(correct, int) else 0

    elif q_type == "multiple-choice":
        correct = q.get("correctAnswers") or q.get("correctAnswer")
        if isinstance(correct, int):
            correct = [correct]
        elif isinstance(correct, list):
            correct = [int(c) for c in correct if isinstance(c, (int, str)) and str(c).isdigit()]
        else:
            correct = [0]
        q["correctAnswers"] = correct
        q["correctAnswer"] = correct

    elif q_type == "true-false":
        correct = q.get("correctAnswer")
        if isinstance(correct, str):
            correct = correct.lower() in ("true", "yes", "1", "так", "да", "правда")
        elif isinstance(correct, int):
            correct = bool(correct)
        elif not isinstance(correct, bool):
            correct = True
        q["correctAnswer"] = correct

    return q


def _shuffle_options(q: Dict[str, Any]) -> Dict[str, Any]:
    """Shuffle options so the correct answer isn't always at index 0."""
    q_type = q.get("type", "")
    options = q.get("options", [])

    if q_type == "single-choice" and len(options) > 1:
        correct_idx = q.get("correctAnswer", 0)
        if isinstance(correct_idx, int) and 0 <= correct_idx < len(options):
            indexed = list(enumerate(options))
            random.shuffle(indexed)
            new_correct = None
            new_options = []
            for new_idx, (old_idx, text) in enumerate(indexed):
                new_options.append(text)
                if old_idx == correct_idx:
                    new_correct = new_idx
            q["options"] = new_options
            q["correctAnswer"] = new_correct if new_correct is not None else 0

    elif q_type == "multiple-choice" and len(options) > 1:
        correct_indices = q.get("correctAnswers", [])
        if not isinstance(correct_indices, list):
            correct_indices = [correct_indices] if correct_indices is not None else []
        indexed = list(enumerate(options))
        random.shuffle(indexed)
        old_to_new = {old: new for new, (old, _) in enumerate(indexed)}
        q["options"] = [text for _, text in indexed]
        new_correct = [old_to_new[i] for i in correct_indices if i in old_to_new]
        q["correctAnswers"] = new_correct
        q["correctAnswer"] = new_correct

    return q
