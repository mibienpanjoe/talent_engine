# Talent Engine — Structure du dépôt proposée

**Date :** 2026-10-03  
**Statut :** monorepo retenu ; détails arrêtés en T06, aucun squelette applicatif créé.
**Dépendances :** [stack retenue](../adr/0001-application-nextjs-fastapi-postgresql.md),
[cadrage MVP](../product/mvp-requirements-and-acceptance.md).

Référence actuelle : [architecture système](system-architecture.md),
[ADR-0003](../adr/0003-tooling-and-contract-generation.md) et
[ADR-0004](../adr/0004-postgresql-analysis-worker.md). Les mentions de proposition
ci-dessous décrivent leur origine ; les choix T06 servent maintenant au bootstrap.

## 1. Recommandation

Le [monorepo retenu](../adr/0002-monorepo-web-et-api.md) contient le frontend,
le backend, les fixtures et la documentation. La proposition ajoute les
contrats générés, un backend modulaire et un worker exécuté comme processus
distinct qui importe le même package Python que l'API.

Cette organisation permet de modifier un contrat serveur, son consommateur
frontend et leurs vérifications dans une seule modification du dépôt. Le code
de calcul, les politiques et les accès aux données ont un propriétaire unique.

Le périmètre MVP reste complet. La structure réduit le coût de coordination
sans transformer une fonctionnalité métier en projet ou service séparé.

## 2. Arborescence cible

Les fichiers ci-dessous sont une cible. Seule la documentation existe
actuellement ; les manifestes, commandes et services ne sont pas encore créés.

```text
talent_engine/
  assets/
    brand/                        PNG partagés et manifest de provenance
  apps/
    web/
      src/
        app/                      routes, layouts et composition Next.js
          (public)/               formulaire de candidature public
          (workspace)/            espace responsable
        features/                 UI et interactions par domaine
          campaigns/
          applications/
          evaluations/
          reviews/
        components/
          ui/                     primitives shadcn/ui
          shared/                 composants partagés entre domaines
        lib/
          api/                    client HTTP et types générés
            generated/
        styles/                   thème sombre et tokens communs
      public/                     ressources publiquement accessibles
      tests/                      tests de composants et logique frontend
      package.json
      next.config.ts
      Dockerfile
    api/
      src/
        talent_engine/
          main.py                 assemblage de l'application FastAPI
          core/                   configuration, journalisation, erreurs
          db/                     connexion, session et métadonnées communes
          modules/
            access/
            campaigns/
            applications/
            sources/
            evaluations/
            reviews/
            analyses/
          integrations/           clients IA, extraction et services externes
          worker/                 entrée du processus et boucle d'exécution
      migrations/                 migrations Alembic, y compris leurs versions
      tests/
        unit/
        integration/
      pyproject.toml
      uv.lock
      alembic.ini
      Dockerfile                  image commune à API et worker
  contracts/
    openapi.json                  contrat exporté depuis FastAPI
  fixtures/
    campaigns/
    applications/
    documents/
    external-responses/
    expected-results/
  tests/
    e2e/                          parcours navigateur traversant toute l'application
  scripts/                        export de contrat, génération client, seed
  docs/                           documentation déjà classée par sujet
  .github/
    workflows/                    contrôles automatisés lorsqu'ils seront définis
  .env.example
  .gitignore
  compose.yaml
  Makefile                        commandes communes du dépôt
  package.json                    scripts frontend et tests de parcours
  pnpm-workspace.yaml
  pnpm-lock.yaml
  README.md
  CONTRIBUTING.md
  SECURITY.md
```

Créer les répertoires au moment où ils accueillent du code ou des données.
Les fichiers privés déposés par les candidats ne vont jamais dans `public/`
ou `fixtures/` : ils utilisent un stockage privé configuré, hors Git.
Le dossier local `tasks/`, s'il est utilisé, reste hors versionnement.

## 3. Organisation frontend

`app/` possède les routes et layouts. `features/` rassemble composants métier,
hooks, schémas de formulaire et fonctions de présentation d'un domaine.
`components/ui/` possède les primitives ; `components/shared/` contient les
composants réellement réutilisés par plusieurs domaines.

L'éditeur, l'aperçu et le formulaire public utilisent un moteur de rendu de
questions commun, initialement sous `features/campaigns/`. Le frontend n'a pas
une deuxième implémentation du score, des politiques ou de l'admissibilité.

Le client API reste dans `apps/web/src/lib/api/`, puisqu'il possède un seul
consommateur. Son extraction dans un package partagé sera justifiée par un
second consommateur réel. La position de shadcn/ui suit la même logique.

La préférence sombre est portée par les tokens de `styles/`, puis consommée
par les primitives et composants métier. La configuration serveur de la
passerelle LLM reste dans le backend.

## 4. Organisation backend

Chaque module possède une surface publique courte. À mesure de ses besoins,
il peut contenir `router.py`, `schemas.py`, `service.py`, `repository.py` et
`models.py`. Ces fichiers ne sont pas tous obligatoires pour chaque module.

