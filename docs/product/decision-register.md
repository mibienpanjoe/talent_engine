# Talent Engine — Registre des décisions et vérifications

**Date :** 2026-10-03  
**Statut :** registre vivant ; les résolutions explicites figurent en section 2.  
**Contexte :** [analyse initiale](project-analysis.md).

Une décision conserve la question, les options, le choix explicite du mainteneur,
le motif et les documents affectés. Un choix d'architecture coûteux à inverser
fera ensuite l'objet d'une ADR sous `docs/adr/`. Une décision déjà exprimée dans
les sources n'est pas remise en discussion sans conflit précis.

## 1. Ordre des arbitrages

| ID | Décision | Options ou proposition à examiner | Débloque |
| --- | --- | --- | --- |
| DEC-01 | Objectif de première livraison, délai et ressources | Challenge démontrable, portfolio évolutif ou pilote opérationnel ; préciser échéance, équipe, volumes et budget. | Priorités et critères d'acceptation. |
| DEC-02 | Contrat de campagne et configuration | Définir le snapshot à la publication, le gel proposé à la première soumission réelle, les tests et la duplication. | Formulaire, persistance et comparabilité. |
| DEC-03 | Transformation des exigences en plan d'évaluation | Familles et barèmes connus ; précision ou revue manuelle pour une attente non prise en charge. Définir poids des familles absentes et critères répétés. | Contrat du moteur et données. |
| DEC-04 | Effet du caractère indispensable | Conditions déterministes séparées ; définir le cas d'une compétence qualitative insuffisante ou inconnue. | Admissibilité et files. |
| DEC-05 | Politiques de démonstration | Examiner 40/35/25 comme exemples, compléter les niveaux marketing et construire les dossiers justificatifs attendus. | Oracles des tests de calcul et essais IA. |
| DEC-06 | Résultats partiels et navigation | Score final `null` ; couverture ; intervalle dans le détail ou omis de l'interface ; priorité ou recouvrement des trois vues. | Contrats de lecture et écrans. |
| DEC-07 | Corrections et nouvelle analyse | Définir résultat effectif, conservation et réapplication explicite des corrections selon la version. | Historique, recalcul et relances. |
| DEC-08 | Stack et frontières applicatives | Next.js/TypeScript + FastAPI/Python + PostgreSQL retenus ; préciser les versions et frontières. | Architecture physique et structure du code. |
| DEC-09 | Réception et exécution persistante | Définir idempotence, transaction de soumission, création durable de tâche, reprise et relance ciblée. | API et parcours résilient. |
| DEC-10 | Accès, fichiers et collecte | Compte de démo et session proposés ; fixer limites d'envoi, pages, délais, accès public et suppression. | Contrats d'accès et d'extraction. |
| DEC-11 | Fournisseurs et limites IA | Utiliser le FreeLLMAPI installé comme piste prioritaire ; vérifier son fonctionnement et comparer ses modèles sur les fixtures. | Intégrations réelles. |
| DEC-12 | Design et preuve de démonstration | Définir les écrans essentiels, l'affichage des preuves et les états ; identifier les résultats préchargés. | Identité visuelle et recette du parcours. |
| DEC-13 | Organisation de contribution | Préciser équipe, conventions locales, branches et contrôles ; adapter aux besoins de Talent Engine. | CONTRIBUTING et guidance agents. |
| DEC-14 | Structure du dépôt et outils | Monorepo proposé, API et worker dans un package Python, frontend par fonctionnalités ; pnpm et uv proposés. | [Structure proposée](../architecture/repository-structure.md) et bootstrap. |

Cet ordre suit les dépendances métier. La phase contrats T01–T06 a été demandée explicitement par le mainteneur.
Les confirmations directes (stack, monorepo, gel) sont distinguées des détails
d’implémentation arrêtés par l’assistant pour exécuter cette phase. Les barèmes
et limites de démo sont des choix documentés, pas des valeurs métier mesurées.
Échéance, budget, capacité et fournisseurs restent non inventés.

## 2. Trace historique des résolutions de la phase contrats

