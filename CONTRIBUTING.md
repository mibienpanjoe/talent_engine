# Contribuer à Talent Engine

Le MVP est développé par un mainteneur avec l'assistant. Les contrats décrivent
le comportement cible ; leur commit n'est pas une preuve d'implémentation.
Voir [architecture](docs/architecture/system-architecture.md),
[contrats HTTP](docs/architecture/api-contract.md) et [sécurité](SECURITY.md).

## Travail par étapes

Les plans `tasks/plan.md`, `tasks/todo.md`, journaux et contrôles locaux restent
ignorés, non stagés, non committés. La documentation durable sous `docs/` et
les fixtures fictives nécessaires au produit sont versionnées. Ne pas publier
les plans ni secrets par `git add .` ou `git add -f`.

Pour chaque étape : lire contrat/dépendances, implémenter, vérifier le chemin
revendiqué, revoir/corriger, noter preuves localement, **committer avant la
suivante**. En cas d'échec, corriger et reprouver la même étape ; ne pas la
cocher sur la promesse qu'une étape future la fera fonctionner.

`main` reste la branche par défaut. Une branche et une PR par phase :
`docs/contracts`, `feat/foundations`, puis les phases fonctionnelles. Si la
phase suivante commence avant fusion, sa PR cible provisoirement la branche
précédente ; elle est reciblée vers `main` après fusion, avec contrôle du diff.
Commits atomiques `docs:`, `feat:`, `fix:`, `test:`, `chore:` ou `ci:` ; stage par
chemins explicites et revue du staged. Le mainteneur autorise ici la publication
et les PR par phase. Fusion, tag et déploiement restent des actions distinctes.

## Définition de terminé

- Exigence/contrat de l'étape respecté ; états vides, échecs et inconnues
  traités, pas uniquement le scénario heureux.
- Logique métier vérifiée par tests comportementaux ; transactions/verrous
  exercés sur PostgreSQL ; tests négatifs d'accès/données non fiables ciblés.
- Changement UI exercé dans navigateur sur version courante, clavier/mobile,
  focus et contraste, avec API réelle lorsque l'étape annonce l'intégration.
- Un chemin multi-domaines prouvé : producteur → API → persistance → consumer
  → rendu. Fixtures/contrat/build ne remplacent pas ce parcours.
- Tests/lint/typecheck/build pertinents et fraîcheur OpenAPI/types contrôlés.
  Diff relu : exactitude, simplicité, frontières, sécurité et coût ; aucun
  changement hors scope, secret, donnée candidat réelle ou plan local stagé.
- Docs propriétaires mises à jour ; limitations et preuves identifiées.
  Commit créé, SHA consigné localement ; CI distante déclarée seulement si
  un run GitHub correspondant au commit a été effectivement contrôlé.

Les étapes documentaires utilisent revue de scénarios, liens, schémas et
calculs indépendants. Ne pas inventer des tests applicatifs avant existence
de l'application. Une affirmation « fonctionne » requiert la bonne surface.

## Commandes disponibles

Voir [runtime local](docs/operations/local-runtime.md) pour l'installation.

| Cible | Comportement |
| --- | --- |
| `make install` | pnpm frozen-lockfile et uv locked. |
| `make up` / `make down` | Runtime Compose ; arrêt sans suppression des volumes. |
| `make migrate` | Migration explicite dans Compose. |
| `make api-test` | Tests comportementaux pytest. |
| `make lint` / `make typecheck` | Ruff et contrôle TypeScript. |
| `make build` | Build web ; images construites par `make up`. |
| `make contracts` / `make contracts-check` | Export FastAPI/client, puis contrôle sans mutation. |
| `make check` | Tests, lint, contrats, types et build. |

Les tests PostgreSQL utilisent une base isolée et `apps/api/checks/check_database.py`.
Les commandes E2E et seed-demo seront ajoutées avec leurs tranches respectives.
uv `--locked` vérifie la fraîcheur du lock ; ne pas masquer une dérive avec
`--frozen`. Toute mise à jour de dépendance est revue et testée avant nouveau lock.

## Conventions de contrats et UI

Maintenir français dans les docs, snake_case pour JSON API, IDs/version et
nullabilité selon dictionnaire. Score/politique seulement backend. Renderer
de questions partagé, client dérivé d'OpenAPI et classes/tokens cohérents.
Ne pas importer le repository privé d'un autre module ; partager la transaction
sans commit interne lors d'une opération multi-domaines.

Pour une modification README, appliquer `anomaly-readme`. Pour UI, appliquer
frontend-ui-engineering/better-ui et vérifier en navigateur. Les inconnues,
conditions, incidents techniques et décisions humaines restent visibles et
distincts ; pas d'animation d'analyse fictive ni de bonus lié au support.

Les fixtures publiques sont fictives, minimisées et identifiées. L'installation
FreeLLMAPI existante n'est ni copiée ni démarrée hors besoin d'intégration.
