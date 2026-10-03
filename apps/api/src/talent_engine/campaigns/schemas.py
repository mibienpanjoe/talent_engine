from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictBool,
    model_validator,
)
from talent_engine.errors import ErrorDetail

FAMILIES = {
    "training": {
        "programming_foundations": 40,
        "practical_work": 35,
        "learning_approach": 25,
    },
    "recruitment": {
        "audience_understanding": 40,
        "results_analysis": 35,
        "content_production": 25,
    },
}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    @model_validator(mode="before")
    @classmethod
    def valid_unicode(cls, value):
        def check(item):
            if isinstance(item, str):
                if "\x00" in item:
                    raise ValueError("NUL is not allowed")
                item.encode("utf-8", errors="strict")
            elif isinstance(item, dict):
                for key, child in item.items():
                    check(key)
                    check(child)
            elif isinstance(item, list):
                for child in item:
                    check(child)

        try:
            check(value)
        except UnicodeEncodeError as error:
            raise ValueError("Invalid Unicode") from error
        return value


class Option(Model):
    id: UUID
    label: str = Field(min_length=1, max_length=200)


class QuestionConstraints(Model):
    min_length: int | None = Field(default=None, ge=0, le=10000, strict=True)
    max_length: int | None = Field(default=None, ge=0, le=10000, strict=True)
    min_value: FiniteFloat | None = None
    max_value: FiniteFloat | None = None
    min_items: int | None = Field(default=None, ge=0, le=20, strict=True)
    max_items: int | None = Field(default=None, ge=0, le=20, strict=True)
    max_files: int | None = Field(default=None, ge=0, le=5, strict=True)
    max_bytes: int | None = Field(default=None, ge=1, le=10485760, strict=True)
    allowed_media_types: (
        list[Literal["application/pdf", "image/png", "image/jpeg"]] | None
    ) = Field(default=None, max_length=3)


class Question(Model):
    id: UUID
    type: Literal[
        "short_text",
        "long_text",
        "email",
        "number",
        "date",
        "single_choice",
        "multiple_choice",
        "url",
        "file",
    ]
    label: str = Field(max_length=200)
    help: str | None = Field(default=None, max_length=1000)
    required: StrictBool
    position: int = Field(ge=0, le=49, strict=True)
    options: list[Option] = Field(default_factory=list, max_length=20)
    constraints: QuestionConstraints

    @model_validator(mode="after")
    def compatible(self):
        allowed = {
            "short_text": {"min_length", "max_length"},
            "long_text": {"min_length", "max_length"},
            "email": set(),
            "url": set(),
            "date": set(),
            "number": {"min_value", "max_value"},
            "single_choice": set(),
            "multiple_choice": {"min_items", "max_items"},
            "file": {"max_files", "max_bytes", "allowed_media_types"},
        }
        fields = {k for k, v in self.constraints.model_dump().items() if v is not None}
        if not fields <= allowed[self.type]:
            raise ValueError("Constraints incompatible with question type")
        if self.type not in ("single_choice", "multiple_choice") and self.options:
            raise ValueError("Options require a choice question")
        if len({o.id for o in self.options}) != len(self.options):
            raise ValueError("Duplicate options")
        for prefix in ("length", "value", "items"):
            low = getattr(self.constraints, "min_" + prefix)
            high = getattr(self.constraints, "max_" + prefix)
            if low is not None and high is not None and low > high:
                raise ValueError("Reversed bounds")
        if self.type == "short_text" and any(
            value is not None and value > 500
            for value in (self.constraints.min_length, self.constraints.max_length)
        ):
            raise ValueError("Short text cannot exceed 500 characters")
        return self


class DateCondition(Model):
    kind: Literal["available_by_date"]
    question_id: UUID
    date: date


class SlotsCondition(Model):
    kind: Literal["available_slots"]
    question_id: UUID
    option_ids: list[UUID] = Field(min_length=1, max_length=20)


ConditionRule = Annotated[DateCondition | SlotsCondition, Field(discriminator="kind")]


