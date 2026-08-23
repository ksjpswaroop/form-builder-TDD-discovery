"""Admin authentication via signed cookies."""

from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings
from app.services.passwords import verify_password

COOKIE_NAME = "admin_session"
MAX_AGE = 86400 * 7


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="admin-auth")


def verify_admin_credentials(username: str, password: str) -> bool:
    if username != settings.admin_username:
        return False
    if settings.admin_password_hash:
        return verify_password(password, settings.admin_password_hash)
    return password == settings.admin_password


def set_admin_cookie(response: Response) -> None:
    token = _serializer().dumps({"admin": True})
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="strict",
        max_age=MAX_AGE,
        secure=settings.require_https,
        path="/admin",
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/admin")


def is_admin_authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        data = _serializer().loads(token, max_age=MAX_AGE)
        return bool(data.get("admin"))
    except (BadSignature, SignatureExpired):
        return False


def require_admin(request: Request) -> None:
    if not is_admin_authenticated(request):
        raise HTTPException(status_code=401, detail="Admin login required")
