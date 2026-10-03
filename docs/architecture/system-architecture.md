# Talent Engine — Architecture d'implémentation

**Date :** 2026-10-03. **Statut :** référence T06 ; services et commandes
non créés. Stack et monorepo acceptés dans ADR-0001/0002 ; détails arrêtés
pour exécuter la phase contrats dans [ADR-0003](../adr/0003-tooling-and-contract-generation.md)
et [ADR-0004](../adr/0004-postgresql-analysis-worker.md).

## 1. Processus et chemins

Navigateur → origine web → `/api/v1` FastAPI → PostgreSQL et stockage privé.
Le worker Python lit les tâches PostgreSQL puis appelle extracteurs et
adaptateurs externes ; il persiste sources/appréciations et résultats avant
leur lecture par l'API. La qualification et son calcul ont un propriétaire
unique dans le backend. Aucun moteur de score dans Next.js.

Compose gère web, API, worker et PostgreSQL ; une image Python commune avec
deux points d'entrée. Migrations explicites, pas de migration concurrente
automatique au démarrage de chaque service. Volume privé partagé API/worker,
jamais monté dans ressources publiques. Répertoire runtime local ignoré,
services exposés sur loopback pour démo. Health live et ready distincts.

Le worker n'utilise pas BackgroundTasks ou mémoire de processus comme file
durable. Pas de Redis, broker, microservices supplémentaires ni base vectorielle
dans ce MVP. PostgreSQL conserve les budgets, leases, checkpoints et demandes
de purge ; leur sûreté devra être testée sur PostgreSQL réel.

## 2. Organisation et frontières

`apps/api/src/talent_engine/` contient core, db, modules, integrations et worker.
Chaque domaine expose services/schémas publics ; ses repositories sont privés.
Ne créer un fichier ou dossier que lorsqu'il porte du code utile.

| Module | Surface possédée |
| --- | --- |
| access | Session, CSRF, identité et autorisation. |
| campaigns | Brouillon, publication/snapshot, politique compilée et contrôle de réception. |
| applications | Réception/coordonnées/réponses, uploads, lecture privée et suppression. |
| sources | Versions de sources, extraits et manifeste, cache privé versionné. |
| evaluations | Compilation des politiques, validation des appréciations, calcul exact et bases immuables. |
| reviews | Projection effective, corrections, décisions et activation. |
| analyses | Tâches/étapes, acquisition/reprises, orchestration des analyses et progression. |

Les opérations multi-domaines partagent une session SQLAlchemy transactionnelle,
mais seule l'opération propriétaire fait commit/rollback. Un service appelé
ne commet pas indépendamment une moitié de réception ou de correction.
Les accès SQL synchrones utilisent SQLAlchemy 2.0 et psycopg 3 ; sessions
distinctes par requête/tentative, jamais partagées entre threads/workers.
Appels HTTP synchrones du worker via httpx avec limites et délais explicites,
hors transaction SQL. Les parsers lourds tournent en processus isolé borné.

Pour éviter des cycles d'import : l'assemblage au point d'entrée injecte les
ports publics de lecture/écriture nécessaires à l'orchestrateur, au lieu
d'importer les repositories d'applications/revue dans analyses. La réception
appelle `enqueue_initial(transaction, application_context)` sans que ce port
importe le service de réception. Le worker reçoit les ports
`load_application_context`, `read_private_file` et `activate_first_base` ;
leur implémentation reste chez applications/reviews. Le calcul reçoit des
appréciations déjà validées et ne dépend pas d'un client HTTP ou du frontend.
Cette inversion est limitée aux frontières réellement cycliques, sans bus
générique ni abstraction pour chaque fonction.

## 3. Frontend et API

`apps/web/src/app/` compose les routes publiques et workspace. `features/`
porte campagnes, candidatures, évaluations et revue ; `components/ui/`
porte primitives, `components/shared/` les composants réellement partagés.
Tokens sombres et assets Signal sont intégrés depuis `assets/brand/`.

Un renderer de questions partagé produit éditeur/aperçu/formulaire. Le serveur
valide la version reçue. Client HTTP sous `lib/api/`, types générés par
openapi-typescript et transport typé par openapi-fetch. Les types TypeScript
ne remplacent pas validation serveur ni traitement des erreurs runtime.

Le client provient du futur export FastAPI `contracts/openapi.json`. Le
[contrat de conception](../../contracts/api-design.openapi.json) sert de
référence de comparaison jusqu'à l'implémentation. Une fois convergés, l'export
serveur est l'autorité ; éviter d'éditer manuellement le fichier généré.
Les écarts de conception sont justifiés et mis à jour avec le code.