class Requirement(Model):
    id: UUID
    family: str = Field(max_length=100)
    expectation: str = Field(max_length=2000)
    importance: Literal["required", "desired"]
    evaluation_mode: Literal["qualitative", "deterministic"]
    assessment_mode: Literal["automatic", "manual"] | None = None
    source_question_ids: list[UUID] = Field(max_length=50)
    condition_rule: ConditionRule | None = None

    @model_validator(mode="after")
    def unique_sources(self):
        if len(set(self.source_question_ids)) != len(self.source_question_ids):
            raise ValueError("Duplicate sources")
        if self.evaluation_mode == "qualitative" and self.condition_rule:
            raise ValueError("Qualitative condition rule")
        if self.evaluation_mode == "deterministic" and self.assessment_mode:
            raise ValueError("Condition assessment mode")
        return self


class DraftConfiguration(Model):
    type: Literal["training", "recruitment"]
    title: str = Field(max_length=200)
    domain: str = Field(max_length=200)
    description: str = Field(max_length=10000)
    target_level: str = Field(max_length=500)
    deadline: datetime | None
    requirements: list[Requirement] = Field(max_length=20)
    questions: list[Question] = Field(max_length=50)

    @model_validator(mode="after")
    def consistent(self):
        if self.deadline and (
            self.deadline.tzinfo is None or self.deadline.utcoffset() is None
        ):
            raise ValueError("Deadline requires timezone")
        ids = {q.id for q in self.questions}
        if len(ids) != len(self.questions) or len(
            {q.position for q in self.questions}
        ) != len(self.questions):
            raise ValueError("Duplicate question id or position")
        if len({r.id for r in self.requirements}) != len(self.requirements):
            raise ValueError("Duplicate requirement id")
        for requirement in self.requirements:
            if not set(requirement.source_question_ids) <= ids:
                raise ValueError("Unknown question source")
            if (
                requirement.condition_rule
                and requirement.condition_rule.question_id not in ids
            ):
                raise ValueError("Unknown condition source")
        if self.deadline:
            self.deadline = self.deadline.astimezone(timezone.utc)
        self.questions.sort(key=lambda q: q.position)
        return self


class CampaignInput(Model):
    configuration: DraftConfiguration


class Campaign(Model):
    id: UUID
    state: Literal["draft", "published", "closed"]
    revision: int
    configuration: DraftConfiguration
    active_snapshot_id: UUID | None
    configuration_locked_at: datetime | None
    has_unpublished_changes: bool
    created_at: datetime
    public_url: str | None


class CampaignPage(Model):
    items: list[Campaign]
    next_cursor: str | None


class Preparation(Model):
    issues: list[ErrorDetail]


def preparation_issues(draft: DraftConfiguration) -> list[ErrorDetail]:
    issues = []

    def add(path, code):
        issues.append(ErrorDetail(path=path, code=code))

    for name in ("title", "domain", "description", "target_level"):
        if not getattr(draft, name).strip():
            add(name, "required")
    questions = {q.id: q for q in draft.questions}
    for i, q in enumerate(draft.questions):
        if not q.label.strip():
            add(f"questions.{i}.label", "required")
        if q.type in ("single_choice", "multiple_choice") and not q.options:
            add(f"questions.{i}.options", "required")
    for i, r in enumerate(draft.requirements):
        path = f"requirements.{i}"
        if not r.expectation.strip():
            add(path + ".expectation", "required")
        if not r.source_question_ids:
            add(path + ".source_question_ids", "missing_source")
        if r.evaluation_mode == "qualitative":
            if r.family not in FAMILIES[draft.type]:
                add(path + ".family", "unsupported_family")
            if not r.assessment_mode:
                add(path + ".assessment_mode", "required")
            if any(
                questions[q].type not in ("short_text", "long_text", "file", "url")
                for q in r.source_question_ids
            ):
                add(path + ".source_question_ids", "incompatible_source")
        else:
            rule = r.condition_rule
            if not rule:
                add(path + ".condition_rule", "required")
                continue
            q = questions[rule.question_id]
            if rule.question_id not in r.source_question_ids or r.family != rule.kind:
                add(path + ".condition_rule", "incompatible_source")
            if rule.kind == "available_by_date" and q.type != "date":
                add(path + ".condition_rule", "incompatible_source")
            if rule.kind == "available_slots" and (
                q.type != "multiple_choice"
                or len(set(rule.option_ids)) != len(rule.option_ids)
                or not set(rule.option_ids) <= {o.id for o in q.options}
            ):
                add(path + ".condition_rule", "incompatible_source")
    if not any(r.evaluation_mode == "qualitative" for r in draft.requirements):
        add("requirements", "qualitative_required")
    return issues
