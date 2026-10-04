import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID, uuid5

from talent_engine.integrations.public_web import WebFailure, normalize_url

from .github import collect_github, repository_url
from .ocr import transcribe_pages
from .portfolio import collect_portfolio

EXTRACTOR_VERSION = "pdf-text-v1+pypdf-6.19.0"


def extract_pdf(path, expected_hash, *, timeout=9):
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("pdf_child.py")),
                str(path),
                expected_hash,
            ],
            capture_output=True,
            timeout=timeout,
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
            if kind == "github":
                locator = dict(
                    kind="github",
                    repository=page["repository"],
                    commit=page["commit"],
                    path=page["path"],
                    start=start,
                    end=start + len(part),
                )
            elif kind == "portfolio":
                locator = dict(
                    kind="web", url=page["url"], start=start, end=start + len(part)
                )
            elif kind == "document":
                locator = dict(
                    kind="pdf",
                    page=page["page"],
                    start=start,
                    end=start + len(part),
                    method=page.get("method", "text"),
                )
            else:
                locator = dict(
                    kind="answer",
                    question_id=question_ids[0],
                    start=start,
                    end=start + len(part),
                )
            excerpts.append(
                dict(
                    id=str(uuid5(source_id, json.dumps(locator, sort_keys=True))),
                    source_version_id=str(source_id),
                    text=part,
                    locator=locator,
                    nature=page.get("nature", "declaration"),
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
        extraction_metadata=extraction.get("extraction_metadata", {"ocr": []}),
        excerpts=excerpts,
    )


def collect_sources(
    application_id,
    answers,
    documents,
    directory,
    *,
    ocr_gateway=None,
    retry_errors=False,
    portfolio_web=None,
    github_web=None,
):
    deadline = time.monotonic() + 50
    sources = []
    links = {}
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
        if external:
            is_github = False
            try:
                text = normalize_url(text)[0]
                from urllib.parse import urlsplit

                is_github = urlsplit(text).hostname == "github.com"
                if is_github:
                    try:
                        text = repository_url(text)
                    except WebFailure:
                        pass
            except WebFailure:
                pass
            key = digest(text)
            if key in links:
                links[key]["question_ids"] = sorted(
                    set(links[key]["question_ids"] + [qid])
                )
                continue
            extraction = (collect_github if is_github else collect_portfolio)(
                text,
                deadline=deadline,
                web=github_web if is_github else portfolio_web,
                retry_errors=retry_errors,
            )
            source = make_source(
                application_id,
                ("github:" if is_github else "portfolio:") + key,
                "github" if is_github else "portfolio",
                extraction.pop("content_hash"),
                [qid],
                extraction,
                version="github-api-v1" if is_github else "portfolio-html-v1",
            )
            links[key] = source
            sources.append(source)
            continue
        extraction = dict(
            state="available",
            error_code=None,
            pages=[dict(page=None, text=text)],
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
        remaining = deadline - time.monotonic()
        if remaining < 1:
            extraction = dict(
                state="unavailable",
                error_code="source_budget_exceeded",
                pages=[],
                ocr_pages=[],
            )
        elif document["media_type"] == "application/pdf":
            extraction = extract_pdf(
                Path(directory) / document["storage_key"],
                key,
                timeout=min(9, remaining),
            )
        else:
            extraction = dict(
                state="unavailable", error_code="ocr_required", pages=[], ocr_pages=[1]
            )
        if extraction["ocr_pages"]:
            extraction = transcribe_pages(
                Path(directory) / document["storage_key"],
                key,
                extraction,
                pdf=document["media_type"] == "application/pdf",
                gateway=ocr_gateway,
                deadline=deadline,
                retry_errors=retry_errors,
            )
        source = make_source(
            application_id,
            "document:" + key,
            "document",
            key,
            [str(document["question_id"])],
            extraction,
            upload_id=document["id"],
            version=EXTRACTOR_VERSION + "+ocr-v1",
        )
        unique[key] = source
        sources.append(source)
    return sources
