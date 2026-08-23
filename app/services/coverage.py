"""Deterministic coverage computation from schema and answers."""

from app.config import settings
from app.schemas import AnswerRecord, AnswerStatus, CoverageSummary, SessionState
from app.services.schema_loader import load_discovery_schema


def _field_keys_for_session(state: SessionState) -> list[tuple[str, str | None]]:
    """Return (field_id, applies_to) tuples representing required coverage units."""
    schema = load_discovery_schema()
    keys: list[tuple[str, str | None]] = []

    for field in schema.fields:
        if field.applies_to == "application":
            for app in state.applications:
                keys.append((field.id, app.name))
        else:
            keys.append((field.id, None))

    return keys


def _answer_key(question_id: str, applies_to: str | None) -> str:
    suffix = applies_to or ""
    return f"{question_id}::{suffix}"


def compute_coverage(state: SessionState) -> CoverageSummary:
    schema = load_discovery_schema()
    required_keys = _field_keys_for_session(state)

    answer_map: dict[str, AnswerRecord] = {}
    for answer in state.answers:
        answer_map[_answer_key(answer.question_id, answer.applies_to)] = answer

    completed = 0
    missing = 0
    unknown = 0
    not_applicable = 0
    conflicting = 0

    for field_id, applies_to in required_keys:
        key = _answer_key(field_id, applies_to)
        answer = answer_map.get(key)

        if answer is None:
            missing += 1
            continue

        if answer.status == AnswerStatus.ANSWERED:
            completed += 1
        elif answer.status == AnswerStatus.UNKNOWN:
            unknown += 1
        elif answer.status == AnswerStatus.NOT_APPLICABLE:
            not_applicable += 1
        elif answer.status == AnswerStatus.CONFLICTING:
            conflicting += 1
        else:
            missing += 1

    total = len(required_keys)
    actionable = total - not_applicable
    resolved = completed + unknown + conflicting
    percent = (resolved / actionable * 100) if actionable > 0 else 0.0
    is_sufficient = actionable > 0 and (resolved / actionable) >= settings.coverage_threshold

    return CoverageSummary(
        completed=completed,
        missing=missing,
        unknown=unknown,
        not_applicable=not_applicable,
        conflicting=conflicting,
        total=total,
        percent_complete=round(percent, 1),
        is_sufficient=is_sufficient,
    )


def get_missing_field_ids(state: SessionState) -> list[tuple[str, str | None]]:
    schema = load_discovery_schema()
    required_keys = _field_keys_for_session(state)

    answer_map: dict[str, AnswerRecord] = {}
    for answer in state.answers:
        answer_map[_answer_key(answer.question_id, answer.applies_to)] = answer

    missing: list[tuple[str, str | None]] = []
    for field_id, applies_to in required_keys:
        key = _answer_key(field_id, applies_to)
        answer = answer_map.get(key)
        if answer is None:
            missing.append((field_id, applies_to))
        elif answer.status == AnswerStatus.MISSING:
            missing.append((field_id, applies_to))

    return missing


def detect_conflicts(state: SessionState) -> list[str]:
    """Detect simple contradictions in answers."""
    conflicts: list[str] = []
    answer_by_id: dict[str, list[AnswerRecord]] = {}
    for answer in state.answers:
        answer_by_id.setdefault(answer.question_id, []).append(answer)

    for question_id, records in answer_by_id.items():
        if len(records) < 2:
            continue
        values = {str(r.value) for r in records if r.status == AnswerStatus.ANSWERED}
        if len(values) > 1:
            conflicts.append(question_id)

    return conflicts
