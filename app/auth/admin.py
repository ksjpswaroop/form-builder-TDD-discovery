"""Admin authentication via session cookie."""

from fastapi import HTTPException, Request

from app.config import settings


def is_admin(request: Request) -> bool:
    return request.session.get("admin_authenticated") is True


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin login required")


def authenticate_admin(username: str, password: str) -> bool:
    return username == settings.admin_username and password == settings.admin_password


def login_admin(request: Request) -> None:
    request.session["admin_authenticated"] = True


def logout_admin(request: Request) -> None:
    request.session.pop("admin_authenticated", None)
