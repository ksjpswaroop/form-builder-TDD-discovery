"""SQLModel database models."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class DiscoverySession(SQLModel, table=True):
    __tablename__ = "discovery_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    company_name: str = ""
    products: str = ""
    access_key: str = Field(default="", index=True, unique=True)
    state_json: str = "{}"
    plan_yaml: Optional[str] = None
    plan_approved: bool = False
    current_step: str = "intake"
    pdf_path: Optional[str] = None
    excel_path: Optional[str] = None
    json_path: Optional[str] = None
    documents_generated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
