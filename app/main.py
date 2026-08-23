"""FastAPI application for adaptive discovery interviews."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlmodel import Session

from app.config import STATIC_DIR, settings
from app.database import create_db_and_tables, get_session
from app.form_options import (
    ASSESSMENT_FREQUENCY_OPTIONS,
    COMPLIANCE_OPTIONS,
    COUNTRY_OPTIONS,
    CRITICALITY_OPTIONS,
    DATA_CLASS_OPTIONS,
    ENGINEERING_SIZE_OPTIONS,
    EXPOSURE_OPTIONS,
    INDUSTRY_OPTIONS,
    PRIMARY_GOAL_OPTIONS,
    PRODUCTION_STATUS_OPTIONS,
    RELEASE_BLOCKER_OPTIONS,
    REMEDIATION_CAPACITY_OPTIONS,
    REPORT_AUDIENCE_OPTIONS,
    RISK_TOLERANCE_OPTIONS,
    TOOLING_OPTIONS,
    USER_COUNT_OPTIONS,
    split_multi_value,
)
from app.http_helpers import render_page
from app.middleware.security import SecurityHeadersMiddleware
from app.schemas import (
    AnswerRecord,
    AnswerStatus,
    ApplicationRecord,
    AssessmentObjectives,
    CompanyIntake,
)
from app.services.assessment_plan import build_assessment_plan, generate_plan_yaml
from app.services.auth import (
    clear_admin_cookie,
    is_admin_authenticated,
    require_admin,
    set_admin_cookie,
    verify_admin_credentials,
)
from app.services.coverage import compute_coverage
from app.services.csrf import validate_csrf
from app.services.data_paths import resolve_document_path
from app.services.document_exporter import export_all
from app.services.question_engine import generate_question_round
from app.services.schema_loader import load_discovery_schema
from app.services.session_service import (
    create_session,
    list_sessions,
    load_session_by_access_key,
    load_session_state,
    save_session_state,
    update_document_paths,
)
from app.services.startup_validation import ensure_data_directory_permissions, validate_settings

limiter = Limiter(key_func=get_remote_address, default_limits=[])


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()
    ensure_data_directory_permissions()
    create_db_and_tables()
    yield


app = FastAPI(
    title="TDD Discovery Form",
    lifespan=lifespan,
    root_path=settings.root_path or "",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def _section_graphics() -> dict[str, str]:
    schema = load_discovery_schema()
    return {s.id: s.graphic for s in schema.sections}


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _get_by_key(db: Session, access_key: str):
    try:
        return load_session_by_access_key(db, access_key)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")


def _url(path: str) -> str:
    base = settings.root_path.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}" if base else path


def _ctx(access_key: str, **kwargs) -> dict:
    return {"access_key": access_key, "base_path": _url(f"/k/{access_key}"), **kwargs}


@app.get("/")
def home(db: Session = Depends(get_db)):
    record, _ = create_session(db)
    return RedirectResponse(url=_url(f"/k/{record.access_key}/intake"), status_code=303)


@app.get("/retrieve")
def retrieve_page(request: Request):
    return render_page(request, "retrieve.html", {"error": None, "step": "retrieve"})


@app.post("/retrieve")
@limiter.limit(settings.rate_limit_retrieve)
def retrieve_submit(
    request: Request,
    access_key: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    key = access_key.strip()
    try:
        load_session_by_access_key(db, key)
    except ValueError:
        return render_page(
            request,
            "retrieve.html",
            {"error": "Not found. Check your key and try again.", "step": "retrieve"},
            status_code=400,
        )
    return RedirectResponse(url=_url(f"/k/{key}/intake"), status_code=303)


@app.get("/k/{access_key}/intake")
def intake_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    record, state = _get_by_key(db, access_key)
    return render_page(
        request,
        "intake.html",
        _ctx(
            access_key,
            company=state.company,
            step="intake",
            industry_options=INDUSTRY_OPTIONS,
            engineering_size_options=ENGINEERING_SIZE_OPTIONS,
            country_options=COUNTRY_OPTIONS,
            compliance_options=COMPLIANCE_OPTIONS,
            tooling_options=TOOLING_OPTIONS,
            risk_tolerance_options=RISK_TOLERANCE_OPTIONS,
            selected_compliance=split_multi_value(state.company.compliance),
            selected_tooling=split_multi_value(state.company.tooling),
        ),
    )


@app.post("/k/{access_key}/intake")
def intake_submit(
    request: Request,
    access_key: str,
    company_name: str = Form(""),
    industry: str = Form(""),
    engineering_size: str = Form(""),
    products: str = Form(""),
    countries: str = Form(""),
    compliance: list[str] = Form(default=[]),
    tooling: list[str] = Form(default=[]),
    risk_tolerance: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    record, state = _get_by_key(db, access_key)
    state.company = CompanyIntake(
        company_name=company_name,
        industry=industry,
        engineering_size=engineering_size,
        products=products,
        countries=countries,
        compliance=", ".join(compliance),
        tooling=", ".join(tooling),
        risk_tolerance=risk_tolerance,
    )
    save_session_state(db, record, state, step="objectives")
    return RedirectResponse(url=_url(f"/k/{access_key}/objectives"), status_code=303)


@app.get("/k/{access_key}/objectives")
def objectives_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    record, state = _get_by_key(db, access_key)
    return render_page(
        request,
        "objectives.html",
        _ctx(
            access_key,
            objectives=state.objectives,
            step="objectives",
            goal_options=PRIMARY_GOAL_OPTIONS,
            audience_options=REPORT_AUDIENCE_OPTIONS,
            blocker_options=RELEASE_BLOCKER_OPTIONS,
            frequency_options=ASSESSMENT_FREQUENCY_OPTIONS,
            capacity_options=REMEDIATION_CAPACITY_OPTIONS,
        ),
    )


@app.post("/k/{access_key}/objectives")
def objectives_submit(
    request: Request,
    access_key: str,
    primary_goal: str = Form(""),
    assessment_frequency: str = Form(""),
    remediation_capacity: str = Form(""),
    report_audiences: list[str] = Form(default=[]),
    release_blockers: list[str] = Form(default=[]),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    record, state = _get_by_key(db, access_key)
    state.objectives = AssessmentObjectives(
        primary_goal=primary_goal,
        report_audiences=report_audiences,
        release_blockers=release_blockers,
        assessment_frequency=assessment_frequency,
        remediation_capacity=remediation_capacity,
    )
    save_session_state(db, record, state, step="applications")
    return RedirectResponse(url=_url(f"/k/{access_key}/applications"), status_code=303)


@app.get("/k/{access_key}/applications")
def applications_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    record, state = _get_by_key(db, access_key)
    return render_page(
        request,
        "applications.html",
        _ctx(
            access_key,
            applications=state.applications,
            step="applications",
            production_status_options=PRODUCTION_STATUS_OPTIONS,
            exposure_options=EXPOSURE_OPTIONS,
            data_class_options=DATA_CLASS_OPTIONS,
            criticality_options=CRITICALITY_OPTIONS,
            user_count_options=USER_COUNT_OPTIONS,
        ),
    )


@app.post("/k/{access_key}/applications")
def applications_submit(
    request: Request,
    access_key: str,
    name: str = Form(...),
    description: str = Form(""),
    business_owner: str = Form(""),
    technical_owner: str = Form(""),
    repositories: str = Form(""),
    production_status: str = Form(""),
    exposure: str = Form(""),
    data_classes: list[str] = Form(default=[]),
    criticality: str = Form(""),
    user_count: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    record, state = _get_by_key(db, access_key)
    state.applications.append(
        ApplicationRecord(
            name=name,
            description=description,
            business_owner=business_owner,
            technical_owner=technical_owner,
            repositories=repositories,
            production_status=production_status,
            exposure=exposure,
            data_classes=", ".join(data_classes),
            criticality=criticality,
            user_count=user_count,
        )
    )
    save_session_state(db, record, state, step="applications")
    return RedirectResponse(url=_url(f"/k/{access_key}/applications"), status_code=303)


@app.post("/k/{access_key}/applications/done")
def applications_done(
    request: Request,
    access_key: str,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    record, state = _get_by_key(db, access_key)
    if not state.applications:
        raise HTTPException(status_code=400, detail="Add at least one application")
    save_session_state(db, record, state, step="interview")
    return RedirectResponse(url=_url(f"/k/{access_key}/interview"), status_code=303)


@app.get("/k/{access_key}/interview")
def interview_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    record, state = _get_by_key(db, access_key)
    round_data = generate_question_round(state)
    coverage = compute_coverage(state)
    schema = load_discovery_schema()
    section_titles = {s.id: s.title for s in schema.sections}
    graphics = _section_graphics()
    return render_page(
        request,
        "interview.html",
        _ctx(
            access_key,
            questions=round_data.questions,
            coverage=coverage,
            section_titles=section_titles,
            graphics=graphics,
            round_number=state.current_round + 1,
            step="interview",
        ),
    )


@app.post("/k/{access_key}/interview")
@limiter.limit("30/minute")
async def interview_submit(access_key: str, request: Request, db: Session = Depends(get_db)):
    record, state = _get_by_key(db, access_key)
    form = await request.form()
    validate_csrf(request, str(form.get("csrf_token", "")))

    new_answers: list[AnswerRecord] = []
    notes_map: dict[str, str] = {}
    status_map: dict[str, str] = {}

    for key, value in form.items():
        if key.startswith("notes__"):
            notes_map[key.replace("notes__", "")] = str(value)
        elif key.startswith("status__"):
            status_map[key.replace("status__", "")] = str(value)

    for key, value in form.items():
        if not key.startswith("q__"):
            continue
        field_key = key.replace("q__", "")
        status = status_map.get(field_key, "answered")
        notes = notes_map.get(field_key, "")
        parts = field_key.split("::", 1)
        question_id = parts[0]
        applies_to = parts[1] if len(parts) > 1 and parts[1] else None

        if status == "unknown":
            answer_status = AnswerStatus.UNKNOWN
            answer_value = None
        elif status == "not_applicable":
            answer_status = AnswerStatus.NOT_APPLICABLE
            answer_value = None
        else:
            answer_status = AnswerStatus.ANSWERED
            answer_value = str(value)

        new_answers.append(
            AnswerRecord(
                question_id=question_id,
                status=answer_status,
                value=answer_value,
                notes=notes or None,
                applies_to=applies_to,
            )
        )

    merged: dict[str, AnswerRecord] = {}
    for a in state.answers:
        key = f"{a.question_id}::{a.applies_to or ''}"
        merged[key] = a
    for a in new_answers:
        key = f"{a.question_id}::{a.applies_to or ''}"
        merged[key] = a

    state.answers = list(merged.values())
    state.current_round += 1
    coverage = compute_coverage(state)

    if coverage.is_sufficient:
        state.plan_yaml = generate_plan_yaml(state)
        save_session_state(db, record, state, step="plan")
        return RedirectResponse(url=_url(f"/k/{access_key}/plan"), status_code=303)

    save_session_state(db, record, state, step="interview")
    return RedirectResponse(url=_url(f"/k/{access_key}/interview"), status_code=303)


@app.post("/k/{access_key}/interview/generate-plan")
def interview_generate_plan(
    request: Request,
    access_key: str,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    record, state = _get_by_key(db, access_key)
    state.plan_yaml = generate_plan_yaml(state)
    save_session_state(db, record, state, step="plan")
    return RedirectResponse(url=_url(f"/k/{access_key}/plan"), status_code=303)


@app.get("/k/{access_key}/plan")
def plan_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    record, state = _get_by_key(db, access_key)
    if not state.plan_yaml:
        state.plan_yaml = generate_plan_yaml(state)
        save_session_state(db, record, state)

    coverage = compute_coverage(state)
    plan_dict = build_assessment_plan(state)
    show_key_modal = request.query_params.get("approved") == "1"

    return render_page(
        request,
        "plan.html",
        _ctx(
            access_key,
            plan_yaml=state.plan_yaml,
            plan_dict=plan_dict,
            company_products=state.company.products,
            coverage=coverage,
            plan_approved=state.plan_approved,
            step="plan",
            show_key_modal=show_key_modal,
            has_documents=bool(record.pdf_path),
        ),
    )


@app.post("/k/{access_key}/plan/approve")
def plan_approve(
    request: Request,
    access_key: str,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    record, state = _get_by_key(db, access_key)
    if not state.plan_yaml:
        state.plan_yaml = generate_plan_yaml(state)

    state.plan_approved = True
    record.approved_at = datetime.utcnow()

    export = export_all(record, state, base_url=_base_url(request))
    update_document_paths(db, record, export.pdf_path, export.excel_path, export.json_path)

    save_session_state(db, record, state, step="complete")
    return RedirectResponse(url=_url(f"/k/{access_key}/plan?approved=1"), status_code=303)


@app.get("/k/{access_key}/documents/{format}")
def download_document(access_key: str, format: str, db: Session = Depends(get_db)):
    record, _ = _get_by_key(db, access_key)
    path_map = {
        "pdf": record.pdf_path,
        "xlsx": record.excel_path,
        "excel": record.excel_path,
        "json": record.json_path,
    }
    rel = path_map.get(format)
    if not rel:
        raise HTTPException(status_code=404, detail="Not found")

    full_path = resolve_document_path(rel)
    media = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }
    return FileResponse(full_path, media_type=media.get(format, "application/octet-stream"))


# --- Admin ---


@app.get("/admin/login")
def admin_login_page(request: Request):
    if is_admin_authenticated(request):
        return RedirectResponse(url=_url("/admin/sessions"), status_code=303)
    return render_page(request, "admin/login.html", {"error": None, "step": "admin"})


@app.post("/admin/login")
@limiter.limit(settings.rate_limit_login)
def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
):
    validate_csrf(request, csrf_token)
    if not verify_admin_credentials(username, password):
        return render_page(
            request,
            "admin/login.html",
            {"error": "Invalid credentials", "step": "admin"},
            status_code=401,
        )
    response = RedirectResponse(url=_url("/admin/sessions"), status_code=303)
    set_admin_cookie(response)
    return response


@app.post("/admin/logout")
def admin_logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    response = RedirectResponse(url=_url("/admin/login"), status_code=303)
    clear_admin_cookie(response)
    return response


@app.get("/admin/sessions")
def admin_sessions_list(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    sessions = list_sessions(db)
    return render_page(request, "admin/sessions.html", {"sessions": sessions, "step": "admin"})


@app.get("/admin/sessions/{session_id}")
def admin_session_detail(request: Request, session_id: int, db: Session = Depends(get_db)):
    require_admin(request)
    record, state = load_session_state(db, session_id)
    return render_page(
        request,
        "admin/session_detail.html",
        {"record": record, "state": state, "step": "admin"},
    )


@app.post("/admin/sessions/{session_id}/update")
def admin_session_update(
    request: Request,
    session_id: int,
    company_name: str = Form(""),
    products: str = Form(""),
    industry: str = Form(""),
    primary_goal: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    require_admin(request)
    validate_csrf(request, csrf_token)
    record, state = load_session_state(db, session_id)
    state.company.company_name = company_name
    state.company.products = products
    state.company.industry = industry
    state.objectives.primary_goal = primary_goal
    if not state.plan_yaml:
        state.plan_yaml = generate_plan_yaml(state)
    save_session_state(db, record, state)
    return RedirectResponse(url=_url(f"/admin/sessions/{session_id}"), status_code=303)


@app.post("/admin/sessions/{session_id}/regenerate")
def admin_regenerate(
    request: Request,
    session_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    require_admin(request)
    validate_csrf(request, csrf_token)
    record, state = load_session_state(db, session_id)
    if not state.plan_yaml:
        state.plan_yaml = generate_plan_yaml(state)
    export = export_all(record, state, base_url=_base_url(request))
    update_document_paths(db, record, export.pdf_path, export.excel_path, export.json_path)
    return RedirectResponse(url=_url(f"/admin/sessions/{session_id}"), status_code=303)
