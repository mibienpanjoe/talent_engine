# Talent Engine — Contrat d'évaluation

**Date :** 2026-10-03. **Statut :** référence T02 ; runtime non implémenté.
Voir [politiques/barèmes](policies-and-rubrics.md) pour la compilation.

## 1. Appréciation d'un critère

| Champ | Contrat |
| --- | --- |
| `criterion_id` | Identifiant d'exigence du snapshot évalué. |
| `status` | `evaluated`, `insufficient_information`, `conflicting_information` ou `source_unavailable`. |
| `level` | Entier 0–4 si `evaluated`, sinon `null`. Aucun nombre flottant, booléen ou niveau hors bornes. |
| `evidence_ids` | Références à des extraits de cette candidature, accessibles dans cette version d'analyse. Non vide si `evaluated`. |
| `rationale` | Justification lisible ; ne contient pas d'instructions autorisant des changements de politique. |
| `uncertainties` | Liste de limites/points à vérifier, éventuellement vide. |
| `policy_version`, `rubric_version` | Identiques aux références figées du snapshot ; jamais choisis par le modèle. |

Pour une inconnue, les extraits peuvent être vides (source inaccessible) ou
présents (information insuffisante/contradictoire). Un incident sur une source
n'empêche pas une appréciation si une autre source suffit ; l'incident reste
visible. Niveau zéro et absence d'information restent distincts.

Un extrait possède source, localisation, texte effectivement récupéré,
empreinte/version et nature (`declaration`, `contextual_explanation`,
`consultable_artifact`, `human_verification`). Une correction humaine peut
ajouter une note justificative liée au dossier ; elle n'invente pas un extrait
de CV. Chaque appréciation attendue apparaît une seule fois par évaluation.
Critère inconnu, référence étrangère/inexistante, politique modifiée ou sortie
non conforme sont rejetés et consignés comme échec technique de validation.
Jamais convertis en niveau zéro. Les références valides prouvent la provenance,
pas la pertinence de l'interprétation ; celle-ci exige une revue.

## 2. Calcul exact et projection

Les poids exacts totalisent 100. Pour les critères évalués E :

- `coverage = somme(w_i, i dans E)`.
- `lower_bound = somme(w_i × level_i / 4, i dans E)`.
- `upper_bound = lower_bound + 100 - coverage`.
- `score = lower_bound` uniquement si tous les critères sont évalués ; sinon `null`.

L'autorité de calcul utilise des rapports rationnels (poids de famille et
division entre exigences), sans arrondi intermédiaire. Les valeurs API de
score/bornes/couverture sont des chaînes décimales, arrondies à 6 décimales
(`ROUND_HALF_UP`) uniquement pour sérialisation ; `score_exact` expose
numérateur/dénominateur pour les tris et ex æquo. La couverture complète est
déterminée par les états des critères, pas par une valeur arrondie à 100.
L'interface affiche score à une décimale et couverture à une décimale au plus.
Un affichage identique ne crée pas une égalité mathématique ni un rang distinct
par arrondi. Le backend fournit le rang exact ; le frontend ne recalcule pas.

`0 ≤ lower_bound ≤ upper_bound ≤ 100` et `0 ≤ coverage ≤ 100`.
Pour une évaluation complète, les deux bornes égalent le score.
Les bornes sont des possibilités arithmétiques, sans probabilité. Elles restent
dans le détail ; la liste affiche « Évaluation partielle », couverture et
score absent. Aucun score final renormalisé à partir des seules données connues.

## 3. Admissibilité et alertes

Une condition indispensable est `met`, `unmet` ou `unknown`, avec réponse et
justification référencées. Le résultat global conserve tous les détails :

1. Une `unmet` → `condition_unmet`.
2. Sinon une `unknown` → `needs_review`.
3. Sinon conditions présentes et satisfaites → `eligible`.
4. Aucune condition indispensable → `not_applicable`.

Les alertes de compétences indispensables sont séparées conformément à la
politique. Une décision humaine n'efface jamais l'admissibilité ni une alerte.
L'état d'exécution (`queued` à `failed`) appartient au traitement, pas à ce
résultat. Le [contrat de revue](../review/review-and-corrections.md) définit
la projection effective et l'appartenance aux files en T03.

## 4. Oracles et contrôle

Les sept cas fictifs sont versionnés dans
[evaluation-cases.json](../../fixtures/expected-results/evaluation-cases.json).
Amina : 81,25 ; Boris : 65 ; Chloé : score `null`, couverture 65 et bornes
58,75–93,75 ; David : 93,75 et `condition_unmet` ; Fatou : 77,50 ; Karim :
76,25 ; Lina : score `null`, couverture 65 et bornes 55–90.

Tests à implémenter T19/T22 : inconnues/contradictions, référence absente ou
étrangère, niveau hors bornes, zéro explicite, même projet cité trois fois,
famille absente, famille partagée entre deux exigences, mêmes entrées donnant
le même calcul exact. Aucun oracle ne remplace une intégration en direct.
