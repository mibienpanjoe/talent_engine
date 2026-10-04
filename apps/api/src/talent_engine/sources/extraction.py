import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid5

EXTRACTOR_VERSION = "pdf-text-v1+pypdf-6.19.0"


def extract_pdf(path, expected_hash):
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("pdf_child.py")),
                str(path),
                expected_hash,
            ],
            capture_output=True,
            timeout=9,
            env={"PATH": os.defpath},
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, ValueError):
        return dict(
            state="unreadable",
            error_code="pdf_extraction_failed",
            pages=[],
            ocr_pages=[],
        )


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def make_source(
    application_id,
    key,
    kind,
    content_hash,
    question_ids,
    extraction,
    *,
    upload_id=None,
    version=EXTRACTOR_VERSION,
):
    source_id = uuid5(
        UUID(str(application_id)),
        key
        + ":"
        + content_hash
        + ":"
        + version
        + ":"
        + digest(json.dumps(extraction, ensure_ascii=False, sort_keys=True)),
    )
    excerpts = []
    for page in extraction["pages"]:
        text = page["text"]
        for start in range(0, len(text), 2000):
            part = text[start : start + 2000]
            if not part.strip():
                continue
            locator = (
                dict(kind="pdf", page=page["page"], start=start, end=start + len(part))
                if kind == "document"
                else dict(
                    kind="answer",
                    question_id=question_ids[0],
                    start=start,
                    end=start + len(part),
                )
            )
            excerpts.append(
                dict(
                    id=str(uuid5(source_id, json.dumps(locator, sort_keys=True))),
                    source_version_id=str(source_id),
                    text=part,
                    locator=locator,
                    nature="declaration",
                    excerpt_hash=digest(part),
                )
            )
    return dict(
        id=str(source_id),
        source_key=key,
        kind=kind,
        content_hash=content_hash,
        text_hash=digest(
            json.dumps(extraction["pages"], ensure_ascii=False, sort_keys=True)
        ),
        question_ids=question_ids,
        upload_id=str(upload_id) if upload_id else None,
        extractor_version=version,
        state=extraction["state"],
        error_code=extraction["error_code"],
        ocr_pages=extraction["ocr_pages"],
        pages=extraction["pages"],
        excerpts=excerpts,
    )


def collect_sources(application_id, answers, documents, directory):
    sources = []
    for answer in answers:
        if answer["kind"] in ("file", "email"):
            continue
        text = (
            answer["value"]
            if isinstance(answer["value"], str)
            else json.dumps(answer["value"], ensure_ascii=False, sort_keys=True)
        )
        qid = str(answer["question_id"])
        external = answer["kind"] == "url"
        extraction = dict(
            state="unavailable" if external else "available",
            error_code="external_retrieval_pending" if external else None,
            pages=[] if external else [dict(page=None, text=text)],
            ocr_pages=[],
        )
        sources.append(
            make_source(
                application_id,
                "answer:" + qid,
                "answer",
                digest(text),
                [qid],
                extraction,
                version="answer-text-v1",
            )
        )
    unique = {}
    for document in documents:
        key = document["sha256"]
        if key in unique:
            unique[key]["question_ids"] = sorted(
                set(unique[key]["question_ids"] + [str(document["question_id"])])
            )
            continue
        if document["media_type"] == "application/pdf":
            extraction = extract_pdf(Path(directory) / document["storage_key"], key)
        else:
            extraction = dict(
                state="unavailable", error_code="ocr_required", pages=[], ocr_pages=[1]
            )
        source = make_source(
            application_id,
            "document:" + key,
            "document",
            key,
            [str(document["question_id"])],
            extraction,
            upload_id=document["id"],
        )
        unique[key] = source
        sources.append(source)
    return sources
