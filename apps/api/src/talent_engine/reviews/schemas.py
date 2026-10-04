from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictBool, StrictInt, model_validator
from talent_engine.campaigns.schemas import Model
from talent_engine.evaluations.schemas import Evaluation


class ReviewExpectation(Model):
    review_revision: StrictInt = Field(ge=1, le=9007199254740990)
    effective_evaluation_id: UUID | None


class CorrectionInput(ReviewExpectation):
    target_kind: Literal["assessment", "condition"]
    criterion_id: UUID
    action: Literal["set", "restore_base"]
    status: (
        Literal[
            "evaluated",
            "insufficient_information",
            "conflicting_information",
            "source_unavailable",
            "met",
            "unmet",
            "unknown",
        ]
        | None
    ) = None
    level: StrictInt | None = Field(default=None, ge=0, le=4)
    reason: str = Field(min_length=1, max_length=2000)
    human_note: str | None = Field(default=None, min_length=1, max_length=2000)
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=30)
    zero_evidence_quote: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def valid_value(self):
        if (
            not self.reason.strip()
            or self.human_note is not None
            and not self.human_note.strip()
        ):
            raise ValueError("Nonempty justification required")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence")
        if self.action == "restore_base":
            if (
                self.status is not None
                or self.level is not None
                or self.human_note
                or self.evidence_ids
                or self.zero_evidence_quote
            ):
                raise ValueError("Restore uses the immutable base")
            return self
        allowed = (
            {"met", "unmet", "unknown"}
            if self.target_kind == "condition"
            else {
                "evaluated",
                "insufficient_information",
                "conflicting_information",
                "source_unavailable",
            }
        )
        if self.status not in allowed or (self.status == "evaluated") != (
            self.level is not None
        ):
            raise ValueError("Status and level disagree")
        if not self.evidence_ids and not self.human_note:
            raise ValueError("Evidence or recorded human verification required")
        if (self.level == 0) != bool(self.zero_evidence_quote):
            raise ValueError("Explicit zero observation required only for level zero")
        return self


class ReviewEvent(Model):
    id: UUID
    application_id: UUID
    evaluation_id: UUID | None
    author_id: UUID
    author_login: str | None = None
    created_at: datetime
    review_revision: int
    kind: str
    criterion_id: UUID | None
    action: str
    reason: str
    previous: dict
    value: dict
    origin_event_id: UUID | None


class DecisionInput(ReviewExpectation):
    decision: Literal["to_review", "shortlisted", "not_selected"]
    reason: str = Field(default="", max_length=2000)


class AnalysisInput(ReviewExpectation):
    reason: Literal["retry_sources", "reanalyze"]
    base_run_id: UUID
    source_ids: list[UUID] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def unique_sources(self):
        if (
            len(set(self.source_ids)) != len(self.source_ids)
            or self.reason == "retry_sources"
            and not self.source_ids
        ):
            raise ValueError("Select distinct failed sources")
        return self


class AnalysisReceipt(Model):
    id: UUID
    application_id: UUID
    reason: Literal["retry_sources", "reanalyze"]
    state: Literal["queued"] = "queued"
    created_at: datetime


class Reapplication(Model):
    origin_event_id: UUID
    correction: CorrectionInput


class ActivationInput(ReviewExpectation):
    evaluation_id: UUID
    mode: Literal["use_new_base", "reapply_selected"]
    reason: str = Field(min_length=1, max_length=2000)
    confirm_discard_corrections: StrictBool = False
    corrections: list[Reapplication] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def explicit_strategy(self):
        if not self.reason.strip() or (self.mode == "reapply_selected") != bool(
            self.corrections
        ):
            raise ValueError("Explicit activation strategy required")
        targets = [
            (c.correction.target_kind, c.correction.criterion_id)
            for c in self.corrections
        ]
        if len(set(targets)) != len(targets):
            raise ValueError("One correction per target")
        for item in self.corrections:
            if (
                item.correction.review_revision != self.review_revision
                or item.correction.effective_evaluation_id
                != self.effective_evaluation_id
                or item.correction.action != "set"
            ):
                raise ValueError("Reapplication must confirm the current version")
        return self


class EvaluationVersion(Model):
    base: Evaluation
    corrected: Evaluation | None
