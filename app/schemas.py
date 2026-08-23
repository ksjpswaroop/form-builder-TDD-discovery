"""Pydantic schemas for discovery questions, answers, and API payloads."""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class AnswerStatus(str, Enum):
    ANSWERED = "answered"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"
    CONFLICTING = "conflicting"


class AnswerType(str, Enum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    YES_NO = "yes_no"
    NUMBER = "number"
    FREE_TEXT = "free_text"
    TABLE = "table"


class SchemaField(BaseModel):
    id: str
    section: str
    question: str
    answer_type: AnswerType
    priority: str
    risk_if_unknown: str
    options: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    applies_to: Optional[str] = None


class SchemaSection(BaseModel):
    id: str
    title: str
    graphic: str


class DiscoverySchema(BaseModel):
    sections: list[SchemaSection]
    fields: list[SchemaField]


class FollowUpCondition(BaseModel):
    when_answer: str
    action: str


class GeneratedQuestion(BaseModel):
    question_id: str
    section: str
    applies_to: Optional[str] = None
    question: str
    reason: str
    answer_type: AnswerType
    options: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    required: bool = True
    risk_if_unknown: str = "medium"
    evidence_requested: list[str] = Field(default_factory=list)
    follow_up_conditions: list[FollowUpCondition] = Field(default_factory=list)


class QuestionRoundResponse(BaseModel):
    questions: list[GeneratedQuestion]
    coverage: dict[str, int]


class AnswerRecord(BaseModel):
    question_id: str
    status: AnswerStatus
    value: Optional[Any] = None
    notes: Optional[str] = None
    applies_to: Optional[str] = None


class CoverageSummary(BaseModel):
    completed: int = 0
    missing: int = 0
    unknown: int = 0
    not_applicable: int = 0
    conflicting: int = 0
    total: int = 0
    percent_complete: float = 0.0
    is_sufficient: bool = False


class CompanyIntake(BaseModel):
    company_name: str = ""
    industry: str = ""
    engineering_size: str = ""
    products: str = ""
    countries: str = ""
    compliance: str = ""
    tooling: str = ""
    risk_tolerance: str = ""


class AssessmentObjectives(BaseModel):
    primary_goal: str = ""
    report_audiences: list[str] = Field(default_factory=list)
    release_blockers: list[str] = Field(default_factory=list)
    assessment_frequency: str = ""
    remediation_capacity: str = ""


class ApplicationRecord(BaseModel):
    id: Optional[int] = None
    name: str
    description: str = ""
    business_owner: str = ""
    technical_owner: str = ""
    repositories: str = ""
    production_status: str = ""
    exposure: str = ""
    data_classes: str = ""
    criticality: str = ""
    user_count: str = ""


class SessionState(BaseModel):
    company: CompanyIntake = Field(default_factory=CompanyIntake)
    objectives: AssessmentObjectives = Field(default_factory=AssessmentObjectives)
    applications: list[ApplicationRecord] = Field(default_factory=list)
    answers: list[AnswerRecord] = Field(default_factory=list)
    current_round: int = 0
    plan_yaml: Optional[str] = None
    plan_approved: bool = False
