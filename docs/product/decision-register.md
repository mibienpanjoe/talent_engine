# Talent Engine — Registre des décisions ouvertes

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

Cet ordre suit les dépendances métier. Certains choix techniques peuvent être
discutés en parallèle ; les décisions restent ouvertes jusqu'à leur résolution
explicite. Aucun délai, budget, volume, barème ou fournisseur n'est inventé.

## 2. Trace des résolutions

| ID | Statut | Choix et motif | Documents à mettre à jour |
| --- | --- | --- | --- |
| DEC-01 | Objectif et organisation résolus ; échéance et ressources techniques ouvertes | MVP du challenge avec parcours complet ; mainteneur seul avec l'assistant ; périmètre conservé explicitement. | Cadrage MVP, roadmap et contribution. |
| DEC-02 à DEC-07 | Ouvert | En attente de discussion. | Contrats métier et modèle de données. |
| DEC-08 | Stack retenue ; détails ouverts | Proposition TypeScript/Next.js et Python/FastAPI retenue avec la base PostgreSQL suggérée. [ADR-0001](../adr/0001-application-nextjs-fastapi-postgresql.md). | Overview, architecture et API. |
| DEC-09 à DEC-10 | Ouvert | En attente de discussion. | Soumission, exécution et sécurité. |
| DEC-11 | Orientation retenue ; intégration non vérifiée | Mainteneur : FreeLLMAPI déjà installé et configuré. Container arrêté constaté ; démarrage seulement lorsque nécessaire ; modèles, quotas et capacités à vérifier en direct. | [Note d'intégration locale](../integrations/local-freellmapi.md). |
| DEC-12 | Référence fournie ; jeu raster généré, design produit proposé | Préférence sombre conservée. Référence « Signal » déclinée en sept PNG inspectés : signatures, symboles et app icon. Masters vectoriels et validation sur écrans produit restent ouverts. | [Direction visuelle](../design/visual-identity.md) et [assets](../design/brand-assets.md). |
| DEC-13 | Organisation résolue ; conventions ouvertes | Mainteneur seul avec l'assistant ; aucun changement de périmètre. Branches et livraison à définir. | Contribution. |
| DEC-14 | Monorepo accepté ; détails ouverts | Un dépôt avec `apps/web/` et `apps/api/` retenu dans [ADR-0002](../adr/0002-monorepo-web-et-api.md). Worker, structure interne et outils proposés ; aucun code applicatif créé. | Structure du dépôt et bootstrap. |

Décomposer les lignes groupées au fil des résolutions.
Une recommandation n'est pas une décision acceptée. Une décision documentaire
n'est pas une preuve d'implémentation ou de validation runtime.
