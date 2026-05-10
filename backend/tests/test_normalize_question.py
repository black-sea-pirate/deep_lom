"""
Unit tests for OpenAI vector store service helpers.

Focuses on _normalize_question and _shuffle_options — pure functions that
had a real production bug (correctAnswer=0 treated as falsy).

No external dependencies required (no DB, no Redis, no OpenAI).
"""

import pytest
from app.services.openai_vectorstore import OpenAIVectorStoreService


# Build a service instance without calling OpenAI
@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setattr(
        "app.services.openai_vectorstore.OpenAI",
        lambda **_: None,  # don't actually connect
    )
    return OpenAIVectorStoreService()


# ─── _normalize_question ───────────────────────────────────────────────────────

class TestNormalizeQuestion:

    # ── single-choice ──────────────────────────────────────────────────────────

    def test_single_choice_correct_answer_is_integer(self, svc):
        q = svc._normalize_question({
            "type": "single-choice",
            "text": "Q?",
            "options": ["A", "B", "C", "D"],
            "correctAnswer": 2,
        })
        assert q["correctAnswer"] == 2
        assert isinstance(q["correctAnswer"], int)

    def test_single_choice_zero_is_preserved(self, svc):
        """
        The falsy-value bug: correctAnswer=0 must NOT be replaced by None.
        This was a real production bug where `or` operator was used.
        """
        q = svc._normalize_question({
            "type": "single-choice",
            "text": "Q?",
            "options": ["Correct", "B", "C", "D"],
            "correctAnswer": 0,
        })
        assert q["correctAnswer"] == 0

    def test_single_choice_string_digit_is_converted(self, svc):
        q = svc._normalize_question({
            "type": "single-choice",
            "text": "Q?",
            "options": ["A", "B", "C", "D"],
            "correctAnswer": "2",
        })
        assert q["correctAnswer"] == 2

    def test_single_choice_string_option_text_finds_index(self, svc):
        """AI sometimes returns the option text instead of its index."""
        q = svc._normalize_question({
            "type": "single-choice",
            "text": "Q?",
            "options": ["Alpha", "Beta", "Gamma"],
            "correctAnswer": "Beta",
        })
        assert q["correctAnswer"] == 1

    def test_single_choice_out_of_bounds_falls_back_to_zero(self, svc):
        q = svc._normalize_question({
            "type": "single-choice",
            "text": "Q?",
            "options": ["A", "B"],
            "correctAnswer": 99,
        })
        assert q["correctAnswer"] == 0

    def test_single_choice_uses_correctAnswers_list_as_fallback(self, svc):
        """AI sometimes puts a list under the wrong key for single-choice."""
        q = svc._normalize_question({
            "type": "single-choice",
            "text": "Q?",
            "options": ["A", "B", "C"],
            "correctAnswers": [1],
        })
        assert q["correctAnswer"] == 1

    # ── multiple-choice ────────────────────────────────────────────────────────

    def test_multiple_choice_list_of_ints(self, svc):
        q = svc._normalize_question({
            "type": "multiple-choice",
            "text": "Q?",
            "options": ["A", "B", "C", "D"],
            "correctAnswers": [0, 2],
        })
        assert q["correctAnswers"] == [0, 2]

    def test_multiple_choice_single_int_wrapped_in_list(self, svc):
        q = svc._normalize_question({
            "type": "multiple-choice",
            "text": "Q?",
            "options": ["A", "B", "C"],
            "correctAnswer": 1,
        })
        assert q["correctAnswers"] == [1]

    def test_multiple_choice_zero_in_list_preserved(self, svc):
        """Same falsy-value concern for multiple-choice."""
        q = svc._normalize_question({
            "type": "multiple-choice",
            "text": "Q?",
            "options": ["A", "B", "C"],
            "correctAnswers": [0, 2],
        })
        assert 0 in q["correctAnswers"]

    # ── true-false ─────────────────────────────────────────────────────────────

    def test_true_false_bool_true(self, svc):
        q = svc._normalize_question({"type": "true-false", "text": "Q?", "correctAnswer": True})
        assert q["correctAnswer"] is True

    def test_true_false_bool_false(self, svc):
        q = svc._normalize_question({"type": "true-false", "text": "Q?", "correctAnswer": False})
        assert q["correctAnswer"] is False

    def test_true_false_string_true_converted(self, svc):
        for val in ("true", "True", "yes", "1", "так", "да"):
            q = svc._normalize_question({"type": "true-false", "text": "Q?", "correctAnswer": val})
            assert q["correctAnswer"] is True, f"Expected True for '{val}'"

    def test_true_false_string_false_converted(self, svc):
        q = svc._normalize_question({"type": "true-false", "text": "Q?", "correctAnswer": "false"})
        assert q["correctAnswer"] is False

    def test_true_false_int_zero_is_false(self, svc):
        q = svc._normalize_question({"type": "true-false", "text": "Q?", "correctAnswer": 0})
        assert q["correctAnswer"] is False

    def test_true_false_int_one_is_true(self, svc):
        q = svc._normalize_question({"type": "true-false", "text": "Q?", "correctAnswer": 1})
        assert q["correctAnswer"] is True


# ─── _shuffle_options ──────────────────────────────────────────────────────────

class TestShuffleOptions:

    def test_single_choice_correct_answer_tracks_shuffle(self, svc):
        """
        After shuffling, correctAnswer index must still point to the same
        option TEXT, regardless of where it ended up after the shuffle.
        """
        original_options = ["Alpha", "Beta", "Gamma", "Delta"]
        correct_idx = 2  # "Gamma" is correct

        q = svc._shuffle_options({
            "type": "single-choice",
            "options": list(original_options),
            "correctAnswer": correct_idx,
        })

        correct_text = original_options[correct_idx]  # "Gamma"
        assert q["options"][q["correctAnswer"]] == correct_text

    def test_single_choice_all_options_preserved(self, svc):
        options = ["A", "B", "C", "D"]
        q = svc._shuffle_options({
            "type": "single-choice",
            "options": list(options),
            "correctAnswer": 1,
        })
        assert sorted(q["options"]) == sorted(options)

    def test_multiple_choice_correct_indices_track_shuffle(self, svc):
        options = ["X", "Y", "Z", "W"]
        correct_texts = {"X", "Z"}  # indices 0 and 2

        q = svc._shuffle_options({
            "type": "multiple-choice",
            "options": list(options),
            "correctAnswers": [0, 2],
        })

        answered_texts = {q["options"][i] for i in q["correctAnswers"]}
        assert answered_texts == correct_texts

    def test_multiple_choice_all_options_preserved(self, svc):
        options = ["A", "B", "C", "D"]
        q = svc._shuffle_options({
            "type": "multiple-choice",
            "options": list(options),
            "correctAnswers": [1, 3],
        })
        assert sorted(q["options"]) == sorted(options)

    def test_non_choice_types_are_unchanged(self, svc):
        """essay, short-answer, matching — no shuffle should occur."""
        for q_type in ("essay", "short-answer", "true-false", "matching"):
            original = {"type": q_type, "text": "Q?", "correctAnswer": True}
            result = svc._shuffle_options(dict(original))
            # Options key absent — nothing touched
            assert result.get("options") == original.get("options")
