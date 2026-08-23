"""Security hardening tests."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services.passwords import hash_password, verify_password
from app.services.startup_validation import validate_settings
from tests.conftest import bootstrap_csrf, post_form


def test_security_headers_on_html(client):
    response = client.get("/retrieve")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_path_traversal_download_rejected(client, db_engine):
    from sqlmodel import Session

    from app.services.session_service import create_session, save_session_state

    with Session(db_engine) as db:
        record, state = create_session(db)
        state.company.company_name = "Traversal Co"
        save_session_state(db, record, state)
        record.pdf_path = "../../../etc/passwd"
        db.add(record)
        db.commit()
        key = record.access_key

    response = client.get(f"/k/{key}/documents/pdf")
    assert response.status_code == 403


def test_csrf_token_rendered_in_form(client):
    response = client.get("/retrieve")
    assert response.status_code == 200
    cookie = client.cookies.get("csrf_token")
    assert cookie
    assert f'name="csrf_token" value="{cookie}"' in response.text


def test_csrf_missing_token_rejected(client):
    response = client.post(
        "/retrieve",
        data={"access_key": "invalid"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_csrf_invalid_token_rejected(client):
    bootstrap_csrf(client)
    response = client.post(
        "/retrieve",
        data={"access_key": "invalid", "csrf_token": "not-a-valid-token"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_rate_limit_admin_login(client):
    client.get("/admin/login")
    for _ in range(6):
        post_form(
            client,
            "/admin/login",
            data={"username": "wrong", "password": "wrong"},
            follow_redirects=False,
        )
    response = post_form(
        client,
        "/admin/login",
        data={"username": "wrong", "password": "wrong"},
        follow_redirects=False,
    )
    assert response.status_code == 429


def test_rate_limit_retrieve(client):
    invalid_key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    for _ in range(11):
        post_form(
            client,
            "/retrieve",
            data={"access_key": invalid_key},
            follow_redirects=False,
        )
    response = post_form(
        client,
        "/retrieve",
        data={"access_key": invalid_key},
        follow_redirects=False,
    )
    assert response.status_code == 429


def test_production_rejects_weak_secret_key(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "change-me-in-production")
    monkeypatch.setattr(settings, "admin_password_hash", hash_password("strong-admin-pass"))
    monkeypatch.setattr(settings, "admin_password", "not-default")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_settings()


def test_password_verify_bcrypt():
    hashed = hash_password("my-secure-password")
    assert verify_password("my-secure-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_security_badge_visible(client):
    response = client.get("/retrieve")
    assert "Your information is secured" in response.text


def test_self_hosted_htmx(client):
    response = client.get("/retrieve")
    assert "/static/js/htmx.min.js" in response.text
    assert "unpkg.com" not in response.text
