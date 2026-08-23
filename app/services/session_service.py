"""Session persistence and access-key lookup."""

import re
import secrets
from datetime import datetime

from sqlmodel import Session, select

from app.models import DiscoverySession
from app.schemas import SessionState

ACCESS_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")


def generate_access_key() -> str:
    return secrets.token_urlsafe(32)


def _validate_access_key_format(access_key: str) -> None:
    if not access_key or not ACCESS_KEY_PATTERN.match(access_key.strip()):
        raise ValueError("Not found")


def load_session_state(db: Session, session_id: int) -> tuple[DiscoverySession, SessionState]:
    record = db.get(DiscoverySession, session_id)
    if not record:
        raise ValueError(f"Session {session_id} not found")
    state = SessionState.model_validate_json(record.state_json)
    return record, state


def load_session_by_access_key(db: Session, access_key: str) -> tuple[DiscoverySession, SessionState]:
    _validate_access_key_format(access_key)
    record = db.exec(
        select(DiscoverySession).where(DiscoverySession.access_key == access_key.strip())
    ).first()
    if not record:
        raise ValueError("Not found")
    state = SessionState.model_validate_json(record.state_json)
    return record, state


def save_session_state(
    db: Session,
    record: DiscoverySession,
    state: SessionState,
    step: str | None = None,
) -> DiscoverySession:
    record.state_json = state.model_dump_json()
    record.updated_at = datetime.utcnow()
    record.company_name = state.company.company_name
    record.products = state.company.products
    record.plan_yaml = state.plan_yaml
    record.plan_approved = state.plan_approved
    if step:
        record.current_step = step
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_session(db: Session) -> tuple[DiscoverySession, SessionState]:
    state = SessionState()
    record = DiscoverySession(
        state_json=state.model_dump_json(),
        access_key=generate_access_key(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, state


def list_sessions(db: Session) -> list[DiscoverySession]:
    return list(
        db.exec(select(DiscoverySession).order_by(DiscoverySession.created_at.desc())).all()
    )


def update_document_paths(
    db: Session,
    record: DiscoverySession,
    pdf_path: str,
    excel_path: str,
    json_path: str,
) -> DiscoverySession:
    record.pdf_path = pdf_path
    record.excel_path = excel_path
    record.json_path = json_path
    record.documents_generated_at = datetime.utcnow()
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
