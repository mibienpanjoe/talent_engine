import base64
import hashlib
import json
import time
from uuid import uuid4

import pytest
from talent_engine.integrations.public_web import Page, WebFailure
from talent_engine.sources.extraction import collect_sources
from talent_engine.sources.github import collect_github, repository_url


class GitHub:
    def __init__(self, *, private=False, size=33, failure=None):
        self.calls = []
        self.private, self.size, self.failure = private, size, failure

    def get(self, url, **kwargs):
        self.calls.append(url)
        if self.failure:
            raise self.failure
        if url.endswith("/repos/demo/project"):
            data = dict(
                private=self.private, full_name="demo/project", default_branch="main"
            )
        elif "/commits/" in url:
            data = dict(sha="a" * 40, commit=dict(tree=dict(sha="b" * 40)))
        elif "/git/trees/" in url:
            data = dict(
                truncated=False,
                tree=[
                    dict(
                        path="README.md",
                        type="blob",
                        mode="100644",
                        size=self.size,
                        sha=hashlib.sha1(
                            b"blob 33\0Projet fictif, equipe collective."
                        ).hexdigest(),
                    )
                ],
            )
        else:
            body = b"Projet fictif, equipe collective."
            data = dict(
                type="file",
                path="README.md",
                encoding="base64",
                size=len(body),
                sha=hashlib.sha1(
                    b"blob " + str(len(body)).encode() + b"\0" + body
                ).hexdigest(),
                content=base64.b64encode(body).decode(),
            )
        return Page(
            url, 200, {"content-type": "application/json"}, json.dumps(data).encode()
        )


def test_repository_is_pinned_and_project_repetition_is_deduplicated(tmp_path):
    web = GitHub()
    qids = [str(uuid4()) for _ in range(3)]
    result = collect_sources(
        uuid4(),
        [
            dict(question_id=q, kind="url", value=u)
            for q, u in zip(
                qids,
                [
                    "https://github.com/demo/project",
                    "https://github.com/DEMO/project.git",
                    "https://github.com/demo/project/",
                ],
            )
        ],
        [],
        tmp_path,
        github_web=web,
    )
    assert len(result) == 1 and set(result[0]["question_ids"]) == set(qids)
    source = result[0]
    assert source["kind"] == "github" and source["state"] == "available"
    assert source["excerpts"][0]["locator"]["commit"] == "a" * 40
    assert source["extraction_metadata"]["github"]["personal_role_verified"] is False
    assert "?ref=" + "a" * 40 in web.calls[-1]


@pytest.mark.parametrize(
    "web,code",
    [
        (GitHub(private=True), "github_private"),
        (GitHub(size=1048577), "github_file_limit"),
        (GitHub(failure=WebFailure("source_http_error")), "source_http_error"),
        (
            GitHub(
                failure=WebFailure(
                    "source_rate_limited", retryable=True, retry_after=60
                )
            ),
            "source_rate_limited",
        ),
    ],
)
def test_private_missing_quota_and_oversize_are_explicit(web, code):
    result = collect_github(
        "https://github.com/demo/project", deadline=time.monotonic() + 5, web=web
    )
    assert result["error_code"] == code and not result["pages"]
    assert (
        all("/contents/" not in u for u in web.calls)
        if code == "github_file_limit"
        else True
    )


@pytest.mark.parametrize(
    "value",
    [
        "https://github.com/demo",
        "https://github.com/demo/project/blob/main/x",
        "https://github.com/demo/../x",
        "https://evil.example/demo/project",
    ],
)
def test_only_supplied_repository_root_is_accepted(value):
    with pytest.raises(WebFailure):
        repository_url(value)


def test_modified_blob_and_symlinks_are_not_usable():
    class Tampered(GitHub):
        def get(self, url, **kwargs):
            page = super().get(url, **kwargs)
            data = json.loads(page.body)
            if "/contents/" in url:
                data["content"] = base64.b64encode(b"Tampered").decode()
            return Page(url, 200, page.headers, json.dumps(data).encode())

    result = collect_github(
        "https://github.com/demo/project", deadline=time.monotonic() + 5, web=Tampered()
    )
    assert not result["pages"] and result["error_code"] == "github_content_changed"


def test_git_api_redirect_cannot_leave_allowed_host():
    import socket

    from talent_engine.integrations.public_web import PublicWeb

    web = PublicWeb(
        allowed_hosts={"api.github.com"},
        resolver=lambda *a: [("8.8.8.8", socket.AF_INET)],
        exchange=lambda *a: (302, {"location": "https://example.com/"}, b""),
    )
    with pytest.raises(WebFailure, match="url_blocked"):
        web.get(
            "https://api.github.com/repos/demo/project", deadline=time.monotonic() + 5
        )
