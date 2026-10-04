# Runtime local des fondations

Prérequis : Docker Compose, Node 24, pnpm 10.28.0, Python 3.13 et uv 0.12.

1. Copier `.env.example` vers `.env` et renseigner `TALENT_DB_PASSWORD` et `TALENT_CSRF_SECRET` avec deux valeurs aléatoires hexadécimales distinctes. Ne pas committer `.env`.
2. `make up` construit et démarre PostgreSQL 17, l’API et le frontend.
3. `make migrate` applique explicitement les migrations. Le démarrage API ne modifie pas le schéma.
4. Ouvrir <http://localhost:3003>. Les requêtes `/api/v1/` passent par le proxy Next.js ; le port API 8001 sert au diagnostic local.
5. `make down` arrête les services et conserve les données. `docker compose down --volumes` supprime les données du projet Compose : réserver cette commande à une base de test jetable.

Les ports publiés écoutent uniquement sur loopback. PostgreSQL n’est pas publié.
Le worker partage l’image API et le stockage privé des documents. La réception
reste disponible sans passerelle LLM ; les appréciations automatiques requièrent
la configuration serveur décrite dans la [note FreeLLMAPI](../integrations/local-freellmapi.md).

Hors Docker : `make install`, puis configurer `TALENT_DATABASE_URL` avec une URL `postgresql+psycopg://…`. Lancer `uv run --project apps/api uvicorn talent_engine.main:create_app --factory`, et `pnpm --filter @talent-engine/web dev`. Le proxy utilise `http://127.0.0.1:8000` par défaut.

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

`docker compose logs worker` montre les événements JSON sans données candidates.
`docker compose run --rm worker python -m talent_engine.analyses.worker --once`
traite au plus une étape éligible. Le nettoyage des temporaires est périodique ;
une exécution ponctuelle utilise `python -m talent_engine.documents.cleanup`
dans le service worker, avec son environnement et son volume.

Réponses, sources extraites et évaluation sont checkpointées. Les PDF textuels
et réponses alimentent les appréciations ; scans et images indiquent encore
qu’un OCR est requis. Sans passerelle configurée, un besoin d’appel modèle
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
pas provenir d’un appel modèle. Le jeu de démonstration distribuable reste à
implémenter dans la phase dédiée.