| Module | Responsabilité |
| --- | --- |
| `access` | Responsable, session et autorisations. |
| `campaigns` | Campagne, exigences, questions et configuration publiée. |
| `applications` | Réception idempotente, réponses et références des pièces. |
| `sources` | Sources récupérées, extractions, snapshots et extraits justificatifs. |
| `evaluations` | Politiques, barèmes, appréciations et calcul déterministe. |
| `reviews` | Corrections motivées, décisions et résultat effectif consultable. |
| `analyses` | Orchestration du parcours, tâches persistantes, reprise et progression. |

Les routes traduisent HTTP en appels de service. Un service d'un domaine
consomme la surface publique d'un autre ; il n'importe pas son repository
privé. `core/` et `db/` contiennent des fondations techniques, sans règles
d'évaluation. Les migrations sont centralisées dans une seule chaîne Alembic.

Les politiques et barèmes versionnés appartiennent à `evaluations/` ; leurs
représentations persistées et snapshots seront définis dans le contrat du
moteur. Les résultats attendus fictifs restent sous `fixtures/expected-results/`.

## 5. API, worker et intégrations

API et worker partagent le package `talent_engine` et la même image Python.
Ils ont deux points d'entrée et deux processus Compose. Le worker acquiert
des tâches persistantes et délègue leur traitement à `modules/analyses/` ;
les règles et le calcul restent dans leurs modules métier.

`integrations/` possède les clients HTTP et adaptateurs pour FreeLLMAPI,
GitHub, OCR et extraction web/documentaire, selon les contrats retenus.
Ces adaptateurs ne décident pas des poids ou des niveaux admissibles.

Le backend appelle la passerelle FreeLLMAPI existante par une URL configurable.
Le dépôt Talent Engine ne copie pas son installation ou ses clés. Son container
est démarré seulement lorsque nécessaire, selon le choix du mainteneur. Son
accès depuis les containers Talent Engine devra être configuré et vérifié.

## 6. Contrat et dépendances

Proposition : pnpm pour la partie TypeScript, uv pour le projet Python.
Chaque écosystème possède son manifeste et son fichier de verrouillage.
Un Makefile à la racine donne des points d'entrée communs pour les opérations
de développement une fois leurs implémentations disponibles.

FastAPI et ses schémas serveur produisent `contracts/openapi.json`. Les types
TypeScript de `lib/api/generated/` dérivent de cet export. Les fichiers générés
sont identifiés et leur fraîcheur doit être vérifiée lors d'un changement de
contrat. Les outils de génération sont arrêtés en T06 : openapi-typescript et openapi-fetch, avec versions exactes verrouillées au bootstrap.

Les versions des langages et bibliothèques seront figées au bootstrap.
Les commandes proposées ne sont pas annoncées comme exécutables avant cela.

## 7. Fixtures et tests

- `apps/api/tests/` vérifie règles, calcul, persistance, reprise et adaptateurs.
- `apps/web/tests/` vérifie interactions et logique de formulaire/presentation.
- `tests/e2e/` exerce le parcours public vers API, persistance, worker et revue.
- `fixtures/` contient uniquement des dossiers fictifs partagés : entrées,
  sources, réponses externes identifiées et résultats attendus.

Les helpers utilisés uniquement par une suite restent avec ses tests.
Le seed de démo et les tests peuvent lire les mêmes fixtures, sans confondre
un résultat préchargé avec une analyse exécutée.

## 8. Décisions proposées pour discussion

1. **Accepté :** monorepo `apps/web` + `apps/api`, avec documentation et fixtures communes.
2. Backend modulaire ; worker partageant le package de l'API.
3. Frontend organisé par fonctionnalités, avec routes Next.js séparées.
4. Client TypeScript généré local au frontend depuis OpenAPI.
5. pnpm + uv et points d'entrée communs dans un Makefile.

Le choix monorepo est consigné dans ADR-0002. Son acceptation ne vaut pas
acceptation implicite des autres détails ci-dessus. Le worker et les outils de dépendances sont arrêtés dans ADR-0003/0004
pour la phase contrats demandée ; leur installation reste à vérifier.

## 9. Sources techniques vérifiées

Les outils documentent les possibilités ci-dessous ; le découpage métier
et leur combinaison sont des recommandations propres à Talent Engine.

- [Next.js — dossier src](https://nextjs.org/docs/app/api-reference/file-conventions/src-folder) : code applicatif sous `src/`, configuration et ressources publiques à leur emplacement dédié.
- [FastAPI — applications réparties en plusieurs fichiers](https://fastapi.tiangolo.com/tutorial/bigger-applications/) : organisation par packages et assemblage de routeurs.
- [pnpm — workspaces](https://pnpm.io/workspaces) : déclaration des projets TypeScript d'un dépôt commun.
- [uv — structure d'un projet](https://docs.astral.sh/uv/concepts/projects/layout/) : manifeste Python, environnement et fichier de verrouillage.
