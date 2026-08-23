"""Tests for retrieve and key-based CRUD."""

from sqlmodel import Session

from app.services.session_service import create_session, load_session_by_access_key, save_session_state
from tests.conftest import post_form


def test_retrieve_invalid_key(client):
    response = post_form(
        client,
        "/retrieve",
        data={"access_key": "invalid-key"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_retrieve_valid_key(client, db_engine):
    with Session(db_engine) as db:
        record, state = create_session(db)
        state.company.company_name = "Retrieve Co"
        save_session_state(db, record, state)
        key = record.access_key

    response = post_form(
        client,
        "/retrieve",
        data={"access_key": key},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert record.access_key in response.headers["location"]


def test_key_based_intake_update(client, db_engine):
    with Session(db_engine) as db:
        record, _ = create_session(db)
        key = record.access_key

    post_form(
        client,
        f"/k/{key}/intake",
        data={
            "company_name": "Updated Co",
            "industry": "Healthcare",
            "engineering_size": "51-200 engineers",
            "products": "New Product",
            "countries": "United States",
            "risk_tolerance": "Conservative, regulated environment",
        },
    )

    with Session(db_engine) as db:
        _, state = load_session_by_access_key(db, key)
        assert state.company.company_name == "Updated Co"
        assert state.company.products == "New Product"
