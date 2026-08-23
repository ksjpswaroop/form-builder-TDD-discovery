"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings
from app.database import migrate_db
from app.main import app, get_db
from app.schemas import (
    ApplicationRecord,
    AssessmentObjectives,
    CompanyIntake,
    SessionState,
)
from app.services.session_service import create_session, save_session_state


def bootstrap_csrf(client: TestClient) -> str:
    """Fetch a page that sets the CSRF cookie (reuse existing cookie if present)."""
    token = client.cookies.get("csrf_token")
    if token:
        return token
    client.get("/retrieve")
    return client.cookies.get("csrf_token")


def post_form(client: TestClient, url: str, data: dict | None = None, **kwargs):
    """POST with CSRF token from cookie."""
    payload = dict(data or {})
    if "csrf_token" not in payload:
        payload["csrf_token"] = bootstrap_csrf(client)
    return client.post(url, data=payload, **kwargs)


@pytest.fixture()
def db_engine():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    migrate_db(engine)
    yield engine
    os.unlink(path)


@pytest.fixture()
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture()
def documents_dir(tmp_path):
    docs = tmp_path / "documents"
    docs.mkdir()
    return docs


@pytest.fixture()
def client(db_engine):
    def override_get_db():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        bootstrap_csrf(c)
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_client(client):
    client.get("/admin/login")
    login = post_form(
        client,
        "/admin/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
        follow_redirects=False,
    )
    assert login.status_code == 303
    return client


@pytest.fixture()
def sample_state() -> SessionState:
    return SessionState(
        company=CompanyIntake(
            company_name="Acme Corp",
            industry="Fintech",
            products="Payments platform",
            compliance="SOC 2, PCI DSS",
            risk_tolerance="Conservative",
        ),
        objectives=AssessmentObjectives(
            primary_goal="Prepare for audit",
            report_audiences=["Security team", "CTO / engineering leadership"],
            release_blockers=["Critical security", "High security"],
        ),
        applications=[
            ApplicationRecord(
                name="customer-portal",
                criticality="Critical",
                exposure="Internet-facing",
                data_classes="PII, payment data",
                repositories="github.com/acme/portal",
            )
        ],
    )


@pytest.fixture()
def session_with_state(db_session, sample_state):
    record, _ = create_session(db_session)
    save_session_state(db_session, record, sample_state)
    return record.id, record.access_key, sample_state
