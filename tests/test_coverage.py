"""Tests for coverage engine."""

from app.schemas import AnswerRecord, AnswerStatus, ApplicationRecord, SessionState
from app.services.coverage import compute_coverage, get_missing_field_ids


def test_coverage_all_missing(sample_state):
    coverage = compute_coverage(sample_state)
    assert coverage.missing > 0
    assert coverage.completed == 0
    assert coverage.percent_complete == 0.0
    assert not coverage.is_sufficient


def test_coverage_answered_counts(sample_state):
    sample_state.answers.append(
        AnswerRecord(
            question_id="CO-INDUSTRY",
            status=AnswerStatus.ANSWERED,
            value="Fintech",
        )
    )
    coverage = compute_coverage(sample_state)
    assert coverage.completed == 1
    assert coverage.missing == coverage.total - 1


def test_coverage_unknown_not_complete(sample_state):
    sample_state.answers.append(
        AnswerRecord(
            question_id="CO-INDUSTRY",
            status=AnswerStatus.UNKNOWN,
        )
    )
    coverage = compute_coverage(sample_state)
    assert coverage.unknown == 1
    assert coverage.completed == 0


def test_coverage_not_applicable_excluded_from_missing(sample_state):
    sample_state.answers.append(
        AnswerRecord(
            question_id="CO-INDUSTRY",
            status=AnswerStatus.NOT_APPLICABLE,
        )
    )
    coverage = compute_coverage(sample_state)
    assert coverage.not_applicable == 1
    assert coverage.missing == coverage.total - 1


def test_missing_field_ids(sample_state):
    missing = get_missing_field_ids(sample_state)
    assert len(missing) > 0
    assert all(isinstance(m[0], str) for m in missing)


def test_application_fields_expand_per_app(sample_state):
    sample_state.applications.append(
        ApplicationRecord(name="billing-api", criticality="High")
    )
    missing = get_missing_field_ids(sample_state)
    app_criticality = [m for m in missing if m[0] == "APP-CRITICALITY"]
    assert len(app_criticality) == 2
