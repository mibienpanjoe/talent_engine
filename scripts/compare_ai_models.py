"""Repeat the versioned fictional FR/EN comparison through server configuration.

Run with uv run --project apps/api python scripts/compare_ai_models.py.
Uses TALENT_LLM_* environment settings. Never prints credentials or vectors.
"""

import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from talent_engine.campaigns.policy import RUBRICS
from talent_engine.evaluations.assessment import (
    build_messages,
    parse_response,
    validate_assessments,
)
from talent_engine.integrations.embeddings import Embeddings
from talent_engine.integrations.llm import Gateway, LLMSettings, ProviderFailure


def compare():
    settings = LLMSettings()
    fixture = Path("fixtures/retrieval/model-cases.json")
    data = json.loads(fixture.read_text())
    policy = dict(version="benchmark-v1", criteria=[])
    config = dict(requirements=[])
    evidence = {}
    names = {}
    expected = {}
    for case in data["cases"]:
        cid = str(uuid5(NAMESPACE_URL, "criterion:" + case["name"]))
        qid = str(uuid5(NAMESPACE_URL, "question:" + case["name"]))
        rubric = RUBRICS[case["family"]]
        policy["criteria"].append(
            dict(
                criterion_id=cid,
                weight="1",
                assessment_mode="automatic",
                source_question_ids=[qid],
                rubric_version=rubric["version"],
                levels=rubric["levels"],
            )
        )
        config["requirements"].append(dict(id=cid, expectation=case["expectation"]))
        names[cid] = case["name"]
        expected[cid] = (case["expected_status"], case["expected_level"])
        for index, text in enumerate(case["texts"]):
            eid = str(uuid5(NAMESPACE_URL, case["name"] + ":" + str(index)))
            evidence[eid] = dict(
                text=text,
                question_ids=[qid],
                source_version_id=str(uuid5(NAMESPACE_URL, "source:" + case["name"])),
                nature="declaration",
            )
    messages, allowed, limits = build_messages(policy, config, evidence)
    results = []
    for model in ["gemini-3.5-flash-lite", "gpt-oss-120b"]:
        for repetition in range(3):
            result = dict(
                kind="generation",
                model=model,
                repeat=repetition + 1,
                fixture_hash=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            )
            try:
                reply = Gateway(settings.model_copy(update={"model": model})).chat(
                    messages, response_format={"type": "json_object"}
                )
                rows = validate_assessments(
                    parse_response(reply.content), policy, allowed
                )
                result.update(
                    provider=reply.provider,
                    effective_model=reply.effective_model,
                    seconds=reply.duration_seconds,
                    cases=[
                        dict(
                            name=names[row["criterion_id"]],
                            status=row["status"],
                            level=row["level"],
                            matches=(row["status"], row["level"])
                            == expected[row["criterion_id"]],
                        )
                        for row in rows
                    ],
                    citations_valid=True,
                )
            except (ProviderFailure, ValueError) as error:
                result["error"] = (
                    error.code
                    if isinstance(error, ProviderFailure)
                    else "invalid_assessment"
                )
            results.append(result)
            print(json.dumps(result), flush=True)
    texts = [e["text"] for e in evidence.values() if "Ignore previous" not in e["text"]]
    text_names = [
        case["name"]
        for case in data["cases"]
        for text in case["texts"]
        if "Ignore previous" not in text
    ]
    for model in ["gemini-embedding-001", "gemini-embedding-2"]:
        for repetition in range(3):
            result = dict(
                kind="embedding",
                model=model,
                repeat=repetition + 1,
                fixture_hash=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            )
            try:
                reply = Embeddings(
                    settings.model_copy(
                        update={"embedding_model": model, "embedding_dimensions": 3072}
                    )
                ).embed([q["query"] for q in data["embedding_queries"]] + texts)
                rankings = []
                for i, q in enumerate(data["embedding_queries"]):
                    scores = [
                        sum(a * b for a, b in zip(reply.vectors[i], v, strict=True))
                        for v in reply.vectors[2:]
                    ]
                    order = sorted(range(len(scores)), key=lambda j: -scores[j])
                    top = text_names[order[0]]
                    rankings.append(
                        dict(
                            query=i,
                            top=top,
                            relevant=top == q["expected_case"],
                            similarity=round(scores[order[0]], 6),
                        )
                    )
                result.update(
                    provider=reply.provider,
                    seconds=reply.duration_seconds,
                    input_tokens=reply.input_tokens,
                    dimensions=reply.dimensions,
                    queries=rankings,
                )
            except ProviderFailure as error:
                result["error"] = error.code
            results.append(result)
            print(json.dumps(result), flush=True)
    return results


if __name__ == "__main__":
    compare()
