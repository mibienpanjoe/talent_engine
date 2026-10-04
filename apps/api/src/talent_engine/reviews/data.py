"""Transaction-bound review schema and projected evaluation read model."""

from sqlalchemy import case, select
from talent_engine.evaluations.data import evaluations as bases

from .repository import events, projections

# A corrected partial score is NULL: COALESCE would restore the base score.
evaluations = (
    select(
        *[
            case(
                (projections.c.evaluation_id.is_not(None), projections.c[c.name]),
                else_=c,
            ).label(c.name)
            if c.name in projections.c
            and c.name not in {"application_id", "evaluation_id"}
            else c
            for c in bases.c
        ]
    )
    .select_from(
        bases.outerjoin(
            projections,
            (projections.c.evaluation_id == bases.c.id)
            & (projections.c.application_id == bases.c.application_id),
        )
    )
    .subquery("projected_evaluations")
)
__all__ = ["evaluations", "projections", "events"]
