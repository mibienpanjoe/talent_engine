"""Read-only review projection; exact ranks precede all user filters."""

from sqlalchemy import and_, case, func, literal, or_, select
from talent_engine.reviews.data import evaluations

from .repository import applications


def predicates(evaluation):
    exists = evaluation.c.id.is_not(None)
    complete = evaluation.c.calculation["complete"].as_boolean()
    alerts = func.coalesce(
        func.jsonb_array_length(evaluation.c.calculation["alerts"]), 0
    )
    ready = and_(
        exists,
        complete.is_(True),
        evaluation.c.eligibility.in_(["eligible", "not_applicable"]),
        alerts == 0,
    )
    needs = or_(
        ~exists,
        complete.is_not(True),
        evaluation.c.eligibility == "needs_review",
        alerts > 0,
    )
    return dict(
        all=literal(True),
        ready=ready,
        needs_review=needs,
        condition_unmet=and_(exists, evaluation.c.eligibility == "condition_unmet"),
    )


def real_rows(application, campaign_id):
    return and_(
        application.c.campaign_id == campaign_id,
        application.c.mode == "real",
        application.c.deleted_at.is_(None),
    )


def exact_rank(campaign_id):
    other_app = applications.alias("ready_application")
    other_eval = evaluations.alias("ready_evaluation")
    better = (
        other_eval.c.score_numerator * evaluations.c.score_denominator
        > evaluations.c.score_numerator * other_eval.c.score_denominator
    )
    count = (
        select(func.count())
        .select_from(
            other_app.join(
                other_eval, other_eval.c.id == other_app.c.effective_evaluation_id
            )
        )
        .where(
            real_rows(other_app, campaign_id), predicates(other_eval)["ready"], better
        )
        .correlate(applications, evaluations)
        .scalar_subquery()
    )
    return case((predicates(evaluations)["ready"], count + 1), else_=None)


def dataset(db, campaign):
    joined = applications.outerjoin(
        evaluations, evaluations.c.id == applications.c.effective_evaluation_id
    )
    filters = predicates(evaluations)
    base = real_rows(applications, campaign["id"])
    counters = (
        db.execute(
            select(
                *(
                    func.count().filter(predicate).label(key)
                    for key, predicate in filters.items()
                ),
                func.coalesce(func.sum(applications.c.processing_revision), 0).label(
                    "processing_revision"
                ),
            )
            .select_from(joined)
            .where(base)
        )
        .mappings()
        .one()
    )
    revision = (
        str(campaign["list_revision"]) + ":" + str(counters["processing_revision"])
    )
    return {k: counters[k] for k in filters}, revision


def listing(
    db,
    campaign,
    *,
    view="all",
    decision=None,
    processing_state=None,
    limit=25,
    offset=0,
):
    joined = applications.outerjoin(
        evaluations,
        (evaluations.c.id == applications.c.effective_evaluation_id)
        & (evaluations.c.application_id == applications.c.id),
    )
    filters = predicates(evaluations)
    base = real_rows(applications, campaign["id"])
    query = (
        select(
            applications,
            evaluations.c.calculation,
            evaluations.c.eligibility,
            evaluations.c.provenance["mode"].as_string().label("evaluation_mode"),
            exact_rank(campaign["id"]).label("rank")
            if view == "ready"
            else literal(None).label("rank"),
        )
        .select_from(joined)
        .where(base, filters[view])
    )
    if decision:
        query = query.where(applications.c.decision == decision)
    if processing_state:
        query = query.where(applications.c.processing_state == processing_state)
    if view == "ready":
        query = query.order_by("rank", applications.c.received_at, applications.c.id)
    else:
        query = query.order_by(applications.c.received_at.desc(), applications.c.id)
    rows = db.execute(query.offset(offset).limit(limit + 1)).mappings().all()
    return rows


def dossier_rank(db, row):
    if row["mode"] != "real":
        return None
    return db.scalar(
        select(exact_rank(row["campaign_id"]))
        .select_from(
            applications.outerjoin(
                evaluations, evaluations.c.id == applications.c.effective_evaluation_id
            )
        )
        .where(applications.c.id == row["id"])
    )
