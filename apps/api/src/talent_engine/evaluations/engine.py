"""Pure exact calculation. A model cannot supply weights, scores or conditions."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

UNKNOWN = {"insufficient_information", "conflicting_information", "source_unavailable"}


def rational(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def exact(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def decimal(value):
    with localcontext() as context:
        context.prec = 80
        return str(
            (Decimal(value.numerator) / Decimal(value.denominator)).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP
            )
        )


def calculate(policy, assessments):
    criteria = [c for c in policy["criteria"] if c["weight"] is not None]
    by_id = {a["criterion_id"]: a for a in assessments}
    if len(by_id) != len(assessments) or set(by_id) != {
        c["criterion_id"] for c in criteria
    }:
        raise ValueError("Exactly one assessment per qualitative criterion required")
    weights = [rational(c["weight"]) for c in criteria]
    if not weights or any(w <= 0 for w in weights) or sum(weights) != 100:
        raise ValueError("Invalid policy weights")
    coverage, lower = Fraction(0), Fraction(0)
    alerts = []
    complete = True
    for c, weight in zip(criteria, weights, strict=True):
        a = by_id[c["criterion_id"]]
        level, status = a["level"], a["status"]
        if status == "evaluated":
            if type(level) is not int or not 0 <= level <= 4:
                raise ValueError("Invalid assessed level")
            coverage += weight
            lower += weight * level / 4
        elif status not in UNKNOWN or level is not None:
            raise ValueError("Invalid unknown assessment")
        else:
            complete = False
        threshold = c["required_skill_threshold"]
        if threshold is not None and (level is None or level < threshold):
            alerts.append(
                dict(
                    criterion_id=c["criterion_id"],
                    code="required_skill_unknown"
                    if level is None
                    else "required_skill_below_threshold",
                )
            )
    upper = lower + 100 - coverage
    return dict(
        score=decimal(lower) if complete else None,
        score_exact=exact(lower) if complete else None,
        coverage=decimal(coverage),
        lower_bound=decimal(lower),
        upper_bound=decimal(upper),
        complete=complete,
        alerts=alerts,
    )


def conditions(configuration, answers):
    by_question = {}
    for answer in answers:
        by_question.setdefault(str(answer["question_id"]), []).append(answer)
    results = []
    for requirement in configuration["requirements"]:
        rule = requirement.get("condition_rule")
        if not rule:
            continue
        candidates = by_question.get(str(rule["question_id"]), [])
        status, value = "unknown", None
        if len(candidates) == 1:
            answer = candidates[0]
            value = answer["value"]
            if rule["kind"] == "available_by_date" and answer["kind"] == "date":
                status = (
                    "met"
                    if date.fromisoformat(value) <= date.fromisoformat(rule["date"])
                    else "unmet"
                )
            elif (
                rule["kind"] == "available_slots"
                and answer["kind"] == "multiple_choice"
            ):
                status = "met" if set(rule["option_ids"]) <= set(value) else "unmet"
        results.append(
            dict(
                criterion_id=str(requirement["id"]),
                question_id=str(rule["question_id"]),
                required=requirement["importance"] == "required",
                status=status,
                value=value,
                rationale="Réponse structurée comparée à la condition publiée."
                if status != "unknown"
                else "Réponse explicite absente ou contradictoire.",
            )
        )
    required = [r["status"] for r in results if r["required"]]
    eligibility = (
        "condition_unmet"
        if "unmet" in required
        else "needs_review"
        if "unknown" in required
        else "eligible"
        if required
        else "not_applicable"
    )
    return dict(eligibility=eligibility, results=results)


def views(calculation, eligibility):
    result = ["all"]
    if (
        calculation is None
        or not calculation["complete"]
        or eligibility == "needs_review"
        or calculation["alerts"]
    ):
        result.append("needs_review")
    elif eligibility in ("eligible", "not_applicable"):
        result.append("ready")
    if eligibility == "condition_unmet":
        result.append("condition_unmet")
    return result


def competition_ranks(scores):
    """Rank exact scores in the entire ready set, before decision filtering."""
    ordered = sorted(scores, key=scores.get, reverse=True)
    result, previous, rank = {}, None, 0
    for position, identifier in enumerate(ordered, 1):
        score = scores[identifier]
        if score != previous:
            rank = position
        result[identifier], previous = rank, score
    return result
