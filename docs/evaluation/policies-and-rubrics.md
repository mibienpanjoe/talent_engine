# Talent Engine — Politiques et barèmes

**Date :** 2026-10-03. **Statut :** référence d'implémentation T02, non calibrée
sur des personnes réelles ; calcul backend et essais modèles à implémenter.

Choix détaillés arrêtés dans le cadre de la demande d'exécuter la phase
contrats, à partir de la [spécification source](evaluation-engine-spec.md).
Ils ne constituent pas une confirmation individuelle du mainteneur de chaque
seuil. La publication applique ce contrat ; toute évolution crée une nouvelle
version et ne modifie pas une campagne gelée.

## 1. Compilation avant publication

Le responsable confirme type, familles, attentes concrètes et sources ; il ne
choisit pas les poids. Les deux politiques initiales sont :

| Politique | Famille / poids de base | Barème |
| --- | --- | --- |
| `training-demo-v1` | `programming_foundations` / 40 | `programming-v1` |
| `training-demo-v1` | `practical_work` / 35 | `practice-v1` |
| `training-demo-v1` | `learning_approach` / 25 | `learning-v1` |
| `recruitment-demo-v1` | `audience_understanding` / 40 | `audience-v1` |
| `recruitment-demo-v1` | `results_analysis` / 35 | `results-v1` |
| `recruitment-demo-v1` | `content_production` / 25 | `content-v1` |

Les domaines développement et marketing illustrent ces familles, sans règles
de sélection fondées sur le domaine ou les coordonnées. Ajouter une famille
ou un barème nécessite une nouvelle version interne documentée et testée.
Les poids identiques des deux exemples sont intentionnels ; les barèmes et
preuves recherchées diffèrent. Ils sont fictifs, pas des normes SKULLVI.

Une exigence qualitative doit appartenir à une famille prise en charge par
la politique. Un rapprochement proposé doit être confirmé dans l'éditeur.
Si aucune famille convient, enregistrer le brouillon, demander une précision
et bloquer sa publication tant qu'une évaluation prise en charge n'est pas
définie. Une option explicite `manual` est permise **dans une famille connue** :
l'appréciation reste inconnue jusqu'à une correction humaine, avec le même
poids et le même barème. Aucun critère inconnu n'est éliminé du score en secret.

Pour les familles qualitatives présentes F, le poids effectif d'une famille
est `100 × poids_base(f) / somme(poids_base des familles présentes)`.
Dans une famille comprenant n exigences distinctes, chaque critère reçoit
`poids_famille / n`. Ces poids sont des rapports exacts, pas des décimales
arrondies à stocker comme autorité. Au moins une famille qualitative est
requise à la publication ; les conditions déterministes ne prennent aucun
poids. Une famille absente est visible dans le récapitulatif de politique.

Deux attentes explicitement identiques dans une famille sont refusées à la
publication ; le responsable doit les fusionner. Les reformulations suspectes
sont signalées pour confirmation/fusion, sans promesse de détection sémantique
exhaustive. Même si deux attentes distinctes partagent des preuves, leur
famille conserve son poids total. Trois mentions d'un même projet ne créent
ni nouvelle exigence ni bonus.

Le snapshot publié conserve politique, barèmes complets, familles présentes,
répartition exacte, mode `automatic`/`manual`, seuil indispensable et sources
attendues. Aucun LLM ne choisit ou n'ajuste ces éléments par candidat.

## 2. Conditions et compétences indispensables

Les conditions initiales prises en charge sont disponibilité à une date et
disponibilité sur créneaux : question structurée, valeur attendue et opérateur
déclarés à la publication. Seule une réponse explicite est `met` ou `unmet` ;
absence ou contradiction est `unknown`. Pas d'inférence à partir d'un CV.
Les conditions souhaitées sont informatives et ne changent pas l'admissibilité.

`available_by_date` compare la date de disponibilité annoncée à la date limite
attendue (`réponse <= date_attendue`). `available_slots` vérifie que la réponse
de choix multiples inclut tous les option_ids attendus. Le type de question,
les options et la référence source doivent correspondre ; sinon publication
refusée. L'absence de réponse reste unknown, pas une liste vide interprétée
comme indisponibilité. Une liste vide **explicitement confirmée** peut établir
une condition non satisfaite si le formulaire permet ce choix.

Une compétence qualitative `required` garde son poids ordinaire. Son seuil
fictif est 2/4 dans les politiques v1 : niveau 0 ou 1 → alerte
`required_skill_below_threshold`, inconnue → `required_skill_unknown`,
niveau ≥ 2 → pas d'alerte. Cette alerte ne devient pas `condition_unmet` et
n'entraîne aucune décision automatique ; elle exclut le dossier de la vue
« Prêts à examiner » et apparaît dans « À vérifier ». La pertinence de ce
seuil doit être reconsidérée avant tout usage sur des personnes réelles.

## 3. Barèmes complets (0–4)

Un niveau est une appréciation du contenu documenté au niveau attendu,
pas une mesure absolue de la personne. Zéro exige un constat explicite sourcé.
Une absence de mention ou un manque de détails n'autorise pas le niveau zéro.
Ni longueur, style rédactionnel, prestige ni popularité d'un dépôt ne donnent
de points. Déclaration et contribution personnelle restent qualifiées.

