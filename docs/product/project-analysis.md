# Talent Engine — Analyse initiale

**Date :** 2026-10-03  
**Statut :** analyse documentaire ; arbitrages ouverts ; aucune implémentation vérifiée.  
**Sources :** [cadrage](project-overview.md), puis [spécification du moteur](../evaluation/evaluation-engine-spec.md).

## 1. Objectif et valeur du produit

Talent Engine transforme des candidatures hétérogènes en dossiers exploitables
pour la revue d'une opportunité. Le responsable décrit son besoin, publie un
formulaire adapté, puis comprend l'adéquation de chaque dossier à partir de
critères et d'éléments justificatifs consultables.

La valeur repose sur trois capacités : collecter des informations pertinentes,
les apprécier selon une politique commune à la campagne, et rendre visibles
les résultats comme les inconnues. Le score organise la revue ; la sélection
reste une décision humaine.

La première livraison retenue est un MVP du mini-challenge SKULLVI avec un
parcours démontrable complet, en formation développement et recrutement
marketing. Le mainteneur travaille seul avec l'assistant. Ce mode de travail
ne réduit pas le périmètre du MVP. L'échéance n'a pas été précisée.

## 2. Parcours principal à documenter

```text
Besoin du responsable
  → exigences confirmées et sources attendues
  → formulaire vérifié et campagne publiée
  → candidature enregistrée durablement
  → collecte et extraction avec provenance
  → appréciations par exigence
  → admissibilité, couverture et score éventuel
  → file de revue et détail des preuves
  → correction motivée et décision humaine
```

Les API externes interviennent après l'enregistrement de la candidature.
Leur échec laisse un dossier et un état de traitement consultables.

## 3. Positions déjà exprimées et propositions

« Position source » désigne une orientation explicite des documents reçus.
Cela ne signifie ni acceptation de tous les détails techniques ni vérification
d'une capacité existante.

| Sujet | Position source | Ce qui reste à décider |
| --- | --- | --- |
| Campagnes | Création autonome, formulaire public intégré, domaines extensibles. | Cycle de publication, versions et instant du gel. |
| Évaluation | Politiques et calcul dans le backend ; aucun réglage de poids imposé au responsable. | Familles prises en charge, barèmes et compilation du besoin. |
| IA | Extraction et appréciation encadrées ; sources citées ; score calculé par code. | Fournisseurs, essais, budget et limites d'usage. |
| Inconnues | Absence d'information distincte du zéro ; résultat partiel non classé comme complet. | Présentation de l'intervalle et affectation exacte aux files. |
| Sources | Réponses, documents, portfolios et GitHub ciblés inclus. | Limites chiffrées, dédoublonnage et localisation des extraits. |
| Revue | Correction motivée, historique et décision humaine distincte. | Résultat effectif après correction et après nouvelle analyse. |
| Stack | Proposition Next.js/TypeScript, FastAPI/Python et PostgreSQL retenue par le mainteneur. | Versions, organisation et contrats ; aucune application vérifiée. |
| Exécution | Application locale ; traitements persistants et relançables. | Contrat de tâches, reprise et exploitation. |
| Accès | Espace responsable protégé. | Compte de démo et session proposés ; limites des routes publiques. |
| Design | Interface sobre, formulaires mobiles, sources accessibles ; préférence pour un mode sombre par défaut. | Tokens, éventuel thème clair secondaire et validation dans un navigateur. |

## 4. Points solides du cadrage

- Les acteurs, le parcours principal et le périmètre exclu sont identifiés.
- Admissibilité, appréciation, couverture, traitement et décision humaine sont
  des concepts distincts.
- Les exemples numériques rendent le calcul testable sans fournisseur IA.
- Les sources ont une provenance et ne donnent pas de bonus lié à leur support.
- La candidature survit aux erreurs des intégrations et les relances conservent
  l'historique.
- Les démonstrations préchargées doivent être identifiées et distinguées des
  analyses exécutées en direct.

## 5. Contrats incomplets ou ambigus

### Besoin libre et politiques fixes

Le responsable peut exprimer des exigences variées, mais le moteur nécessite
des familles et des barèmes connus avant l'analyse. Les deux exemples ne
définissent pas encore la transformation générale du besoin en plan
d'évaluation. Il faut préciser les familles admises, les exigences non prises
en charge, les doublons, les familles absentes et la répartition des poids.
Les exemples formation et marketing utilisent tous deux 40/35/25 ; ils ne
démontrent pas encore une différenciation effective entre les deux politiques.

