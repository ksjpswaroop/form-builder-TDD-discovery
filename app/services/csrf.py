"""CSRF protection via signed double-submit cookie."""

import secrets

from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

CSRF_COOKIE = "csrf_token"
CSRF_MAX_AGE = 86400 * 2


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="csrf-token")


def generate_csrf_token() -> str:
    return _serializer().dumps({"t": secrets.token_hex(16)})


def get_csrf_token(request: Request) -> str:
    cookie = request.cookies.get(CSRF_COOKIE)
    if cookie:
        try:
            _serializer().loads(cookie, max_age=CSRF_MAX_AGE)
            return cookie
        except (BadSignature, SignatureExpired):
            pass
    return generate_csrf_token()


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=True,
        samesite="strict",
        max_age=CSRF_MAX_AGE,
        secure=settings.require_https,
    )


def validate_csrf(request: Request, form_token: str | None) -> None:
    if not form_token:
        raise HTTPException(status_code=403, detail="Invalid request")
    cookie = request.cookies.get(CSRF_COOKIE)
    if not cookie or form_token != cookie:
        raise HTTPException(status_code=403, detail="Invalid request")
    try:
        _serializer().loads(cookie, max_age=CSRF_MAX_AGE)
        _serializer().loads(form_token, max_age=CSRF_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=403, detail="Invalid request")
