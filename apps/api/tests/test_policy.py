from fractions import Fraction
from uuid import uuid4

import pytest
from talent_engine.campaigns.policy import compile_policy
from talent_engine.campaigns.schemas import DraftConfiguration
from talent_engine.errors import AccessError


def draft():
    q = str(uuid4())
    return DraftConfiguration.model_validate(
        dict(
            type="training",
            title="Test",
            domain="Dev",
            description="Test",
            target_level="Débutant",
            deadline=None,
            questions=[
                dict(
                    id=q,
                    type="long_text",
                    label="Projet",
                    required=False,
                    position=0,
                    constraints={},
                )
            ],
            requirements=[
                dict(
                    id=str(uuid4()),
                    family=f,
                    expectation=str(i),
                    importance="desired",
                    evaluation_mode="qualitative",
                    assessment_mode="automatic",
                    source_question_ids=[q],
                )
                for i, f in enumerate(
                    ["programming_foundations", "practical_work", "practical_work"]
                )
            ],
        )
    )


def test_policy_weights_are_exact_and_rubrics_complete():
    policy = compile_policy(draft())
    weights = [
        Fraction(int(c["weight"]["numerator"]), int(c["weight"]["denominator"]))
        for c in policy["criteria"]
    ]
    assert sum(weights) == 100
    assert weights == [Fraction(160, 3), Fraction(70, 3), Fraction(70, 3)]
    assert all(len(c["levels"]) == 5 for c in policy["criteria"])


def test_duplicate_expectation_and_unknown_family_block_publication():
    data = draft()
    data.requirements[2].expectation = data.requirements[1].expectation
    with pytest.raises(AccessError):
        compile_policy(data)
    data = draft()
    data.requirements[0].family = "unsupported"
    with pytest.raises(AccessError):
        compile_policy(data)