| Niveau | Bases de programmation (`programming-v1`) |
| --- | --- |
| 0 | Réponse explicite établissant que les prérequis demandés ne sont pas acquis. |
| 1 | Notions citées avec compréhension très partielle du cas demandé. |
| 2 | Concepts de base expliqués sur un cas simple, lacunes identifiées. |
| 3 | Raisonnement cohérent et étapes expliquées sur le cas. |
| 4 | Raisonnement cohérent, vérification et cas limites adaptés au niveau débutant. |

| Niveau | Mise en pratique (`practice-v1`) |
| --- | --- |
| 0 | Le candidat indique explicitement n'avoir réalisé aucun exercice/projet pertinent. |
| 1 | Exercice guidé décrit avec contribution limitée. |
| 2 | Petite réalisation décrite avec rôle personnel identifiable. |
| 3 | Réalisation avec contribution, choix et résultat décrits. |
| 4 | Réalisation avec difficulté résolue et vérification du résultat. |

| Niveau | Démarche d'apprentissage (`learning-v1`) |
| --- | --- |
| 0 | Le candidat indique explicitement ne pouvoir fournir aucune démarche sur la période demandée. |
| 1 | Activité citée sans démarche détaillée. |
| 2 | Objectif et ressources décrits, application peu détaillée. |
| 3 | Difficulté, ressource et application concrète décrites. |
| 4 | Essai, retour, ajustement et réutilisation décrits. |

| Niveau | Compréhension d'audience (`audience-v1`) |
| --- | --- |
| 0 | Le candidat affirme ne pas savoir identifier une audience pour le cas demandé. |
| 1 | Audience citée sans besoin ni relation avec le message. |
| 2 | Segment et besoin décrits, lien au message encore limité. |
| 3 | Segment, besoin et choix de message/canal justifiés sur le cas. |
| 4 | Choix justifiés avec hypothèses, vérification proposée et ajustement selon retour. |

| Niveau | Analyse de résultats (`results-v1`) |
| --- | --- |
| 0 | Réponse explicite établissant que les indicateurs demandés ne sont pas interprétables par le candidat. |
| 1 | Indicateurs cités sans interprétation utile. |
| 2 | Indicateurs reliés à un objectif, interprétation limitée. |
| 3 | Résultats interprétés et proposition d'action cohérente. |
| 4 | Comparaison contextualisée, limites et recommandation justifiée. |

| Niveau | Production de contenu (`content-v1`) |
| --- | --- |
| 0 | Le candidat indique explicitement n'avoir produit aucun contenu pertinent. |
| 1 | Exemple guidé décrit, contribution limitée ou simplement reproduite. |
| 2 | Contenu décrit/consultable avec rôle personnel et objectif identifiables. |
| 3 | Contenu personnel avec choix de format/message justifiés et résultat décrit. |
| 4 | Choix justifiés, vérification auprès de l'audience et adaptation du contenu documentées. |

Pour tous les barèmes, une contradiction non résolue est une inconnue. Le
modèle doit sélectionner un niveau étayé et signaler ses limites ; il ne
déduit pas un niveau supérieur de l'existence seule d'un artefact.

## 4. Dossiers fictifs et éléments attendus

Les [oracles numériques](../../fixtures/expected-results/evaluation-cases.json)
sont des entrées contrôlées pour le calcul, **pas** des sorties LLM ni une
preuve d'extraction. Les descriptions suivantes guident la rédaction des
sources complètes en T20/T32 ; les pièces réelles et extraits persistés doivent
exister avant tout essai de citation. Les niveaux sont attendus, non mesurés.

| Dossier | Éléments fictifs à fournir | Niveaux attendus |
| --- | --- | --- |
| Amina | Réponse technique cohérente et étapes ; projet personnel avec choix/résultat ; apprentissage avec essai, retour, ajustement et réutilisation. | 3/3/4 ; disponibilité compatible |
| Boris | Cas simple avec lacunes ; projet et contribution décrits ; difficulté, ressource et application. | 2/3/3 ; compatible |
| Chloé | Raisonnement avec cas limites ; projet collectif sans rôle personnel ; difficulté et application. | 4/inconnu/3 ; compatible |
| David | Cas limites vérifiés ; projet avec difficulté résolue et vérification ; difficulté et application. | 4/4/3 ; incompatible |
| Fatou | Audience/message/canal justifiés ; comparaison d'indicateurs contextualisée avec limites ; contenu personnel et objectif. | 3/4/2 ; compatible |
| Karim | Audience avec hypothèses et vérification ; indicateurs reliés à objectif sans interprétation approfondie ; contenu avec choix et résultat. | 4/2/3 ; compatible |
| Lina | Audience justifiée ; aucun indicateur exploitable ; contenu testé et adapté. | 3/inconnu/4 ; compatible |

Inclure ensuite les paraphrases, contradictions, sources répétées et
instructions hostiles. L'oracle de calcul ne démontre pas la validité d'un
modèle de recrutement ni la pertinence d'une appréciation générée.