### Indispensable : condition ou compétence

La disponibilité possède une règle structurée ; une compétence qualitative
nécessite une appréciation. Le contrat doit dire si une compétence indispensable
explicitement insuffisante produit `condition_unmet`, un avertissement distinct
ou une autre conséquence. Les seuils et l'effet sur les files ne sont pas fixés.

### Gel et comparabilité

Le cadrage propose un gel à la première candidature réelle, tandis que le
moteur exige une politique fixée avant le traitement. Il faut préciser le
snapshot utilisé dès la publication, le rôle des candidatures de test et le
comportement d'une modification concurrente à une soumission.

### Inconnues et représentation du score

La spécification indique « score final nul » pour Chloé. Cela doit être clarifié
comme absence de score final (`null`), conformément au contrat des inconnues,
et non comme score numérique zéro. Les deux formules de score sont compatibles
si le niveau 0–4 est divisé par quatre et les poids totalisent 100.

Les niveaux marketing pour « audience » et « contenu » restent à rédiger.
Les chiffres fictifs illustrent le calcul ; ils ne valident pas ces barèmes.

### Files de revue

Le cadrage évoque deux files utiles ; le complément en précise trois, plus
« Toutes les candidatures ». C'est une précision à consolider dans un contrat
unique. Un dossier peut être partiel et avoir une condition non satisfaite :
la priorité entre vues ou leur recouvrement doit être explicite. Le tri doit
aussi préciser le rapport entre précision interne, score affiché et ex æquo.

### Corrections et réanalyses

Conserver les anciennes évaluations ne suffit pas à déterminer le résultat
effectif du dashboard. Il faut définir la couche de correction, son rattachement
à une version et le comportement d'une nouvelle analyse face aux corrections
existantes. Aucun report ou effacement implicite ne doit être inventé.

### Réception et reprise

Le contrat de soumission doit définir l'idempotence, les pièces jointes,
la transaction de réception et la création de la tâche durable. Le contrat
d'exécution doit couvrir acquisition, interruption, quota, reprise limitée
et relance ciblée. Les noms d'états seuls ne définissent pas ces transitions.

### Preuve et généralisation

Une référence d'extrait existante valide la provenance, pas la pertinence de
l'appréciation. Les fixtures doivent inclure les textes et sources qui
justifient les résultats attendus, puis permettre des essais de récupération
et d'appréciation. Les limites du jeu de démonstration restent visibles.

## 6. Découpage métier proposé

| Domaine | Responsabilité |
| --- | --- |
| Accès | Responsable, session et contrôle des routes privées. |
| Campagnes et formulaires | Besoin, exigences, questions, publication et configuration versionnée. |
| Candidatures | Réception durable, réponses, pièces et idempotence. |
| Sources et éléments justificatifs | Collecte bornée, extraction, snapshots et provenance. |
| Évaluation | Politiques, barèmes, appréciations validées et calcul. |
| Revue | Résultat consultable, corrections, décisions et historique. |
| Exécution | Tâches persistantes, reprises et état opérationnel. |

Ce découpage est une proposition de responsabilités, pas un schéma de
microservices ni une structure de code acceptée. Les intégrations IA et web
servent ces domaines sans devenir propriétaires des règles métier.

## 7. Ce que nous reprenons de FIRA

Les fichiers actuels de FIRA séparent exigences avec acceptation, architecture,
modèle canonique, dictionnaire, contrats métier, design et ADR. Nous reprenons
cette séparation, la provenance de bout en bout et les décisions documentées.

Les données bancaires, rôles de conformité, anciens délais de 72 heures et
workflows historiques de FIRA ne s'appliquent pas à Talent Engine. Son exécution
inline garantie ne remplace pas automatiquement la proposition de worker
persistant de Talent Engine. La méthode d'organisation sert de référence ;
chaque choix d'architecture doit répondre au parcours Talent Engine.

## 8. Suite de la documentation

Le [registre de décisions](decision-register.md) ordonne les arbitrages.
La [carte documentaire](../documentation-map.md) indique les documents à
produire et leur ordre de dépendance. Le [cadrage MVP](mvp-requirements-and-acceptance.md)
formalise maintenant le périmètre source. Les versions techniques et modèles
restent ouverts ; FreeLLMAPI local constitue la piste d'intégration à vérifier.
