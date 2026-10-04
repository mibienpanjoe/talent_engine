# Talent Engine — Carte documentaire

**Date :** 2026-10-04

**Statut :** index de la documentation du MVP implémenté.

Cette carte rassemble les guides, contrats et décisions du dépôt. Les résultats
vérifiés et leurs limites sont détaillés dans la recette ; les documents de
cadrage initial conservent leur contexte historique.

## Découvrir et essayer

- [Aperçu de l’interface](interface-gallery.md) : fonctionnalités et captures de démonstration.
- [Installation locale](operations/local-runtime.md) : commandes, configuration et accès.
- [Démonstrations](testing/demonstrations.md) : formation et marketing, résultats préchargés ou analyses réelles.
- [Recette du MVP](testing/acceptance-and-reference-cases.md) : couverture des exigences et limites des vérifications.

## Produit et règles métier

- [Cadrage produit](product/project-overview.md) : vision et parcours initial.
- [Exigences et acceptation](product/mvp-requirements-and-acceptance.md) : périmètre du MVP et critères observables.
- [Registre des décisions](product/decision-register.md) : choix retenus et arbitrages.
- [Campagnes et formulaires](campaigns/campaign-and-form-contract.md) : configuration, publication, gel et duplication.
- [Réception des candidatures](applications/submission-contract.md) : réponses, documents et idempotence.
- [Revue et corrections](review/review-and-corrections.md) : files de dossiers, corrections humaines, décisions et versions.

## Évaluation et collecte des sources

- [Contrat d’évaluation](evaluation/evaluation-contract.md) : états, disponibilité, couverture et score.
- [Politiques et barèmes](evaluation/policies-and-rubrics.md) : compilation des critères, poids et niveaux.
- [Extraction des sources](operations/source-extraction.md) : réponses, documents, OCR, portfolios et GitHub.
- [Adaptateurs IA](integrations/ai-adapters.md) : appréciation, vecteurs, OCR et provenance.
- [Passerelle FreeLLMAPI](integrations/local-freellmapi.md) : configuration serveur et limites vérifiées.
- [Cycle de l’analyse](operations/analysis-lifecycle.md) : tâches persistantes, tentatives, reprise et relances.

## Architecture et données

- [Architecture système](architecture/system-architecture.md) : modules, outils et runtime.
- [Organisation du dépôt](architecture/repository-structure.md) : découpage du monorepo et contexte des choix initiaux.
- [Contrat HTTP](architecture/api-contract.md) : routes et conception de l’API.
- [Modèle canonique](data/canonical-model.md) : entités, relations et invariants.
- [Dictionnaire de données](data/data-dictionary.md) : types, nullabilité et versions.
- [Audit des dépendances](operations/dependency-audit.md) : versions et vérifications.

Les schémas HTTP actuels sont exportés depuis le serveur dans
[contracts/openapi.json](../contracts/openapi.json). Le fichier
[contracts/api-design.openapi.json](../contracts/api-design.openapi.json)
conserve le contrat manuel de conception. Les résultats numériques fictifs de
référence se trouvent dans `fixtures/expected-results/`.

## Identité et sécurité

- [Identité visuelle](design/visual-identity.md) : thème sombre et direction « Signal ».
- [Assets de marque](design/brand-assets.md) : logos, icônes et usages.
- [Sécurité](../SECURITY.md) : accès, collecte et suppression des données.

## Décisions d’architecture

- [ADR-0001](adr/0001-application-nextjs-fastapi-postgresql.md) : Next.js, FastAPI et PostgreSQL.
- [ADR-0002](adr/0002-monorepo-web-et-api.md) : monorepo web et API.
- [ADR-0003](adr/0003-tooling-and-contract-generation.md) : outils et génération des contrats.
- [ADR-0004](adr/0004-postgresql-analysis-worker.md) : worker PostgreSQL durable.

## Documents de cadrage initial

L’[analyse initiale](product/project-analysis.md) et la
[spécification initiale du moteur](evaluation/evaluation-engine-spec.md)
expliquent l’origine du produit et des propositions. Pour les règles détaillées,
consulter les contrats métier ci-dessus ; pour leur vérification, consulter la recette.

## Organisation du dépôt

```text
apps/web/       Interface Next.js et client TypeScript généré
apps/api/       API FastAPI, métier, worker et migrations
contracts/      Export HTTP actuel et contrat de conception
fixtures/       Données fictives et résultats de référence
docs/           Guides, contrats, décisions et captures de l’interface
assets/brand/   Logos et icônes partagés
```

Les plans et notes du dossier `tasks/` restent locaux et non committés. La
documentation destinée aux lecteurs du dépôt est conservée sous `docs/`.

## Conventions de documentation

- Distinguer cadrage initial, décision retenue et comportement vérifié.
- Définir chaque exigence avec un identifiant stable et une acceptation observable.
- Donner à chaque contrat une responsabilité principale et y renvoyer depuis les autres documents.
- Conserver les informations inconnues, échecs techniques et décisions humaines comme états distincts.
- Documenter les versions de configuration, politique, modèle, prompt et sources.
- Consigner les choix d’architecture dans les ADR et actualiser le contrat concerné lorsqu’il change.
- Identifier les données fictives, résultats préchargés et analyses réellement exécutées.
