"""Admin panel routes."""

import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.auth.admin import authenticate_admin, is_admin, login_admin, logout_admin, require_admin
from app.config import TEMPLATES_DIR
from app.schemas import SessionState
from app.services.assessment_plan import generate_plan_yaml
from app.services.document_exporter import export_all
from app.services.session_service import (
    list_sessions,
    load_session_state,
    save_session_state,
    update_document_paths,
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/admin")


def get_db():
    from app.database import get_session

    db = get_session()
    try:
        yield db
    finally:
        db.close()


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    if is_admin(request):
        return RedirectResponse(url="/admin/sessions", status_code=303)
    return templates.TemplateResponse(request, "admin/login.html", {})


@router.post("/login")
def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not authenticate_admin(username, password):
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": "Invalid credentials"},
            status_code=401,
        )
    login_admin(request)
    return RedirectResponse(url="/admin/sessions", status_code=303)


@router.post("/logout")
def admin_logout(request: Request):
    logout_admin(request)
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/sessions", response_class=HTMLResponse)
def admin_sessions(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    sessions = list_sessions(db)
    return templates.TemplateResponse(
        request,
        "admin/sessions.html",
        {"sessions": sessions},
    )


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
def admin_session_detail(request: Request, session_id: int, db: Session = Depends(get_db)):
    require_admin(request)
    record, state = load_session_state(db, session_id)
    return templates.TemplateResponse(
        request,
        "admin/session_detail.html",
        {
            "record": record,
            "state": state,
            "state_json_pretty": json.dumps(state.model_dump(), indent=2),
        },
    )


@router.post("/sessions/{session_id}/update")
def admin_session_update(
    request: Request,
    session_id: int,
    state_json: str = Form(...),
    db: Session = Depends(get_db),
):
    require_admin(request)
    record, _ = load_session_state(db, session_id)
    try:
        state = SessionState.model_validate_json(state_json)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}")

    if not state.plan_yaml:
        state.plan_yaml = generate_plan_yaml(state)
    save_session_state(db, record, state)
    return RedirectResponse(url=f"/admin/sessions/{session_id}", status_code=303)


@router.post("/sessions/{session_id}/regenerate")
def admin_regenerate(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
):
    require_admin(request)
    record, state = load_session_state(db, session_id)
    if not state.plan_yaml:
        state.plan_yaml = generate_plan_yaml(state)
        save_session_state(db, record, state)

    export = export_all(record, state, base_url=_base_url(request))
    update_document_paths(db, record, export.pdf_path, export.excel_path, export.json_path)
    return RedirectResponse(url=f"/admin/sessions/{session_id}", status_code=303)
