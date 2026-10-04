import hashlib
import json
from decimal import Decimal

from talent_engine.campaigns.schemas import DraftConfiguration
from talent_engine.errors import AccessError, ErrorDetail


def validate_answers(payload, configuration):
    questions = {
        q.id: q for q in DraftConfiguration.model_validate(configuration).questions
    }
    seen = set()
    issues = []
    for i, answer in enumerate(payload.answers):
        q = questions.get(answer.question_id)
        code = None
        if answer.question_id in seen:
            code = "duplicate_answer"
        seen.add(answer.question_id)
        if not q:
            code = "unknown_question"
        elif q.type != answer.kind:
            code = "answer_type_mismatch"
        else:
            value = answer.value
            c = q.constraints
            if q.type in ("short_text", "long_text") and (
                len(value) < (c.min_length or 0)
                or len(value)
                > (
                    c.max_length
                    if c.max_length is not None
                    else (500 if q.type == "short_text" else 10000)
                )
                or (q.required and not value.strip())
            ):
                code = "invalid_length"
            if q.type == "number" and (
                (c.min_value is not None and value < c.min_value)
                or (c.max_value is not None and value > c.max_value)
            ):
                code = "out_of_range"
            if q.type == "single_choice" and value not in {o.id for o in q.options}:
                code = "unknown_option"
            if q.type == "multiple_choice" and (
                not set(value) <= {o.id for o in q.options}
                or len(value) < (c.min_items or 0)
                or len(value) > (c.max_items if c.max_items is not None else 20)
            ):
                code = "invalid_choices"
            if q.type == "file" and (
                len(set(value)) != len(value)
                or len(value) > (c.max_files if c.max_files is not None else 5)
            ):
                code = "invalid_files"
            if q.required and value == []:
                code = "required"
        if code:
            issues.append(ErrorDetail(path=f"answers.{i}", code=code))
    for q in questions.values():
        if q.required and q.id not in seen:
            issues.append(ErrorDetail(path=f"questions.{q.id}", code="required"))
    if sum(a.kind == "url" for a in payload.answers) > 5:
        issues.append(ErrorDetail(path="answers", code="too_many_links"))
    if issues:
        raise AccessError(
            422, "validation_error", "Check application answers", details=issues
        )


def canonical_payload(payload, files=None):
    answers = []
    for answer in sorted(payload.answers, key=lambda a: str(a.question_id)):
        data = answer.model_dump(mode="json")
        if answer.kind == "multiple_choice":
            data["value"] = sorted(data["value"])
        if answer.kind == "number":
            data["value"] = {"decimal": str(Decimal(str(answer.value)).normalize())}
        if answer.kind == "file":
            data["value"] = [
                {k: item[k] for k in ("filename", "media_type", "bytes", "sha256")}
                for item in (files or {}).get(str(answer.question_id), [])
            ]
        answers.append(data)
    data = {
        "canonical_version": "submission-v1",
        "snapshot_id": str(payload.snapshot_id),
        "contact": payload.contact.model_dump(mode="json"),
        "answers": answers,
    }
    return hashlib.sha256(
        json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()
