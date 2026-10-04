"""Deterministic semantic retrieval; cache writes only during fenced finalization."""

import hashlib
import json
import time
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from talent_engine.integrations.embeddings import Embeddings, normalized_vectors
from talent_engine.integrations.llm import ProviderFailure

from .assessment import EMAIL, EXPLICIT_ZERO, INSTRUCTION
from .repository import embedding_cache

VERSION = "evidence-retrieval-v1"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def identity(model, dimensions, *, version=VERSION):
    return digest(json.dumps([model, dimensions, version, "freellmapi-embeddings-v1"]))


def text_key(origin, text):
    return digest(json.dumps([origin, text], ensure_ascii=False))


def inputs_for(policy, config, evidence):
    criteria = [
        c
        for c in policy["criteria"]
        if c["weight"] is not None and c["assessment_mode"] == "automatic"
    ]
    qids = {q for c in criteria for q in c["source_question_ids"]}
    blocked = []
    omitted = []
    groups = defaultdict(list)
    for key, e in evidence.items():
        if not qids.intersection(e["question_ids"]):
            continue
        if INSTRUCTION.search(e["text"]):
            blocked.append(key)
            continue
        groups[str(e["source_version_id"])].append(key)
    # Round-robin avoids one long source consuming the entire candidate budget.
    candidates = []
    for offset in range(max((len(g) for g in groups.values()), default=0)):
        for group in groups.values():
            if offset < len(group):
                candidates.append(group[offset])
    # Prioritize explicit negative observations within the candidate cap.
    negative = [k for k in candidates if EXPLICIT_ZERO.search(evidence[k]["text"])]
    chosen = list(dict.fromkeys(negative + candidates))[:64]
    omitted = [k for k in candidates if k not in chosen]
    inputs = {}
    candidate_keys = {}
    for key in chosen:
        e = evidence[key]
        text = EMAIL.sub("[coordonnée masquée]", e["text"])
        cache_key = text_key(str(e["source_version_id"]), text)
        inputs[cache_key] = text
        candidate_keys[key] = cache_key
    requirements = {str(r["id"]): r["expectation"] for r in config["requirements"]}
    queries = {}
    for c in criteria:
        text = (
            requirements[c["criterion_id"]]
            + "\n"
            + json.dumps(c["levels"], ensure_ascii=False, sort_keys=True)
        )
        key = text_key("criterion:" + c["criterion_id"] + ":" + VERSION, text)
        inputs[key] = text
        queries[c["criterion_id"]] = dict(
            key=key, question_ids=c["source_question_ids"]
        )
    return inputs, queries, candidate_keys, blocked, omitted


def rank(queries, candidates, vectors, evidence):
    selected = []
    rankings = {}
    for cid, query in queries.items():
        relevant = [
            k
            for k in candidates
            if set(query["question_ids"]).intersection(evidence[k]["question_ids"])
        ]
        scores = {
            k: sum(
                a * b
                for a, b in zip(
                    vectors[query["key"]], vectors[candidates[k]], strict=True
                )
            )
            for k in relevant
        }
        ordered = sorted(relevant, key=lambda k: (-scores[k], k))
        chosen = list(
            dict.fromkeys(
                ordered[:3]
                + [k for k in ordered if EXPLICIT_ZERO.search(evidence[k]["text"])]
            )
        )
        rankings[cid] = [
            dict(evidence_id=k, similarity=round(scores[k], 6)) for k in chosen
        ]
        selected += chosen
    return list(dict.fromkeys(selected)), rankings


def cached(db, appid, cache_id, keys):
    return {
        r["input_hash"]: r["vector"]
        for r in db.execute(
            select(embedding_cache).where(
                (embedding_cache.c.application_id == appid)
                & (embedding_cache.c.identity == cache_id)
                & embedding_cache.c.input_hash.in_(keys)
            )
        ).mappings()
    }


