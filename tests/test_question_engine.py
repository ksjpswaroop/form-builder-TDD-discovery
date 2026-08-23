"""Tests for question engine and Ollama integration."""

import json
from unittest.mock import MagicMock

from app.schemas import AnswerRecord, AnswerStatus, SessionState
from app.services.ollama_client import OllamaClient
from app.services.question_engine import (
    _build_fallback_questions,
    _contains_secret_request,
    generate_question_round,
)


def test_secret_request_detection():
    assert _contains_secret_request("Please provide your API key")
    assert _contains_secret_request("What is the database password?")
    assert not _contains_secret_request("How is authentication implemented?")


def test_fallback_questions_without_ollama(sample_state):
    questions = _build_fallback_questions(sample_state, 5)
    assert 1 <= len(questions) <= 5
    assert all(q.reason for q in questions)
    assert all(q.examples or q.question for q in questions)


def test_generate_question_round_offline(sample_state):
    round_data = generate_question_round(sample_state, ollama=None)
    assert len(round_data.questions) > 0
    assert "missing" in round_data.coverage


def test_ollama_mock_generates_questions(sample_state):
    mock_response = {
        "questions": [
            {
                "question_id": "CO-INDUSTRY",
                "section": "company_context",
                "question": "What industry does the company operate in?",
                "reason": "Industry drives compliance expectations.",
                "answer_type": "free_text",
                "options": [],
                "examples": ["Banking", "Healthcare"],
                "required": True,
                "risk_if_unknown": "medium",
                "evidence_requested": [],
            }
        ],
        "coverage": {"completed": 0, "missing": 10, "unknown": 0, "conflicting": 0},
    }

    mock_client = MagicMock()
    mock_client.chat.return_value = json.dumps(mock_response)
    mock_client.parse_json_response.return_value = mock_response

    round_data = generate_question_round(sample_state, ollama=mock_client)
    assert len(round_data.questions) == 1
    assert round_data.questions[0].question_id == "CO-INDUSTRY"
    mock_client.chat.assert_called_once()


def test_secret_questions_filtered(sample_state):
    mock_response = {
        "questions": [
            {
                "question_id": "BAD-001",
                "section": "security",
                "question": "What is your API key for production?",
                "reason": "We need the API key",
                "answer_type": "free_text",
                "examples": [],
            }
        ],
        "coverage": {},
    }
    mock_client = MagicMock()
    mock_client.chat.return_value = json.dumps(mock_response)
    mock_client.parse_json_response.return_value = mock_response

    round_data = generate_question_round(sample_state, ollama=mock_client)
    # Should fall back since secret question filtered and list empty
    assert len(round_data.questions) > 0
    assert all("API key" not in q.question for q in round_data.questions)


def test_already_answered_not_repeated(sample_state):
    sample_state.answers.append(
        AnswerRecord(
            question_id="CO-INDUSTRY",
            status=AnswerStatus.ANSWERED,
            value="Fintech",
        )
    )
    questions = _build_fallback_questions(sample_state, 20)
    ids = [q.question_id for q in questions]
    assert "CO-INDUSTRY" not in ids


def test_ollama_client_parse_json():
    client = OllamaClient()
    parsed = client.parse_json_response('{"questions": []}')
    assert parsed == {"questions": []}
