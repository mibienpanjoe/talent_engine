from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictInt, model_validator
from talent_engine.campaigns.schemas import Model


class Assessment(Model):
    criterion_id: UUID
    status: Literal[
        "evaluated",
        "insufficient_information",
        "conflicting_information",
        "source_unavailable",
    ]
    level: StrictInt | None = Field(ge=0, le=4)
    evidence_ids: list[UUID] = Field(max_length=30)
    rationale: str = Field(min_length=1, max_length=2000)
    zero_evidence_quote: str | None = Field(default=None, max_length=1000)
    uncertainties: list[str] = Field(max_length=10)
    policy_version: str = Field(max_length=100)
    rubric_version: str = Field(max_length=100)

    @model_validator(mode="after")
    def consistency(self):
        if (self.status == "evaluated") != (self.level is not None):
            raise ValueError("Status and level disagree")
        if not self.rationale.strip():
            raise ValueError("Rationale required")
        if self.level != 0 and self.zero_evidence_quote is not None:
            raise ValueError("Zero quote only for explicit zero")
        if self.level == 0 and not self.zero_evidence_quote:
            raise ValueError("Explicit zero observation required")
        if self.status == "evaluated" and not self.evidence_ids:
            raise ValueError("Evidence required")
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or any(
            len(x) > 500 for x in self.uncertainties
        ):
            raise ValueError("Invalid evidence or limits")
        return self


class AssessmentResponse(Model):
    assessments: list[Assessment] = Field(max_length=20)


class Rational(Model):
    numerator: str
    denominator: str


class Alert(Model):
    criterion_id: UUID
    code: Literal["required_skill_unknown", "required_skill_below_threshold"]


class Calculation(Model):
    score: str | None
    score_exact: Rational | None
    coverage: str
    lower_bound: str
    upper_bound: str
    complete: bool
    alerts: list[Alert]


class ConditionResult(Model):
    criterion_id: UUID
    question_id: UUID
    required: bool
    status: Literal["met", "unmet", "unknown"]
    value: str | list[str] | None
    rationale: str
    evidence_ids: list[UUID] = Field(default_factory=list)


Eligibility = Literal["eligible", "condition_unmet", "needs_review", "not_applicable"]


class Provenance(Model):
    mode: Literal["live"]
    requested_model: str | None
    provider: str | None
    effective_model: str | None
    response_model: str | None
    prompt_version: str
    adapter_version: str
    prompt_hash: str
    evidence_ids: list[UUID]
    blocked_evidence_ids: list[UUID]
    omitted_evidence_ids: list[UUID]
    extractor_versions: list[str]
    duration_seconds: float
    started_at: datetime
    finished_at: datetime


class Evaluation(Model):
    id: UUID
    application_id: UUID
    run_id: UUID
    snapshot_id: UUID
    policy_version: str
    assessments: list[Assessment]
    conditions: list[ConditionResult]
    eligibility: Eligibility
    calculation: Calculation
    provenance: Provenance
    created_at: datetime
