"""Generate assessment plan YAML from collected answers."""

import yaml

from app.schemas import AnswerRecord, AnswerStatus, SessionState
from app.services.coverage import compute_coverage


def _answers_by_id(state: SessionState) -> dict[str, list[AnswerRecord]]:
    result: dict[str, list[AnswerRecord]] = {}
    for answer in state.answers:
        result.setdefault(answer.question_id, []).append(answer)
    return result


def _get_value(state: SessionState, field_id: str, applies_to: str | None = None) -> str | None:
    for answer in state.answers:
        if answer.question_id == field_id and answer.applies_to == applies_to:
            if answer.status == AnswerStatus.ANSWERED:
                return str(answer.value)
    return None


def _infer_scans(state: SessionState) -> list[str]:
    scans = ["sast", "dependency_scan", "secret_scan"]
    internet_exposed = False

    for answer in state.answers:
        if answer.question_id == "APP-EXPOSURE" and answer.status == AnswerStatus.ANSWERED:
            if "internet" in str(answer.value).lower():
                internet_exposed = True

    for app in state.applications:
        if app.exposure and "internet" in app.exposure.lower():
            internet_exposed = True

    if internet_exposed:
        scans.extend(["container_scan", "iac_scan"])

    compliance = state.company.compliance.lower()
    if any(x in compliance for x in ["pci", "hipaa", "soc"]):
        if "dast" not in scans:
            scans.append("dast")
    return scans


def _infer_release_gates(state: SessionState) -> dict[str, int | str]:
    blockers = state.objectives.release_blockers
    gates: dict[str, int | str] = {
        "critical_security_findings": 0 if "Critical security" in blockers else 5,
        "high_security_findings": 0 if "High security" in blockers else 10,
        "maximum_new_critical_debt": 0,
        "minimum_critical_path_coverage": 85,
    }
    return gates


def _infer_sla(state: SessionState) -> dict[str, str]:
    risk = state.company.risk_tolerance.lower()
    if "conservative" in risk or "zero" in risk:
        return {"critical": "24_hours", "high": "7_days", "medium": "30_days"}
    if "fast" in risk:
        return {"critical": "7_days", "high": "30_days", "medium": "90_days"}
    return {"critical": "48_hours", "high": "14_days", "medium": "60_days"}


def build_assessment_plan(state: SessionState) -> dict:
    coverage = compute_coverage(state)
    answers_map = _answers_by_id(state)

    missing_register = [
        {
            "question_id": a.question_id,
            "applies_to": a.applies_to,
            "risk_if_unknown": "high",
            "notes": a.notes,
        }
        for a in state.answers
        if a.status == AnswerStatus.UNKNOWN
    ]

    evidence_checklist: list[str] = []
    for answer in state.answers:
        if answer.notes and "http" in answer.notes:
            evidence_checklist.append(answer.notes)

    applications_plan = []
    for app in state.applications:
        app_plan = {
            "application": app.name,
            "criticality": _get_value(state, "APP-CRITICALITY", app.name) or app.criticality,
            "exposure": _get_value(state, "APP-EXPOSURE", app.name) or app.exposure,
            "data_classes": _get_value(state, "APP-DATA-CLASSES", app.name) or app.data_classes,
            "repositories": _get_value(state, "APP-REPOS", app.name) or app.repositories,
            "required_scans": _infer_scans(state),
            "release_gates": _infer_release_gates(state),
            "remediation_sla": _infer_sla(state),
        }
        applications_plan.append(app_plan)

    plan = {
        "version": "1.0",
        "company": {
            "name": state.company.company_name,
            "industry": state.company.industry,
            "compliance": state.company.compliance,
            "risk_tolerance": state.company.risk_tolerance,
        },
        "objectives": {
            "primary_goal": state.objectives.primary_goal,
            "report_audiences": state.objectives.report_audiences,
            "release_blockers": state.objectives.release_blockers,
        },
        "applications": applications_plan,
        "exceptions": {
            "approval_roles": ["application_owner", "security_owner"],
            "maximum_duration_days": 90,
            "compensating_control_required": True,
        },
        "coverage_summary": {
            "completed": coverage.completed,
            "missing": coverage.missing,
            "unknown": coverage.unknown,
            "not_applicable": coverage.not_applicable,
            "conflicting": coverage.conflicting,
            "percent_complete": coverage.percent_complete,
        },
        "missing_information_register": missing_register,
        "evidence_checklist": evidence_checklist,
        "answer_count": len(state.answers),
        "fields_with_answers": list(answers_map.keys()),
    }

    return plan


def generate_plan_yaml(state: SessionState) -> str:
    plan = build_assessment_plan(state)
    return yaml.dump(plan, default_flow_style=False, sort_keys=False, allow_unicode=True)
