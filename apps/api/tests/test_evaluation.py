import json
from fractions import Fraction
from pathlib import Path

import pytest
from talent_engine.evaluations.engine import calculate, competition_ranks, conditions

ORACLES = json.loads(
    (
        Path(__file__).parents[3] / "fixtures/expected-results/evaluation-cases.json"
    ).read_text()
)


def policy(weights=(40, 35, 25)):
    return {
        "criteria": [
            dict(
                criterion_id=str(i),
                weight=dict(numerator=str(w), denominator="1"),
                required_skill_threshold=None,
            )
            for i, w in enumerate(weights)
        ]
    }


def assessments(levels):
    return [
        dict(
            criterion_id=str(i),
            status="evaluated" if x is not None else "insufficient_information",
            level=x,
        )
        for i, x in enumerate(levels)
    ]


@pytest.mark.parametrize("case", ORACLES["cases"], ids=lambda c: c["name"])
def test_exact_oracles(case):
    result = calculate(policy(), assessments(case["levels"]))
    for key in ("score", "coverage", "lower_bound", "upper_bound"):
        expected = case["expected"][key]
        assert (
            result[key] is None
            if expected is None
            else Fraction(result[key]) == Fraction(expected)
        )


def test_explicit_zero_is_complete_and_unknown_is_not_zero():
    assert calculate(policy(), assessments([0, 0, 0]))["score"] == "0.000000"
    assert (
        calculate(policy(), assessments([None, None, None]))["upper_bound"]
        == "100.000000"
    )
    for bad in (True, -1, 5, 2.5):
        with pytest.raises(ValueError):
            calculate(policy(), assessments([bad, 2, 2]))
    with pytest.raises(ValueError):
        calculate(policy(), assessments([2, 2]))
    with pytest.raises(ValueError):
        calculate(policy(), assessments([2, 2, 2]) + assessments([2])[0:1])


def test_fractional_weights_and_exact_ranks():
    p = policy()
    p["criteria"][0]["weight"] = dict(numerator="160", denominator="3")
    p["criteria"][1]["weight"] = p["criteria"][2]["weight"] = dict(
        numerator="70", denominator="3"
    )
    result = calculate(p, assessments([4, 3, 2]))
    assert result["score_exact"] == dict(numerator="165", denominator="2")
    assert competition_ranks(
        {"a": Fraction(10), "b": Fraction(10), "c": Fraction(9)}
    ) == {"a": 1, "b": 1, "c": 3}
    assert competition_ranks({"a": Fraction(1, 3), "b": Fraction(333333, 1000000)}) == {
        "a": 1,
        "b": 2,
    }


def test_required_skills_and_conditions_are_independent():
    p = policy()
    p["criteria"][0]["required_skill_threshold"] = 2
    assert (
        calculate(p, assessments([1, 4, 4]))["alerts"][0]["code"]
        == "required_skill_below_threshold"
    )
    assert (
        calculate(p, assessments([None, 4, 4]))["alerts"][0]["code"]
        == "required_skill_unknown"
    )
    config = {
        "requirements": [
            dict(
                id="date",
                importance="required",
                condition_rule=dict(
                    kind="available_by_date", question_id="q", date="2026-10-05"
                ),
            ),
            dict(
                id="slots",
                importance="desired",
                condition_rule=dict(
                    kind="available_slots", question_id="s", option_ids=["one"]
                ),
            ),
        ]
    }
    result = conditions(
        config,
        [
            dict(question_id="q", kind="date", value="2026-10-06"),
            dict(question_id="s", kind="multiple_choice", value=[]),
        ],
    )
    assert result["eligibility"] == "condition_unmet"
    assert result["results"][1]["status"] == "unmet"
    assert conditions(config, [])["eligibility"] == "needs_review"
    assert (
        conditions(config, [dict(question_id="q", kind="date", value="2026-10-05")])[
            "eligibility"
        ]
        == "eligible"
    )
    assert conditions({"requirements": []}, [])["eligibility"] == "not_applicable"


def test_views_overlap_and_failed_analysis_does_not_change_effective_result():
    from talent_engine.evaluations.engine import views

    partial = calculate(policy(), assessments([4, None, 3]))
    assert views(partial, "condition_unmet") == [
        "all",
        "needs_review",
        "condition_unmet",
    ]
    assert views(calculate(policy(), assessments([4, 4, 3])), "condition_unmet") == [
        "all",
        "condition_unmet",
    ]
    assert views(calculate(policy(), assessments([3, 3, 4])), "eligible") == [
        "all",
        "ready",
    ]
    assert views(None, None) == ["all", "needs_review"]


@pytest.mark.parametrize(
    "status",
    ["insufficient_information", "conflicting_information", "source_unavailable"],
)
def test_unknown_states_preserve_bounds(status):
    values = assessments([4, None, 3])
    values[1]["status"] = status
    result = calculate(policy(), values)
    assert result["score"] is None and result["score_exact"] is None
    assert (result["coverage"], result["lower_bound"], result["upper_bound"]) == (
        "65.000000",
        "58.750000",
        "93.750000",
    )


def test_repeated_sources_have_no_effect_on_score_or_family_weight():
    from talent_engine.campaigns.policy import compile_policy
    from test_policy import draft

    p = compile_policy(draft())
    inputs = [
        dict(
            criterion_id=c["criterion_id"],
            status="evaluated",
            level=3,
            evidence_ids=["same-project"] * 3,
        )
        for c in p["criteria"]
    ]
    assert calculate(p, inputs)["score"] == "75.000000"
