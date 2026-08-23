"""API and HTML integration tests."""

from sqlmodel import Session

from app.services.session_service import load_session_by_access_key
from tests.conftest import post_form


def test_home_redirects_to_key_intake(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert "/k/" in response.headers["location"]
    assert "/intake" in response.headers["location"]


def test_intake_flow(client):
    access_key = _start_session(client)
    response = post_form(
        client,
        f"/k/{access_key}/intake",
        data={
            "company_name": "Test Co",
            "industry": "SaaS / technology",
            "engineering_size": "11-50 engineers",
            "products": "Analytics platform",
            "countries": "United States",
            "compliance": "SOC 2",
            "tooling": "GitHub Actions",
            "risk_tolerance": "Balanced risk and velocity",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "objectives" in response.headers["location"]


def test_interview_page_has_reason_and_examples(client):
    access_key = _full_session_to_interview(client)
    response = client.get(f"/k/{access_key}/interview")
    html = response.text
    assert "Why we ask" in html
    assert "Unknown" in html
    assert "Additional notes" in html


def test_plan_page_has_document_format(client):
    access_key = _full_session_to_interview(client)
    post_form(client, f"/k/{access_key}/interview/generate-plan")
    response = client.get(f"/k/{access_key}/plan")
    assert "Assessment plan" in response.text
    assert "plan-report" in response.text
    assert "Raw YAML" in response.text


def test_interview_submit_persists_answers(client, db_engine):
    access_key = _full_session_to_interview(client)
    post_form(
        client,
        f"/k/{access_key}/interview",
        data={
            "q__CO-INDUSTRY::": "Fintech",
            "status__CO-INDUSTRY::": "answered",
            "notes__CO-INDUSTRY::": "Primary vertical",
        },
        follow_redirects=False,
    )
    with Session(db_engine) as db:
        _, state = load_session_by_access_key(db, access_key)
        assert any(a.question_id == "CO-INDUSTRY" for a in state.answers)


def _start_session(client) -> str:
    response = client.get("/", follow_redirects=False)
    return response.headers["location"].split("/k/")[1].split("/")[0]


def _full_session_to_interview(client) -> str:
    access_key = _start_session(client)
    post_form(
        client,
        f"/k/{access_key}/intake",
        data={
            "company_name": "Acme",
            "industry": "Financial services / banking",
            "engineering_size": "51-200 engineers",
            "products": "Payments",
            "countries": "United States",
            "compliance": "PCI DSS",
            "tooling": "Semgrep",
            "risk_tolerance": "Conservative, regulated environment",
        },
    )
    post_form(
        client,
        f"/k/{access_key}/objectives",
        data={
            "primary_goal": "Prepare for audit",
            "report_audiences": ["Security team"],
            "release_blockers": ["Critical security", "High security"],
            "assessment_frequency": "Monthly",
            "remediation_capacity": "2 engineers part-time",
        },
    )
    post_form(
        client,
        f"/k/{access_key}/applications",
        data={
            "name": "portal",
            "description": "Customer portal",
            "business_owner": "Alice",
            "technical_owner": "Bob",
            "repositories": "github.com/acme/portal",
            "production_status": "Production",
            "exposure": "Internet-facing public API or web app",
            "data_classes": "PII",
            "criticality": "Critical — revenue or safety impact",
            "user_count": "5000",
        },
    )
    post_form(client, f"/k/{access_key}/applications/done")
    return access_key
