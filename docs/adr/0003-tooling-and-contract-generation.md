# ADR-0003 — Outils du monorepo et génération du client

**Statut :** retenu pour implémentation de la phase contrats ; installation non vérifiée.
**Date :** 2026-10-03.
**Décision source :** demande du mainteneur d'exécuter toute la phase contrats ;
détails choisis pour préparer le bootstrap, sans attribuer une confirmation
individuelle du mainteneur à chaque version.

## Contexte

Stack et monorepo sont acceptés dans ADR-0001/0002. T06 doit arrêter les outils,
frontières et conventions tout en séparant ce choix d'un runtime installé.
Deux écosystèmes nécessitent des locks distincts et un contrat serveur unique.

## Décision

- pnpm 10 pour workspace TypeScript, uv 0.12 pour package Python.
- Node 24 LTS, Next.js 16/React 19.2, CPython 3.13, PostgreSQL 17.
- FastAPI 0.142/Pydantic 2, SQLAlchemy 2.0/psycopg 3/Alembic 1.
- API REST versionnée, schémas stricts et OpenAPI 3.1 serveur ; types via
  openapi-typescript 7, consommateur openapi-fetch dans le frontend.
- Locks suivis, versions runtime et outils exactes enregistrées, images
  figées au bootstrap. Candidats précis et sources dans
  [l'architecture](../architecture/system-architecture.md).
- Makefile comme entrées communes ; ses commandes ne sont annoncées comme
  exécutables qu'après création et vérification.

## Alternatives considérées

npm/pip sont possibles, mais pnpm/uv suivent la proposition du dépôt et
conservent une installation verrouillée par écosystème. Des DTO TypeScript
écrits manuellement créeraient un second contrat à synchroniser. Un SDK partagé
hors frontend n'est pas justifié par un deuxième consommateur aujourd'hui.

## Conséquences

T07/T08 doivent résoudre et tester les patches exacts, générer locks/types
et refuser la dérive. Les fichiers `tasks/` restent hors versionnement ;
le contrat de conception manuel ne devient pas un export FastAPI fictif.
Cette ADR complète les détails ouverts des ADR précédentes sans changer stack
ou structure du dépôt. Aucune commande d'installation exécutée n'est sous-entendue.