## 4. Versions cibles et verrouillage

Choix de base à vérifier par installation/build en T07/T08 ; aucune installation
du runtime cible réalisée dans cette phase. Les versions patch sont enregistrées
dans manifestes, fichiers de version, locks et images digest au bootstrap,
après examen des avis de sécurité ; pas d'image `latest` en livraison.

| Composant | Cible retenue / premier candidat |
| --- | --- |
| Node.js | 24 LTS ; candidat 24.21.0 documenté, pas le 24.12.0 actuellement installé. |
| Next.js / React | Next.js 16, candidat 16.3.8 ; React/React DOM 19.2 compatibles avec sa résolution. |
| TypeScript / UI | TypeScript 5, Tailwind CSS 4, primitives shadcn/ui et Lucide ; patches verrouillés au bootstrap. |
| pnpm | Série 10 ; 10.28.0 local observé, packageManager exact fixé après vérification. |
| Python | CPython 3.13 standard ; candidat 3.13.16 ; le Python système 3.10.12 n'est pas modifié. |
| uv | Série 0.12 ; 0.12.15 local observé, version exacte de bootstrap enregistrée. |
| API | FastAPI 0.142, candidat 0.142.2 ; Pydantic 2 et pydantic-settings 2 ; Starlette résolu par FastAPI. |
| Persistance | PostgreSQL 17, candidat 17.11 ; SQLAlchemy 2.0, psycopg 3, Alembic 1. |
| Types API | openapi-typescript 7, openapi-fetch compatible avec les types générés. |
| Tests | pytest + PostgreSQL réel pour transactions ; Vitest/Testing Library pour UI ; Playwright pour parcours. |

Ces candidats ne constituent pas un lockfile testé ni la promesse d'utiliser
un patch devenu vulnérable. Les lignes sont retenues ; les patches exacts et
versions transitives deviennent vérifiés seulement après bootstrap. Une
incompatibilité exige une correction documentée, pas un contournement silencieux.

## 5. Intégrations et modes

FreeLLMAPI existant : URL configurée exclusivement serveur, clé hors repo ;
pas de copie de son installation. La connectivité depuis les containers sera
vérifiée T21, avec réseau Docker partagé contrôlé si possible ; ne pas rendre
le port de passerelle public et ne pas supposer que localhost du worker est
celui de l'hôte. Ne pas démarrer ni modifier cette installation pendant la
phase contrats. Embeddings et OCR sont des capacités séparées à tester.

Mode `live` : services configurés, collecte réelle, modèle/fournisseur effectifs,
sortie validée. Mode `preloaded` : résultats fictifs identifiés et versionnés,
aucune animation ou trace affirmant un appel non exécuté. Absence de clé en
mode live produit un incident de configuration ; pas de fallback silencieux
vers fixtures. Le démarrage général doit rester possible sans clé.

## 6. Vérifications avant fondations

Tous les liens de contrats résolus, OpenAPI de conception validé, sept oracles
recalculés, décisions détaillées et définition de terminé présente. Les
docs officielles confirment des prérequis ; elles ne prouvent pas le runtime
intégré, Docker, les modèles ou la CI de ce dépôt. G1 demande cette preuve.

Sources officielles consultées le 2026-10-03 :

- [Next.js installation](https://nextjs.org/docs/app/getting-started/installation)
  et [passage à v16](https://nextjs.org/docs/app/guides/upgrading/version-16) :
  minimum Node 20.9 et ligne React 19.2 ; Node 24 retenu par le projet.
- [Versions Node](https://nodejs.org/en/about/previous-releases) : Node 24 LTS.
- [Python 3.13](https://docs.python.org/3.13/whatsnew/3.13.html) : ligne de runtime cible.
- [Compatibilité pnpm](https://pnpm.io/installation) : pnpm 10 et Node 24.
- [Verrouillage uv](https://docs.astral.sh/uv/concepts/projects/sync/) :
  `--locked` contrôle la fraîcheur ; `--frozen` ne remplace pas ce contrôle.
- [Versions FastAPI](https://fastapi.tiangolo.com/deployment/versions/) et
  [releases](https://fastapi.tiangolo.com/release-notes/) : pin de version,
  résolution Starlette et candidate 0.142.2.
- [Support PostgreSQL](https://www.postgresql.org/support/versioning/) et
  [SELECT/locking](https://www.postgresql.org/docs/17/sql-select.html) : ligne 17
  supportée et SKIP LOCKED ; la garantie métier reste à tester.
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/intro.html) : ORM retenu.
- [openapi-typescript](https://openapi-ts.dev/introduction) : support OpenAPI
  3.1 et génération de types ; choix de contrat unique côté serveur.
