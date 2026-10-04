from uuid import uuid5

from talent_engine.campaigns.schemas import DraftConfiguration


def configuration(domain, campaign_id, mode):
    question_ids = [str(uuid5(campaign_id, "question:" + str(i))) for i in range(7)]
    questions = [
        dict(
            id=qid,
            type="long_text"
            if i < 3
            else "date"
            if i == 3
            else "file"
            if i == 4
            else "url",
            label=domain["questions"][i]
            if i < 3
            else [
                "Disponibilité au plus tard le 5 octobre 2026",
                "Documents justificatifs",
                "Portfolio public (facultatif)",
                "Dépôt GitHub choisi (facultatif)",
            ][i - 3],
            required=False,
            position=i,
            options=[],
            constraints={},
        )
        for i, qid in enumerate(question_ids)
    ]
    requirements = [
        dict(
            id=str(uuid5(campaign_id, "criterion:" + family)),
            family=family,
            expectation=domain["expectations"][i],
            importance="desired",
            evaluation_mode="qualitative",
            assessment_mode="automatic",
            source_question_ids=[question_ids[i], *question_ids[4:]],
        )
        for i, family in enumerate(domain["families"])
    ]
    requirements.append(
        dict(
            id=str(uuid5(campaign_id, "availability")),
            family="available_by_date",
            expectation="Disponible au plus tard le 5 octobre 2026",
            importance="required",
            evaluation_mode="deterministic",
            source_question_ids=[question_ids[3]],
            condition_rule=dict(
                kind="available_by_date", question_id=question_ids[3], date="2026-10-05"
            ),
        )
    )
    return DraftConfiguration(
        type=domain["type"],
        title=domain["title"]
        + " · "
        + ("préchargée" if mode == "preloaded" else "analyse réelle"),
        domain=domain["domain"],
        description=(
            "Tous les candidats et réponses de ce jeu sont fictifs. "
            "Les références publiques ajoutées en analyse réelle "
            "sont des sources distinctes à vérifier."
        ),
        target_level="Débutant" if domain["type"] == "training" else "Junior",
        deadline=None,
        questions=questions,
        requirements=requirements,
    ).model_dump(mode="json")
