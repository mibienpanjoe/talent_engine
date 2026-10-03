# Runtime local des fondations

Prérequis : Docker Compose, Node 24, pnpm 10.28.0, Python 3.13 et uv 0.12.

1. Copier `.env.example` vers `.env` et renseigner `TALENT_DB_PASSWORD` avec une valeur aléatoire hexadécimale. Ne pas committer `.env`.
2. `make up` construit et démarre PostgreSQL 17, l’API et le frontend.
3. `make migrate` applique explicitement les migrations. Le démarrage API ne modifie pas le schéma.
4. Ouvrir <http://localhost:3003>. Les requêtes `/api/v1/` passent par le proxy Next.js ; le port API 8001 sert au diagnostic local.
5. `make down` arrête les services et conserve les données. `docker compose down --volumes` supprime les données du projet Compose : réserver cette commande à une base de test jetable.

Les ports publiés écoutent uniquement sur loopback. PostgreSQL n’est pas publié.
Aucun LLM ni worker n’est nécessaire aux fondations. Le worker sera ajouté avec les tâches d’analyse ; il partagera le package et l’image de l’API. Le stockage privé sera ajouté avec la réception des fichiers.

Hors Docker : `make install`, puis configurer `TALENT_DATABASE_URL` avec une URL `postgresql+psycopg://…`. Lancer `uv run --project apps/api uvicorn talent_engine.main:create_app --factory`, et `pnpm --filter @talent-engine/web dev`. Le proxy utilise `http://127.0.0.1:8000` par défaut.

`make check` exécute les tests API, Ruff, la fraîcheur des contrats, TypeScript et le build. Le contrôle réel PostgreSQL s’exécute après migration avec `uv run --project apps/api python apps/api/checks/check_database.py` sur une base isolée configurée via `TALENT_DATABASE_URL`.

Références : [uv dans Docker](https://docs.astral.sh/uv/guides/integration/docker/), [Next.js standalone](https://nextjs.org/docs/app/api-reference/config/next-config-js/output), [migrations Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
