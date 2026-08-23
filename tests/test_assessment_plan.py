"""Tests for assessment plan generation."""

import yaml

from app.schemas import AnswerRecord, AnswerStatus
from app.services.assessment_plan import build_assessment_plan, generate_plan_yaml


def test_generate_plan_yaml(sample_state):
    yaml_str = generate_plan_yaml(sample_state)
    plan = yaml.safe_load(yaml_str)
    assert plan["version"] == "1.0"
    assert plan["company"]["name"] == "Acme Corp"
    assert len(plan["applications"]) == 1
    assert plan["applications"][0]["application"] == "customer-portal"


def test_plan_includes_unknown_register(sample_state):
    sample_state.answers.append(
        AnswerRecord(
            question_id="SEC-SECRET-MGMT",
            status=AnswerStatus.UNKNOWN,
            notes="Team does not know vault setup",
        )
    )
    plan = build_assessment_plan(sample_state)
    assert len(plan["missing_information_register"]) == 1
    assert plan["missing_information_register"][0]["question_id"] == "SEC-SECRET-MGMT"


def test_plan_includes_scans_for_internet_exposure(sample_state):
    sample_state.answers.append(
        AnswerRecord(
            question_id="APP-EXPOSURE",
            status=AnswerStatus.ANSWERED,
            value="Internet-facing public API",
            applies_to="customer-portal",
        )
    )
    plan = build_assessment_plan(sample_state)
    scans = plan["applications"][0]["required_scans"]
    assert "sast" in scans
    assert "container_scan" in scans


def test_plan_release_gates_from_objectives(sample_state):
    plan = build_assessment_plan(sample_state)
    gates = plan["applications"][0]["release_gates"]
    assert gates["critical_security_findings"] == 0
    assert gates["high_security_findings"] == 0
