"""Public routes keyed by access_key."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlmodel import Session

from app.config import DATA_DIR, TEMPLATES_DIR
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
from app.schemas import (
    AnswerRecord,
    AnswerStatus,
    ApplicationRecord,
    AssessmentObjectives,
    CompanyIntake,
)
from app.services.assessment_plan import build_assessment_plan, generate_plan_yaml
from app.services.coverage import compute_coverage
from app.services.document_exporter import export_all
from app.services.question_engine import generate_question_round
from app.services.schema_loader import load_discovery_schema
from app.services.session_service import (
    load_session_by_access_key,
    save_session_state,
    update_document_paths,
)
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def get_db():
    from app.database import get_session

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


@router.get("/retrieve", response_class=HTMLResponse)
def retrieve_page(request: Request):
    return templates.TemplateResponse(request, "retrieve.html", {})


@router.post("/retrieve")
def retrieve_submit(access_key: str = Form(...)):
    return RedirectResponse(url=f"/k/{access_key.strip()}/intake", status_code=303)


@router.get("/k/{access_key}/intake", response_class=HTMLResponse)
def intake_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    try:
        record, state = load_session_by_access_key(db, access_key)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid access key")
    return templates.TemplateResponse(
        request,
        "intake.html",
        {
            "access_key": access_key,
            "company": state.company,
            "step": "intake",
            "industry_options": INDUSTRY_OPTIONS,
            "engineering_size_options": ENGINEERING_SIZE_OPTIONS,
            "country_options": COUNTRY_OPTIONS,
            "compliance_options": COMPLIANCE_OPTIONS,
            "tooling_options": TOOLING_OPTIONS,
            "risk_tolerance_options": RISK_TOLERANCE_OPTIONS,
            "selected_compliance": split_multi_value(state.company.compliance),
            "selected_tooling": split_multi_value(state.company.tooling),
        },
    )


@router.post("/k/{access_key}/intake")
def intake_submit(
    access_key: str,
    company_name: str = Form(""),
    industry: str = Form(""),
    engineering_size: str = Form(""),
    products: str = Form(""),
    countries: str = Form(""),
    compliance: list[str] = Form(default=[]),
    tooling: list[str] = Form(default=[]),
    risk_tolerance: str = Form(""),
    db: Session = Depends(get_db),
):
    record, state = load_session_by_access_key(db, access_key)
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
    return RedirectResponse(url=f"/k/{access_key}/objectives", status_code=303)


@router.get("/k/{access_key}/objectives", response_class=HTMLResponse)
def objectives_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    record, state = load_session_by_access_key(db, access_key)
    return templates.TemplateResponse(
        request,
        "objectives.html",
        {
            "access_key": access_key,
            "objectives": state.objectives,
            "step": "objectives",
            "goal_options": PRIMARY_GOAL_OPTIONS,
            "audience_options": REPORT_AUDIENCE_OPTIONS,
            "blocker_options": RELEASE_BLOCKER_OPTIONS,
            "frequency_options": ASSESSMENT_FREQUENCY_OPTIONS,
            "capacity_options": REMEDIATION_CAPACITY_OPTIONS,
        },
    )


@router.post("/k/{access_key}/objectives")
def objectives_submit(
    access_key: str,
    primary_goal: str = Form(""),
    assessment_frequency: str = Form(""),
    remediation_capacity: str = Form(""),
    report_audiences: list[str] = Form(default=[]),
    release_blockers: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    record, state = load_session_by_access_key(db, access_key)
    state.objectives = AssessmentObjectives(
        primary_goal=primary_goal,
        report_audiences=report_audiences,
        release_blockers=release_blockers,
        assessment_frequency=assessment_frequency,
        remediation_capacity=remediation_capacity,
    )
    save_session_state(db, record, state, step="applications")
    return RedirectResponse(url=f"/k/{access_key}/applications", status_code=303)


@router.get("/k/{access_key}/applications", response_class=HTMLResponse)
def applications_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    record, state = load_session_by_access_key(db, access_key)
    return templates.TemplateResponse(
        request,
        "applications.html",
        {
            "access_key": access_key,
            "applications": state.applications,
            "step": "applications",
            "production_status_options": PRODUCTION_STATUS_OPTIONS,
            "exposure_options": EXPOSURE_OPTIONS,
            "data_class_options": DATA_CLASS_OPTIONS,
            "criticality_options": CRITICALITY_OPTIONS,
            "user_count_options": USER_COUNT_OPTIONS,
        },
    )


@router.post("/k/{access_key}/applications")
def applications_submit(
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
    db: Session = Depends(get_db),
):
    record, state = load_session_by_access_key(db, access_key)
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
    return RedirectResponse(url=f"/k/{access_key}/applications", status_code=303)


@router.post("/k/{access_key}/applications/done")
def applications_done(access_key: str, db: Session = Depends(get_db)):
    record, state = load_session_by_access_key(db, access_key)
    if not state.applications:
        raise HTTPException(status_code=400, detail="Add at least one application")
    save_session_state(db, record, state, step="interview")
    return RedirectResponse(url=f"/k/{access_key}/interview", status_code=303)


@router.get("/k/{access_key}/interview", response_class=HTMLResponse)
def interview_page(request: Request, access_key: str, db: Session = Depends(get_db)):
    record, state = load_session_by_access_key(db, access_key)
    round_data = generate_question_round(state)
    coverage = compute_coverage(state)
    schema = load_discovery_schema()
    section_titles = {s.id: s.title for s in schema.sections}
    graphics = _section_graphics()
    return templates.TemplateResponse(
        request,
        "interview.html",
        {
            "access_key": access_key,
            "questions": round_data.questions,
            "coverage": coverage,
            "section_titles": section_titles,
            "graphics": graphics,
            "round_number": state.current_round + 1,
            "step": "interview",
        },
    )


@router.post("/k/{access_key}/interview")
async def interview_submit(access_key: str, request: Request, db: Session = Depends(get_db)):
    record, state = load_session_by_access_key(db, access_key)
    form = await request.form()
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
        return RedirectResponse(url=f"/k/{access_key}/plan", status_code=303)

    save_session_state(db, record, state, step="interview")
    return RedirectResponse(url=f"/k/{access_key}/interview", status_code=303)


@router.post("/k/{access_key}/interview/generate-plan")
def interview_generate_plan(access_key: str, db: Session = Depends(get_db)):
    record, state = load_session_by_access_key(db, access_key)
    state.plan_yaml = generate_plan_yaml(state)
    save_session_state(db, record, state, step="plan")
    return RedirectResponse(url=f"/k/{access_key}/plan", status_code=303)


@router.get("/k/{access_key}/plan", response_class=HTMLResponse)
def plan_page(request: Request, access_key: str, approved: int = 0, db: Session = Depends(get_db)):
    record, state = load_session_by_access_key(db, access_key)
    if not state.plan_yaml:
        state.plan_yaml = generate_plan_yaml(state)
        save_session_state(db, record, state)

    coverage = compute_coverage(state)
    plan_dict = build_assessment_plan(state)
    return templates.TemplateResponse(
        request,
        "plan.html",
        {
            "access_key": access_key,
            "plan_yaml": state.plan_yaml,
            "plan_dict": plan_dict,
            "coverage": coverage,
            "plan_approved": state.plan_approved,
            "step": "plan",
            "show_key_modal": approved == 1 and state.plan_approved,
            "has_documents": bool(record.pdf_path),
        },
    )


@router.post("/k/{access_key}/plan/approve")
def plan_approve(access_key: str, request: Request, db: Session = Depends(get_db)):
    from datetime import datetime

    record, state = load_session_by_access_key(db, access_key)
    if not state.plan_yaml:
        state.plan_yaml = generate_plan_yaml(state)

    state.plan_approved = True
    record.approved_at = datetime.utcnow()
    save_session_state(db, record, state, step="complete")

    export = export_all(record, state, base_url=_base_url(request))
    update_document_paths(db, record, export.pdf_path, export.excel_path, export.json_path)

    return RedirectResponse(url=f"/k/{access_key}/plan?approved=1", status_code=303)


@router.get("/k/{access_key}/documents/{format}")
def download_document(access_key: str, format: str, db: Session = Depends(get_db)):
    record, _ = load_session_by_access_key(db, access_key)
    path_map = {
        "pdf": record.pdf_path,
        "xlsx": record.excel_path,
        "json": record.json_path,
    }
    rel_path = path_map.get(format)
    if not rel_path:
        raise HTTPException(status_code=404, detail="Unknown format")

    full_path = DATA_DIR / rel_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    media_types = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }
    return FileResponse(full_path, media_type=media_types[format], filename=full_path.name)
