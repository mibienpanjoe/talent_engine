import unicodedata
from fractions import Fraction

from talent_engine.errors import AccessError, ErrorDetail

from .schemas import FAMILIES, preparation_issues

RUBRICS = {
    "programming_foundations": {
        "version": "programming-v1",
        "levels": [
            (
                "Réponse explicite établissant que les prérequis demandés ne "
                "sont pas acquis."
            ),
            "Notions citées avec compréhension très partielle du cas demandé.",
            "Concepts de base expliqués sur un cas simple, lacunes identifiées.",
            "Raisonnement cohérent et étapes expliquées sur le cas.",
            (
                "Raisonnement cohérent, vérification et cas limites adaptés "
                "au niveau débutant."
            ),
        ],
    },
    "practical_work": {
        "version": "practice-v1",
        "levels": [
            (
                "Le candidat indique explicitement n'avoir réalisé aucun "
                "exercice/projet pertinent."
            ),
            "Exercice guidé décrit avec contribution limitée.",
            "Petite réalisation décrite avec rôle personnel identifiable.",
            "Réalisation avec contribution, choix et résultat décrits.",
            "Réalisation avec difficulté résolue et vérification du résultat.",
        ],
    },
    "learning_approach": {
        "version": "learning-v1",
        "levels": [
            (
                "Le candidat indique explicitement ne pouvoir fournir aucune "
                "démarche sur la période demandée."
            ),
            "Activité citée sans démarche détaillée.",
            "Objectif et ressources décrits, application peu détaillée.",
            "Difficulté, ressource et application concrète décrites.",
            "Essai, retour, ajustement et réutilisation décrits.",
        ],
    },
    "audience_understanding": {
        "version": "audience-v1",
        "levels": [
            (
                "Le candidat affirme ne pas savoir identifier une audience "
                "pour le cas demandé."
            ),
            "Audience citée sans besoin ni relation avec le message.",
            "Segment et besoin décrits, lien au message encore limité.",
            "Segment, besoin et choix de message/canal justifiés sur le cas.",
            (
                "Choix justifiés avec hypothèses, vérification proposée et "
                "ajustement selon retour."
            ),
        ],
    },
    "results_analysis": {
        "version": "results-v1",
        "levels": [
            (
                "Réponse explicite établissant que les indicateurs demandés "
                "ne sont pas interprétables par le candidat."
            ),
            "Indicateurs cités sans interprétation utile.",
            "Indicateurs reliés à un objectif, interprétation limitée.",
            "Résultats interprétés et proposition d'action cohérente.",
            "Comparaison contextualisée, limites et recommandation justifiée.",
        ],
    },
    "content_production": {
        "version": "content-v1",
        "levels": [
            (
                "Le candidat indique explicitement n'avoir produit aucun "
                "contenu pertinent."
            ),
            "Exemple guidé décrit, contribution limitée ou simplement reproduite.",
            "Contenu décrit/consultable avec rôle personnel et objectif identifiables.",
            (
                "Contenu personnel avec choix de format/message justifiés et "
                "résultat décrit."
            ),
            (
                "Choix justifiés, vérification auprès de l'audience et "
                "adaptation du contenu documentées."
            ),
        ],
    },
}


def compile_policy(draft):
    issues = preparation_issues(draft)
    seen = set()
    for i, r in enumerate(draft.requirements):
        key = (
            r.family,
            " ".join(unicodedata.normalize("NFKC", r.expectation).casefold().split()),
        )
        if key in seen:
            issues.append(
                ErrorDetail(
                    path=f"requirements.{i}.expectation", code="duplicate_expectation"
                )
            )
        seen.add(key)
    if issues:
        raise AccessError(
            422, "preparation_failed", "Complete campaign preparation", details=issues
        )
    qualitative = [r for r in draft.requirements if r.evaluation_mode == "qualitative"]
    present = {r.family for r in qualitative}
    total = sum(FAMILIES[draft.type][f] for f in present)
    criteria = []
    for r in draft.requirements:
        if r.evaluation_mode == "qualitative":
            weight = Fraction(
                100 * FAMILIES[draft.type][r.family],
                total * sum(x.family == r.family for x in qualitative),
            )
            rubric = RUBRICS[r.family]
            criteria.append(
                dict(
                    criterion_id=str(r.id),
                    family=r.family,
                    weight=dict(
                        numerator=str(weight.numerator),
                        denominator=str(weight.denominator),
                    ),
                    rubric_version=rubric["version"],
                    levels=rubric["levels"],
                    required_skill_threshold=2 if r.importance == "required" else None,
                    assessment_mode=r.assessment_mode,
                    source_question_ids=[str(x) for x in r.source_question_ids],
                    condition_rule=None,
                )
            )
        else:
            criteria.append(
                dict(
                    criterion_id=str(r.id),
                    family=r.family,
                    weight=None,
                    rubric_version=None,
                    levels=[],
                    required_skill_threshold=None,
                    assessment_mode=None,
                    source_question_ids=[str(x) for x in r.source_question_ids],
                    condition_rule=r.condition_rule.model_dump(mode="json"),
                )
            )
    return dict(
        version=draft.type + "-demo-v1",
        present_families=sorted(present),
        absent_families=sorted(set(FAMILIES[draft.type]) - present),
        criteria=criteria,
    )