def retrieve(engine, appid, policy, config, evidence, *, embedder=None):
    embedder = embedder or Embeddings()
    inputs, queries, candidates, blocked, omitted = inputs_for(policy, config, evidence)
    cache_id = identity(embedder.model, embedder.dimensions)
    with engine.connect() as db:
        vectors = cached(db, appid, cache_id, list(inputs))
    hits = len(vectors)
    pending = []
    providers = set()
    tokens = 0
    observed_tokens = True
    started = time.monotonic()
    deadline = started + 20
    missing = [key for key in inputs if key not in vectors]
    for index in range(0, len(missing), 16):
        if time.monotonic() >= deadline:
            raise ProviderFailure("retrieval_budget_exceeded")
        client = embedder
        if isinstance(embedder, Embeddings):
            client = Embeddings(
                embedder.settings.model_copy(
                    update={"timeout_seconds": min(20, deadline - time.monotonic())}
                )
            )
        keys = missing[index : index + 16]
        reply = client.embed([inputs[key] for key in keys])
        if reply.model != embedder.model or reply.dimensions != embedder.dimensions:
            raise ProviderFailure("embedding_response_invalid")
        normalized = normalized_vectors(reply.vectors, embedder.dimensions)
        for key, vector in zip(keys, normalized, strict=True):
            vectors[key] = vector
            pending.append(dict(input_hash=key, vector=vector))
        if reply.provider:
            providers.add(reply.provider)
        if reply.input_tokens is None:
            observed_tokens = False
        else:
            tokens += reply.input_tokens
    if time.monotonic() > deadline:
        raise ProviderFailure("retrieval_budget_exceeded")
    # Cached data follows the same finite vector validation as provider data.
    vectors = dict(
        zip(
            vectors,
            normalized_vectors(list(vectors.values()), embedder.dimensions),
            strict=True,
        )
    )
    selected, rankings = rank(queries, candidates, vectors, evidence)
    return dict(
        version=VERSION,
        model=embedder.model,
        dimensions=embedder.dimensions,
        identity=cache_id,
        providers=sorted(providers),
        input_tokens=tokens if observed_tokens else None,
        duration_seconds=round(time.monotonic() - started, 6),
        cache_hits=hits,
        cache_misses=len(missing),
        selected_ids=selected,
        rankings=rankings,
        blocked_ids=blocked,
        omitted_ids=omitted + [k for k in candidates if k not in selected],
        query_hashes={cid: q["key"] for cid, q in queries.items()},
    ), pending


def persist_and_verify(db, appid, policy, config, evidence, metadata, pending):
    if metadata["version"] != VERSION or metadata["identity"] != identity(
        metadata["model"], metadata["dimensions"]
    ):
        raise ValueError("Retrieval identity changed")
    inputs, queries, candidates, blocked, omitted = inputs_for(policy, config, evidence)
    vectors = cached(db, appid, metadata["identity"], list(inputs))
    if len(pending) > 84 or len({r["input_hash"] for r in pending}) != len(pending):
        raise ValueError("Invalid pending embeddings")
    for row in pending:
        if row["input_hash"] not in inputs:
            raise ValueError("Foreign embedding input")
        vectors[row["input_hash"]] = row["vector"]
    if set(vectors) != set(inputs):
        raise ValueError("Missing embedding input")
    vectors = dict(
        zip(
            vectors,
            normalized_vectors(list(vectors.values()), metadata["dimensions"]),
            strict=True,
        )
    )
    selected, rankings = rank(queries, candidates, vectors, evidence)
    if (
        selected != metadata["selected_ids"]
        or rankings != metadata["rankings"]
        or blocked != metadata["blocked_ids"]
        or omitted + [k for k in candidates if k not in selected]
        != metadata["omitted_ids"]
        or {cid: q["key"] for cid, q in queries.items()} != metadata["query_hashes"]
    ):
        raise ValueError("Retrieval changed")
    return selected


def persist(db, appid, metadata, pending):
    # Only after retrieval, assessment and provenance validation all pass.
    for row in pending:
        db.execute(
            insert(embedding_cache)
            .values(
                application_id=appid,
                identity=metadata["identity"],
                input_hash=row["input_hash"],
                vector=row["vector"],
            )
            .on_conflict_do_nothing()
        )
