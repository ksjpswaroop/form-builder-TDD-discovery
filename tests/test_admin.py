"""Tests for admin panel."""

from tests.conftest import post_form
def test_admin_sessions_requires_login(client):
    response = client.get("/admin/sessions", follow_redirects=False)
    assert response.status_code == 401


def test_admin_login_and_list(admin_client):
    response = admin_client.get("/admin/sessions")
    assert response.status_code == 200
    assert "Discovery Sessions" in response.text or "Admin" in response.text


def test_admin_session_detail(admin_client, db_session, sample_state):
    from app.services.session_service import create_session, save_session_state

    record, state = create_session(db_session)
    save_session_state(db_session, record, sample_state)

    response = admin_client.get(f"/admin/sessions/{record.id}")
    assert response.status_code == 200
    assert record.access_key in response.text
    assert "Acme Corp" in response.text


def test_admin_regenerate_documents(admin_client, db_engine, sample_state):
    from sqlmodel import Session

    from app.services.assessment_plan import generate_plan_yaml
    from app.services.session_service import create_session, load_session_state, save_session_state

    with Session(db_engine) as db:
        record, state = create_session(db)
        state.company = sample_state.company
        state.plan_yaml = generate_plan_yaml(state)
        save_session_state(db, record, state)
        session_id = record.id

    response = post_form(admin_client, f"/admin/sessions/{session_id}/regenerate", follow_redirects=False)
    assert response.status_code == 303

    with Session(db_engine) as db:
        record, _ = load_session_state(db, session_id)
        assert record.pdf_path
        assert record.json_path
