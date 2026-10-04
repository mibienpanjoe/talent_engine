"""Official public API, immutable commit, bounded text files; no execution."""

import base64
import binascii
import hashlib
import json
import re
from datetime import UTC, datetime
from urllib.parse import quote, urlsplit

from talent_engine.integrations.public_web import PublicWeb, WebFailure, normalize_url

VERSION = "github-api-v1"
SHA = re.compile(r"[0-9a-f]{40}")
TEXT = {
    ".md",
    ".txt",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
}


def repository_url(value):
    normalized, host, _ = normalize_url(value)
    parts = urlsplit(normalized)
    match = re.fullmatch(r"/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)/?", parts.path)
    if host != "github.com" or parts.scheme != "https" or parts.query or not match:
        raise WebFailure("github_repository_url_required")
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    if owner in (".", "..") or repo in ("", ".", ".."):
        raise WebFailure("github_repository_url_required")
    return "https://github.com/" + owner.lower() + "/" + repo.lower()


def safe_path(path):
    return (
        isinstance(path, str)
        and 0 < len(path) <= 512
        and all(p not in ("", ".", "..") for p in path.split("/"))
        and not any(ord(c) < 32 or c == "\\" for c in path)
    )


def collect_github(value, *, deadline, web=None, retry_errors=False):
    pages, files, hashes = [], [], []
    snapshot = dict(
        repository=value,
        commit=None,
        fetched_at=datetime.now(UTC).isoformat(),
        personal_role_verified=False,
        files=files,
    )
    error_code = None
    try:
        canonical = repository_url(value)
        repo = canonical.removeprefix("https://github.com/")
        snapshot["repository"] = canonical
        api = "https://api.github.com/repos/" + repo
        web = web or PublicWeb(allowed_hosts={"api.github.com"})

        def get(path):
            page = web.get(api + path, deadline=deadline)
            if urlsplit(page.url).hostname != "api.github.com":
                raise WebFailure("url_blocked")
            try:
                result = json.loads(page.body)
                if not isinstance(result, dict):
                    raise ValueError()
                return result
            except (ValueError, UnicodeError):
                raise WebFailure("github_response_invalid") from None

        metadata = get("")
        if metadata.get("private") is not False:
            raise WebFailure("github_private")
        if str(metadata.get("full_name", "")).lower() != repo:
            raise WebFailure("github_repository_changed")
        branch = metadata.get("default_branch")
        if not isinstance(branch, str) or not 0 < len(branch) <= 255:
            raise WebFailure("github_response_invalid")
        commit = get("/commits/" + quote(branch, safe=""))
        sha = commit.get("sha", "")
        tree = commit.get("commit", {}).get("tree", {}).get("sha", "")
        if not SHA.fullmatch(sha) or not SHA.fullmatch(tree):
            raise WebFailure("github_response_invalid")
        snapshot["commit"] = sha
        listing = get("/git/trees/" + tree + "?recursive=1")
        entries = listing.get("tree")
        if (
            listing.get("truncated") is not False
            or not isinstance(entries, list)
            or len(entries) > 1000
        ):
            raise WebFailure("github_tree_limit")
        entries = [
            e
            for e in entries
            if isinstance(e, dict)
            and e.get("type") == "blob"
            and e.get("mode") in ("100644", "100755")
            and safe_path(e.get("path"))
            and "." + e["path"].rsplit(".", 1)[-1].lower() in TEXT
        ]
        entries.sort(
            key=lambda e: (
                0
                if e["path"].lower() in ("readme.md", "readme.txt")
                else 1
                if e["path"].startswith(("src/", "app/", "apps/", "tests/"))
                else 2,
                e["path"],
            )
        )
        readmes = [
            e for e in entries if e["path"].lower() in ("readme.md", "readme.txt")
        ][:1]
        chosen = readmes + [e for e in entries if e not in readmes][:5]
        total = 0
        for entry in chosen:
            path = entry["path"]
            record = dict(path=path, status="failed")
            files.append(record)
            try:
                size = entry.get("size")
                if type(size) is not int or size < 0:
                    raise WebFailure("github_response_invalid")
                if size > 1048576 or total + size > 3145728:
                    raise WebFailure("github_file_limit")
                data = get("/contents/" + quote(path, safe="/") + "?ref=" + sha)
                if (
                    data.get("type") != "file"
                    or data.get("path") != path
                    or data.get("encoding") != "base64"
                ):
                    raise WebFailure("github_response_invalid")
                content = data.get("content")
                if not isinstance(content, str) or len(content) > 1500000:
                    raise WebFailure("github_file_limit")
                body = base64.b64decode("".join(content.split()), validate=True)
                if len(body) > 1048576 or total + len(body) > 3145728:
                    raise WebFailure("github_file_limit")
                blob = hashlib.sha1(
                    b"blob " + str(len(body)).encode() + b"\0" + body
                ).hexdigest()
                if (
                    data.get("sha") != blob
                    or entry.get("sha") != blob
                    or len(body) != size
                ):
                    raise WebFailure("github_content_changed")
                if b"\0" in body:
                    raise WebFailure("github_binary_file")
                text = body.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
                if sum(len(p["text"]) for p in pages) + len(text) > 200000:
                    raise WebFailure("source_text_limit")
                total += len(body)
                digest = hashlib.sha256(body).hexdigest()
                hashes.append(digest)
                record.update(
                    status="succeeded",
                    content_hash=digest,
                    blob_sha=blob,
                    size=len(body),
                )
                if text.strip():
                    pages.append(
                        dict(
                            page=len(pages) + 1,
                            text=text,
                            path=path,
                            repository=canonical,
                            commit=sha,
                            nature="contextual_explanation"
                            if entry in readmes
                            else "consultable_artifact",
                        )
                    )
            except (UnicodeError, binascii.Error):
                record["error_code"] = "github_text_invalid"
            except WebFailure as error:
                if error.retryable and retry_errors:
                    raise
                record["error_code"] = error.code
        error_code = next(
            (r.get("error_code") for r in files if r.get("error_code")), None
        )
        if not pages and error_code is None:
            error_code = "source_text_unavailable"
    except WebFailure as error:
        if error.retryable and retry_errors:
            raise
        error_code = error.code
    except (TypeError, AttributeError):
        error_code = "github_response_invalid"
    return dict(
        state="available"
        if pages
        else "blocked"
        if error_code == "url_blocked"
        else "unavailable",
        error_code=error_code,
        pages=pages,
        ocr_pages=[],
        content_hash=hashlib.sha256("".join(hashes).encode()).hexdigest(),
        extraction_metadata=dict(ocr=[], web=[], source_url=value, github=snapshot),
    )
