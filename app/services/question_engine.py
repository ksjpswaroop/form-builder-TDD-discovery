"""Generate adaptive question rounds via Ollama with schema fallback."""

import json
import re
from typing import Any

from app.config import settings
from app.schemas import (
    AnswerRecord,
    AnswerStatus,
    AnswerType,
    GeneratedQuestion,
    QuestionRoundResponse,
    SessionState,
)
from app.services.coverage import compute_coverage, get_missing_field_ids
from app.services.ollama_client import OllamaClient, OllamaError
from app.services.schema_loader import get_field_by_id, load_discovery_schema

SECRET_PATTERNS = [
    r"password",
    r"private\s*key",
    r"api\s*key",
    r"secret\s*token",
    r"credential",
    r"ssh\s*key",
]


def _contains_secret_request(text: str) -> bool:
    lower = text.lower()
    return any(re.search(pat, lower) for pat in SECRET_PATTERNS)


def _answered_ids(state: SessionState) -> set[str]:
    return {
        a.question_id
        for a in state.answers
        if a.status in (AnswerStatus.ANSWERED, AnswerStatus.UNKNOWN, AnswerStatus.NOT_APPLICABLE)
    }


def _build_fallback_questions(
    state: SessionState,
    max_questions: int,
) -> list[GeneratedQuestion]:
    schema = load_discovery_schema()
    missing = get_missing_field_ids(state)
    questions: list[GeneratedQuestion] = []

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def sort_key(item: tuple[str, str | None]) -> tuple[int, str]:
        field = get_field_by_id(schema, item[0])
        prio = priority_order.get(field.priority if field else "medium", 2)
        return (prio, item[0])

    missing.sort(key=sort_key)

    for field_id, applies_to in missing[:max_questions]:
        field = get_field_by_id(schema, field_id)
        if not field:
            continue

        question_text = field.question
        if applies_to:
            question_text = f"[{applies_to}] {question_text}"

        options = list(field.options)
        if field.answer_type in (AnswerType.SINGLE_SELECT, AnswerType.MULTI_SELECT):
            if "Unknown" not in options:
                options.append("Unknown")

        questions.append(
            GeneratedQuestion(
                question_id=field_id,
                section=field.section,
                applies_to=applies_to,
                question=question_text,
                reason=f"This field is required for {field.section.replace('_', ' ')} assessment.",
                answer_type=field.answer_type,
                options=options,
                examples=field.examples,
                required=True,
                risk_if_unknown=field.risk_if_unknown,
                evidence_requested=[],
            )
        )

    return questions


def _build_system_prompt() -> str:
    return (
        "You are a technical debt and source-security discovery interviewer. "
        "Generate structured JSON questions only. Never ask for passwords, API keys, "
        "tokens, private keys, or credentials. Do not repeat already answered fields. "
        "Include reason and 2-3 concrete examples per question. "
        "Return valid JSON matching the schema: "
        '{"questions": [...], "coverage": {"completed": N, "missing": N, "unknown": N, "conflicting": N}}'
    )


def _build_user_prompt(state: SessionState, max_questions: int) -> str:
    schema = load_discovery_schema()
    missing = get_missing_field_ids(state)
    coverage = compute_coverage(state)

    context = {
        "company": state.company.model_dump(),
        "objectives": state.objectives.model_dump(),
        "applications": [a.model_dump() for a in state.applications],
        "answered": [
            {
                "question_id": a.question_id,
                "status": a.status,
                "value": a.value,
                "applies_to": a.applies_to,
            }
            for a in state.answers
        ],
        "missing_field_ids": [{"id": fid, "applies_to": ato} for fid, ato in missing],
        "schema_sections": [s.model_dump() for s in schema.sections],
        "max_questions": max_questions,
        "current_coverage": coverage.model_dump(),
    }

    return (
        f"Generate up to {max_questions} prioritized follow-up questions as JSON. "
        f"Context:\n{json.dumps(context, indent=2)}\n\n"
        "Each question must include: question_id, section, applies_to, question, reason, "
        "answer_type (single_select|multi_select|yes_no|number|free_text), options, "
        "examples (array of strings), required, risk_if_unknown, evidence_requested."
    )


def _validate_and_filter_questions(
    raw_questions: list[dict[str, Any]],
    state: SessionState,
) -> list[GeneratedQuestion]:
    answered = _answered_ids(state)
    valid: list[GeneratedQuestion] = []

    for item in raw_questions:
        question_id = item.get("question_id", "")
        question_text = item.get("question", "")

        if not question_id or question_id in answered:
            continue
        if _contains_secret_request(question_text):
            continue
        if _contains_secret_request(item.get("reason", "")):
            continue

        try:
            answer_type = AnswerType(item.get("answer_type", "free_text"))
        except ValueError:
            answer_type = AnswerType.FREE_TEXT

        valid.append(
            GeneratedQuestion(
                question_id=question_id,
                section=item.get("section", "company_context"),
                applies_to=item.get("applies_to"),
                question=question_text,
                reason=item.get("reason", "Required for assessment configuration."),
                answer_type=answer_type,
                options=item.get("options", []),
                examples=item.get("examples", []),
                required=item.get("required", True),
                risk_if_unknown=item.get("risk_if_unknown", "medium"),
                evidence_requested=item.get("evidence_requested", []),
            )
        )

    return valid


def generate_question_round(
    state: SessionState,
    ollama: OllamaClient | None = None,
    max_questions: int | None = None,
) -> QuestionRoundResponse:
    max_q = max_questions or settings.max_questions_per_round
    coverage = compute_coverage(state)

    if ollama is None:
        questions = _build_fallback_questions(state, max_q)
        return QuestionRoundResponse(
            questions=questions,
            coverage={
                "completed": coverage.completed,
                "missing": coverage.missing,
                "unknown": coverage.unknown,
                "conflicting": coverage.conflicting,
            },
        )

    try:
        content = ollama.chat(_build_system_prompt(), _build_user_prompt(state, max_q))
        data = ollama.parse_json_response(content)
        raw_questions = data.get("questions", [])
        questions = _validate_and_filter_questions(raw_questions, state)

        if not questions:
            questions = _build_fallback_questions(state, max_q)

        cov = data.get("coverage", {})
        return QuestionRoundResponse(
            questions=questions,
            coverage={
                "completed": cov.get("completed", coverage.completed),
                "missing": cov.get("missing", coverage.missing),
                "unknown": cov.get("unknown", coverage.unknown),
                "conflicting": cov.get("conflicting", coverage.conflicting),
            },
        )
    except (OllamaError, Exception):
        questions = _build_fallback_questions(state, max_q)
        return QuestionRoundResponse(
            questions=questions,
            coverage={
                "completed": coverage.completed,
                "missing": coverage.missing,
                "unknown": coverage.unknown,
                "conflicting": coverage.conflicting,
            },
        )