| ID | Statut | Choix et motif | Documents à mettre à jour |
| --- | --- | --- | --- |
| DEC-01 | Objectif et organisation résolus ; échéance et ressources techniques ouvertes | MVP du challenge avec parcours complet ; mainteneur seul avec l'assistant ; périmètre conservé explicitement. | Cadrage MVP, roadmap et contribution. |
| DEC-02 | Gel confirmé ; contrat T01 défini, runtime non vérifié | Mainteneur : campagne révisable avant première candidature réelle, puis formulaire et politique figés ; changements par duplication. Snapshots immuables à chaque publication, tests isolés et conflits de version décrits dans le [contrat campagne/formulaire](../campaigns/campaign-and-form-contract.md). | Contrat campagne/formulaire, puis modèle et API en T05. |
| DEC-03 | Référence T02 définie | Familles connues, normalisation des familles présentes et partage égal intra-famille ; exigences non prises en charge bloquent la publication ; mode manuel explicite dans une famille connue. | [Politiques](../evaluation/policies-and-rubrics.md). |
| DEC-04 | Référence T02 définie | Conditions structurées séparées ; seuil fictif 2/4 pour compétences indispensables, alerte de revue sans rejet automatique. | [Contrat d’évaluation](../evaluation/evaluation-contract.md). |
| DEC-05 | Référence T02 définie, non calibrée | Politiques fictives 40/35/25, six barèmes complets et sept oracles numériques ; choix d’implémentation de la phase contrats, pas validation sur personnes réelles. | [Politiques](../evaluation/policies-and-rubrics.md), fixtures attendues. |
| DEC-06 | Référence T03 définie | Score null et couverture en liste, bornes dans le détail ; vues avec recouvrement explicite et all exhaustif ; rang exact de compétition uniquement pour ready. | [Revue](../review/review-and-corrections.md). |
| DEC-07 | Référence T03 définie | Base immuable et corrections historisées ; réanalyse inactive jusqu’à activation explicite, report sélectif contrôlé ou nouvelle base confirmée. | [Revue](../review/review-and-corrections.md). |
| DEC-08 | Stack acceptée ; détails T06 retenus, installation non vérifiée | Next.js 16/Node 24, Python 3.13/FastAPI 0.142, PostgreSQL 17 ; versions cibles et patches candidats dans architecture, locks testés au bootstrap. | [Architecture](../architecture/system-architecture.md), [ADR-0003](../adr/0003-tooling-and-contract-generation.md). |
| DEC-09 | Référence T04 définie | Transaction candidature/réponses/uploads/tâche/clé, rejeu canonique ; worker PostgreSQL avec lease et fencing, étapes/checkpoints, trois tentatives et relance ciblée. | [Réception](../applications/submission-contract.md), [exécution](../operations/analysis-lifecycle.md). |
| DEC-10 | Référence T04 définie | Session responsable et CSRF ; uploads privés bornés, collecte publique limitée, rétention démo et purge durable avec contrôle des tâches en vol. | [Protection](../../SECURITY.md), réception et exécution. |
| DEC-11 | Orientation retenue ; intégration non vérifiée | Mainteneur : FreeLLMAPI déjà installé et configuré. Container arrêté constaté ; démarrage seulement lorsque nécessaire ; modèles, quotas et capacités à vérifier en direct. | [Note d'intégration locale](../integrations/local-freellmapi.md). |
| DEC-12 | Référence fournie ; jeu raster généré, design produit proposé | Préférence sombre conservée. Référence « Signal » déclinée en sept PNG inspectés : signatures, symboles et app icon. Masters vectoriels et validation sur écrans produit restent ouverts. | [Direction visuelle](../design/visual-identity.md) et [assets](../design/brand-assets.md). |
| DEC-13 | Organisation acceptée ; conventions T06 définies | Étapes séquentielles avec vérification/revue/commit ; main conservée, plans locaux ignorés ; push distinct sur demande, définition de terminé et commandes cibles. | [Contribution](../../CONTRIBUTING.md). |
| DEC-14 | Monorepo accepté ; détails T06 retenus, bootstrap à faire | pnpm/uv, backend modulaire et worker partageant package/image ; client local au web généré depuis OpenAPI ; tâches PostgreSQL, pas de broker supplémentaire. | [ADR-0003](../adr/0003-tooling-and-contract-generation.md), [ADR-0004](../adr/0004-postgresql-analysis-worker.md). |

Décomposer les lignes groupées au fil des résolutions.
Une recommandation n'est pas une décision acceptée. Une décision documentaire
n'est pas une preuve d'implémentation ou de validation runtime.

## 3. Clôture de la phase contrats

T01–T06 disposent de contrats propriétaires, modèle/dictionnaire, OpenAPI de
conception, ADR et conventions de contribution. Les références détaillées
servent au bootstrap ; une demande d’exécution n’est pas reformulée en
confirmation individuelle de tous les seuils ou versions par le mainteneur.
Les décisions ci-dessus ne certifient pas leur implémentation.

Restent à **vérifier au moment prévu**, sans rouvrir les choix déjà confirmés :
patches/locks compatibles T07–T08, transactions/authentification et UI en
fondations/tranches, fournisseurs/embeddings/OCR T21–T27, calibration avant
personnes réelles, CI distante après push autorisé. L’échéance, les volumes et
le budget n’ont pas été fournis ; aucun périmètre n’est réduit implicitement.

## 4. Vérification du MVP local, 4 octobre 2026

Les contrats acceptés ont été implémentés : configuration figée au premier
dépôt réel, politiques et calcul backend, revue, corrections, décisions,
reprises et suppression. La [recette](../testing/acceptance-and-reference-cases.md)
relie les exigences à leurs tests et parcours ; les tableaux historiques
ci-dessus ne décrivent pas un reste à implémenter.

Les locks installés, l’interface sombre et les trois usages FreeLLMAPI ont
été exercés. Les [démonstrations](../testing/demonstrations.md) distinguent
résultats préchargés sans clé et dossiers neufs analysés avec fournisseur
identifié. Les choix de démonstration restent non calibrés sur des personnes.
Échéance, capacité, budget, production et conformité restent hors preuve.
