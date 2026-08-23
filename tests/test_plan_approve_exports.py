"""Tests for plan approval and document export."""

from sqlmodel import Session

from app.config import DATA_DIR
from app.services.session_service import create_session, load_session_by_access_key, save_session_state
from app.schemas import SessionState, CompanyIntake
from tests.conftest import post_form


def _full_session(client, access_key: str):
    post_form(
        client,
        f"/k/{access_key}/intake",
        data={
            "company_name": "Export Co",
            "industry": "SaaS / technology",
            "engineering_size": "11-50 engineers",
            "products": "Analytics",
            "countries": "United States",
            "compliance": "SOC 2",
            "tooling": "Semgrep",
            "risk_tolerance": "Balanced risk and velocity",
        },
    )
    post_form(
        client,
        f"/k/{access_key}/objectives",
        data={
            "primary_goal": "Prepare for audit",
            "report_audiences": ["Security team"],
            "release_blockers": ["Critical security"],
            "assessment_frequency": "Weekly",
            "remediation_capacity": "1 engineer part-time",
        },
    )
    post_form(
        client,
        f"/k/{access_key}/applications",
        data={
            "name": "portal",
            "description": "Main portal",
            "business_owner": "Alice",
            "technical_owner": "Bob",
            "repositories": "github.com/export/portal",
            "production_status": "Production",
            "exposure": "Internet-facing public API or web app",
            "data_classes": "PII",
            "criticality": "Critical — revenue or safety impact",
            "user_count": "1000 - 10,000",
        },
    )
    post_form(client, f"/k/{access_key}/applications/done")
    post_form(client, f"/k/{access_key}/interview/generate-plan")


def test_approve_generates_documents(client, db_engine):
    response = client.get("/", follow_redirects=False)
    access_key = response.headers["location"].split("/k/")[1].split("/")[0]
    _full_session(client, access_key)

    for format_name in ("pdf", "xlsx", "json"):
        response = client.get(f"/k/{access_key}/documents/{format_name}")
        assert response.status_code == 404

    response = post_form(client, f"/k/{access_key}/plan/approve", follow_redirects=False)
    assert response.status_code == 303
    assert "approved=1" in response.headers["location"]

    with Session(db_engine) as db:
        record, state = load_session_by_access_key(db, access_key)
        assert record.plan_approved
        assert state.plan_approved
        assert record.approved_at
        assert record.documents_generated_at
        assert record.pdf_path
        assert record.excel_path
        assert record.json_path

        for rel_path in (record.pdf_path, record.excel_path, record.json_path):
            path = DATA_DIR / rel_path
            assert path.is_file()
            assert path.stat().st_size > 0

    for format_name in ("pdf", "xlsx", "json"):
        response = client.get(f"/k/{access_key}/documents/{format_name}")
        assert response.status_code == 200
        assert response.content

    retrieve = post_form(
        client,
        "/retrieve",
        data={"access_key": access_key},
        follow_redirects=False,
    )
    assert retrieve.status_code == 303
    assert f"/k/{access_key}/intake" in retrieve.headers["location"]

    with Session(db_engine) as db:
        record, state = load_session_by_access_key(db, access_key)
        assert record.current_step == "complete"
        assert state.company.company_name == "Export Co"
        assert state.objectives.primary_goal == "Prepare for audit"
        assert record.pdf_path

    response = client.get(f"/k/{access_key}/documents/pdf")
    assert response.status_code == 200
    assert response.content
