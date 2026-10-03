from uuid import uuid4

import pytest
from pydantic import ValidationError
from talent_engine.campaigns.schemas import DraftConfiguration, preparation_issues


def configuration():
    question = str(uuid4())
    return dict(
        type="training",
        title="Formation",
        domain="Développement",
        description="Bases",
        target_level="Débutant",
        deadline=None,
        questions=[
            dict(
                id=question,
                type="long_text",
                label="Expliquez votre projet",
                required=True,
                position=0,
                options=[],
                constraints={},
            )
        ],
        requirements=[
            dict(
                id=str(uuid4()),
                family="practical_work",
                expectation="Projet personnel",
                importance="desired",
                evaluation_mode="qualitative",
                assessment_mode="automatic",
                source_question_ids=[question],
                condition_rule=None,
            )
        ],
    )


def test_unknown_family_is_saved_but_reported():
    data = configuration()
    data["requirements"][0]["family"] = "unknown"
    draft = DraftConfiguration.model_validate(data)
    assert any(x.code == "unsupported_family" for x in preparation_issues(draft))


def test_question_constraints_and_references_are_validated():
    data = configuration()
    data["questions"][0]["constraints"] = {"min_value": 2}
    with pytest.raises(ValidationError):
        DraftConfiguration.model_validate(data)
    data = configuration()
    data["requirements"][0]["source_question_ids"] = [str(uuid4())]
    with pytest.raises(ValidationError):
        DraftConfiguration.model_validate(data)


def test_incomplete_draft_retains_missing_sources():
    data = configuration()
    data["requirements"][0]["source_question_ids"] = []
    assert any(
        x.code == "missing_source"
        for x in preparation_issues(DraftConfiguration.model_validate(data))
    )
