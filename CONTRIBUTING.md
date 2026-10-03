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

`main` reste la branche par défaut. Conserver la branche de travail actuelle
sauf demande explicite ; une branche courte peut être choisie avec le
mainteneur pour les évolutions suivantes. Commits atomiques `docs:`, `feat:`,
`fix:`, `test:`, `chore:` ou `ci:` avec raison claire. Stage par chemins
explicites et revue du staged. Commit et push sont deux actions distinctes :
pas de push, PR, merge, tag, réécriture ou déploiement sans demande applicable.

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

## Commandes cibles (à implémenter)

Aucun Makefile, manifest applicatif ou suite de tests n'existe encore pendant
la phase contrats. Les noms suivants sont un contrat de bootstrap, **pas des
commandes utilisables aujourd'hui** :

| Cible | Comportement / étape de création |
| --- | --- |
| `make install` | pnpm install frozen-lockfile + uv sync locked ; T07–T09. |
| `make dev` | Démarrer runtime local et healthchecks, sans clé IA requise ; T09. |
| `make migrate` | Alembic upgrade head sur base configurée ; T07/T09. |
| `make test-api` | pytest, unités puis intégration PostgreSQL ; T07/T10. |
| `make test-web` | Tests composants/interactions frontend ; T08/T10. |
| `make test-e2e` | Playwright avec runtime/current build, nettoyage isolé ; première tranche UI intégrée. |
| `make lint` / `make typecheck` | Ruff, ESLint, contrôle Python/TypeScript ; T07–T10. |
| `make build` | Build web et image(s) ; T08/T09. |
| `make contracts` / `make check-contracts` | Export serveur/génération puis contrôle sans diff ; T08/T10. |
| `make seed-demo` | Profils fictifs et modes identifiés, seed idempotent ; T32. |

Chaque cible devient documentée comme disponible seulement après preuve.
Versions patch, outils et images figés dans leurs fichiers de version/locks ;
uv `--locked` vérifie la fraîcheur, ne pas remplacer par `--frozen` pour masquer
une dérive. Une mise à jour de dépendance est revue et testée avant nouveau lock.

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
