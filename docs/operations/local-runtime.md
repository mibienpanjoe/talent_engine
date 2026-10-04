# Installation et runtime local

Pour Compose : Docker avec Compose et GNU make. Pour les outils de développement
hôte : Node 24, pnpm 10.28.0, Python 3.13 et uv 0.12.15. Les images installent
leurs propres dépendances verrouillées.

Copier `.env.example` vers `.env`, puis renseigner `TALENT_DB_PASSWORD` et
`TALENT_CSRF_SECRET` avec deux valeurs aléatoires hexadécimales distinctes
(par exemple deux appels à `openssl rand -hex 32`). Renseigner également
`TALENT_REVIEWER_LOGIN` et `TALENT_REVIEWER_PASSWORD` (au moins 12 caractères).
Ne pas committer `.env` ; limiter ses droits de lecture.

```sh
docker compose build
make migrate
make seed-access
make up
make seed-demo
```

Le service de migration démarre PostgreSQL 17 et attend sa disponibilité.
La migration précède les services applicatifs ; le démarrage API ne modifie
pas le schéma. `make up` démarre API, web et worker et réutilise le build.
`make seed-demo` initialise les démonstrations sans clé, de façon idempotente.

Ouvrir <http://localhost:3003> et se connecter avec les identifiants choisis.
Les requêtes `/api/v1/` passent par le proxy Next.js ; le port API 8001 sert au
diagnostic local. Changer les ports via `TALENT_API_PORT`/`TALENT_WEB_PORT`
nécessite aussi l’origine publique correspondante.

`make down` arrête les services et conserve les données.
`docker compose down --volumes` supprime les données du projet Compose :
réserver cette commande à une base de test jetable.

Les ports publiés écoutent uniquement sur loopback. PostgreSQL n’est pas publié.
Le worker partage l’image API et le stockage privé des documents. La réception
reste disponible sans passerelle LLM ; les appréciations automatiques requièrent
la configuration serveur décrite dans la [note FreeLLMAPI](../integrations/local-freellmapi.md).

Pour travailler sur le code, `make install` installe les dépendances hôte
avec locks vérifiés. Les processus hôte ne chargent pas automatiquement le
fichier Compose `.env` : exporter `TALENT_DATABASE_URL` vers une base PostgreSQL,
`TALENT_PUBLIC_ORIGIN`, `TALENT_LOCAL_DEVELOPMENT=true` et `TALENT_CSRF_SECRET`.
Les identifiants initiaux doivent aussi être exportés pour le seed d’accès.
Les commandes de développement disponibles sont :

```sh
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api python -m talent_engine.seed_access
uv run --project apps/api uvicorn talent_engine.main:create_app --factory
pnpm --filter @talent-engine/web dev --port 3003
```

Le proxy utilise `http://127.0.0.1:8000` par défaut, configurable via
`TALENT_API_ORIGIN`. Le worker hôte est un processus distinct :
`uv run --project apps/api python -m talent_engine.analyses.worker`.
La recette propre ci-dessous porte sur Compose ; ces alternatives sont les
points d’entrée disponibles, pas une seconde recette d’installation exécutée.

`make check` exécute les tests API, Ruff, la fraîcheur des contrats, TypeScript et le build. Le contrôle réel PostgreSQL s’exécute après migration avec `uv run --project apps/api python apps/api/checks/check_database.py` sur une base isolée configurée via `TALENT_DATABASE_URL`.

