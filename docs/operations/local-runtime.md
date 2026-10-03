# Runtime local des fondations

Prérequis : Docker Compose, Node 24, pnpm 10.28.0, Python 3.13 et uv 0.12.

1. Copier `.env.example` vers `.env` et renseigner `TALENT_DB_PASSWORD` et `TALENT_CSRF_SECRET` avec deux valeurs aléatoires hexadécimales distinctes. Ne pas committer `.env`.
2. `make up` construit et démarre PostgreSQL 17, l’API et le frontend.
3. `make migrate` applique explicitement les migrations. Le démarrage API ne modifie pas le schéma.
4. Ouvrir <http://localhost:3003>. Les requêtes `/api/v1/` passent par le proxy Next.js ; le port API 8001 sert au diagnostic local.
5. `make down` arrête les services et conserve les données. `docker compose down --volumes` supprime les données du projet Compose : réserver cette commande à une base de test jetable.

Les ports publiés écoutent uniquement sur loopback. PostgreSQL n’est pas publié.
Aucun LLM ni worker n’est nécessaire aux fondations. Le worker sera ajouté avec les tâches d’analyse ; il partagera le package et l’image de l’API. Le stockage privé sera ajouté avec la réception des fichiers.

Hors Docker : `make install`, puis configurer `TALENT_DATABASE_URL` avec une URL `postgresql+psycopg://…`. Lancer `uv run --project apps/api uvicorn talent_engine.main:create_app --factory`, et `pnpm --filter @talent-engine/web dev`. Le proxy utilise `http://127.0.0.1:8000` par défaut.

`make check` exécute les tests API, Ruff, la fraîcheur des contrats, TypeScript et le build. Le contrôle réel PostgreSQL s’exécute après migration avec `uv run --project apps/api python apps/api/checks/check_database.py` sur une base isolée configurée via `TALENT_DATABASE_URL`.

Références : [uv dans Docker](https://docs.astral.sh/uv/guides/integration/docker/), [Next.js standalone](https://nextjs.org/docs/app/api-reference/config/next-config-js/output), [migrations Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

## Accès responsable

Configurer `TALENT_REVIEWER_LOGIN` et `TALENT_REVIEWER_PASSWORD` dans `.env`, puis `make seed-access` après migration. Le mot de passe contient au moins 12 caractères et reste hors Git. Relancer ce seed change le mot de passe du même compte et révoque ses sessions ; aucun second compte n’est créé.

L’origine publique configurée doit correspondre exactement à l’adresse ouverte dans le navigateur (`http://localhost:3003` par défaut). HTTP local n’est accepté que sur loopback. Hors développement local, HTTPS et cookie Secure sont requis. La page `/review` vérifie la session côté serveur ; les mutations API contrôlent également Origin et CSRF.

Les compteurs de login utilisent l’adresse du pair réseau et ignorent les en-têtes forwarded non fiables. Derrière le proxy Next local, la limite IP est donc conservatrice et partagée entre visiteurs ; le compteur par compte reste distinct. Une exposition Internet devra définir explicitement une chaîne de proxy de confiance avant d’utiliser l’IP transmise.

`make integration-test` requiert `TALENT_TEST_DATABASE_URL` pointant sur une base loopback jetable dont le nom se termine par `_test`. Chaque test d’accès utilise son propre schéma, retiré ensuite. Aucune purge de données applicatives n’est exécutée.

En cas de rotation de `TALENT_CSRF_SECRET`, réinitialiser le même compte avec `make seed-access` pour révoquer ses sessions avant de redémarrer l’API avec le nouveau secret. Ne jamais conserver les sessions d’avant rotation.