Références : [uv dans Docker](https://docs.astral.sh/uv/guides/integration/docker/), [Next.js standalone](https://nextjs.org/docs/app/api-reference/config/next-config-js/output), [migrations Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

## Accès responsable

Configurer `TALENT_REVIEWER_LOGIN` et `TALENT_REVIEWER_PASSWORD` dans `.env`, puis `make seed-access` après migration. Le mot de passe contient au moins 12 caractères et reste hors Git. Relancer ce seed change le mot de passe du même compte et révoque ses sessions ; aucun second compte n’est créé.

L’origine publique configurée doit correspondre exactement à l’adresse ouverte dans le navigateur (`http://localhost:3003` par défaut). HTTP local n’est accepté que sur loopback. Hors développement local, HTTPS et cookie Secure sont requis. La page `/review` vérifie la session côté serveur ; les mutations API contrôlent également Origin et CSRF.

Les compteurs de login utilisent l’adresse du pair réseau et ignorent les en-têtes forwarded non fiables. Derrière le proxy Next local, la limite IP est donc conservatrice et partagée entre visiteurs ; le compteur par compte reste distinct. Une exposition Internet devra définir explicitement une chaîne de proxy de confiance avant d’utiliser l’IP transmise.

`make integration-test` requiert `TALENT_TEST_DATABASE_URL` pointant sur une base loopback jetable dont le nom se termine par `_test`. Chaque test d’accès utilise son propre schéma, retiré ensuite. Aucune purge de données applicatives n’est exécutée.

En cas de rotation de `TALENT_CSRF_SECRET`, réinitialiser le même compte avec `make seed-access` pour révoquer ses sessions avant de redémarrer l’API avec le nouveau secret. Ne jamais conserver les sessions d’avant rotation.

## Worker et documents privés

Après `make migrate`, `make up` démarre aussi le worker persistant. API et
worker partagent `private_uploads`, jamais le serveur web. Les documents ne
sont téléchargés que par la route privée authentifiée. Les volumes PostgreSQL
et documents sont conservés par `make down`.

Les événements JSON privés du worker se lisent avec :
`docker compose exec worker cat /app/private-logs/worker.jsonl`.
Le volume `technical_logs` applique une rotation horaire et une rétention de
sept jours ; Compose désactive la copie des journaux du worker dans Docker.
`docker compose run --rm worker python -m talent_engine.analyses.worker --once`
traite au plus une étape éligible. Le nettoyage des temporaires est périodique ;
une exécution ponctuelle utilise `python -m talent_engine.documents.cleanup`
dans le service worker, avec son environnement et son volume.

Réponses, sources extraites et évaluation sont checkpointées. Les PDF textuels
et réponses alimentent les appréciations ; scans et images passent par un OCR
conditionnel, avec état par page et modèle effectif conservés. Sans passerelle configurée, un besoin d’appel modèle
produit un incident explicite, sans perdre la candidature ni inventer de score.

## Revue sourcée

La liste privée propose tous les dossiers, les prêts à examiner, les dossiers
à vérifier et les conditions non satisfaites. Les deux dernières files peuvent
se chevaucher. Les compteurs portent sur toute la campagne ; les filtres de
décision et traitement s’appliquent ensuite à la liste. Les essais privés sont
exclus de ces files et du classement.

Le classement des prêts à examiner utilise le rapport exact avant arrondi,
avec des rangs de compétition (1, 1, 3). Une panne technique ultérieure ne
remplace pas un résultat effectif. Une liste paginée modifiée doit être rechargée.

La fiche distingue score éventuel, couverture, disponibilité, décision humaine
et traitement. Les preuves citées ouvrent le texte réellement conservé avec
page ou réponse d’origine ; les documents restent accessibles uniquement au
propriétaire connecté. Un résultat préchargé indique son origine et ne prétend
pas provenir d’un appel modèle. Les deux domaines sont disponibles via
`make seed-demo` ; voir les
[démonstrations](../testing/demonstrations.md) pour les profils fictifs, les modes
préchargé/réel et la recette de revue.

## Démonstrations et dépannage

`make seed-demo` produit sept dossiers fictifs explicitement préchargés ;
il ne nécessite pas FreeLLMAPI et ne fait aucun appel modèle. Le mode live
crée des dossiers neufs à traiter par le worker. Les commandes, documents,
liens optionnels et étapes de correction/décision sont décrits dans le
[guide de démonstration](../testing/demonstrations.md).

- Connexion refusée : vérifier origine exacte, identifiants initiaux et seed d’accès après migration.
- Dossier reçu mais incident `llm_not_configured` : configurer le complément serveur FreeLLMAPI, puis relancer dans la fiche ; le dossier reste enregistré.
- Modèle indisponible ou sortie invalide : consulter état, code assaini et tentatives ; aucune panne ne devient une note zéro.
- Page indisponible : attendre le retour du service et utiliser Réessayer, qui refait une navigation serveur.
- Configuration figée : dupliquer la campagne pour changer questions ou politique.

Les sources nécessitant JavaScript, les données privées et l’exécution de
code candidat sont hors collecte. Une citation traçable ne garantit pas une
interprétation correcte ; vérifier le barème et conserver la décision humaine.
La passerelle peut router vers un fournisseur distant et ses coûts ne sont
pas établis par la démonstration.

## Preuve d’installation

Le 4 octobre 2026, une archive propre du code `8d5d9b6`, nouveaux secrets,
ports et volumes, a exécuté les commandes Compose ci-dessus. Installation
hôte verrouillée, images, migration 0018, accès, deux seeds sans doublons et
`make check` ont réussi. Les 26 tables/colonnes correspondent au modèle.
Les dossiers préchargés sans clé et deux nouveaux dossiers sans passerelle
ont été consultés ; ces derniers restent en incident sans faux score.
Deux autres dossiers ont terminé une analyse réelle via Groq avec preuves,
corrections et décisions rendues en navigateur. Voir la
[recette complète](../testing/acceptance-and-reference-cases.md).

Cette preuve concerne le démarrage local Compose avec cache d’images et
connexion réseau disponibles. Les images et dépendances verrouillées ont été
installées ;
la sortie du fournisseur et les scores qualitatifs ne sont pas garantis
identiques entre appels. Aucun hébergement public n’est livré par cette recette.
