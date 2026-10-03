# ADR-0002 — Monorepo pour le frontend et le backend

**Statut :** accepté pour l'organisation du dépôt.  
**Date :** 2026-10-03  
**Décision source :** le mainteneur choisit « One monorepo with apps/web and apps/api ».

## Contexte

Le MVP est développé par un mainteneur avec l'assistant. Il possède un frontend
Next.js et un backend FastAPI, ainsi que des contrats, fixtures et une
documentation qui évoluent ensemble.

La [proposition de structure](../architecture/repository-structure.md) rend
explicites les responsabilités et les autres choix encore ouverts.

## Décision

Un seul dépôt contient :

- `apps/web/` : application Next.js/TypeScript ;
- `apps/api/` : application FastAPI/Python ;
- `docs/` : documentation et décisions ;
- `fixtures/` : dossiers et données fictifs partagés.

La séparation en deux dépôts n'est pas retenue. API et frontend peuvent évoluer
dans une même modification, avec leurs contrôles respectifs.

## Conséquences

Chaque écosystème garde ses dépendances et sa configuration. Le dépôt possède
une organisation commune pour ses contrats, sa démonstration et son démarrage.

L'emplacement du worker, les outils de dépendances et le détail de la structure
interne étaient proposés à la date de cette décision ; ils sont maintenant
complétés dans [ADR-0003](0003-tooling-and-contract-generation.md) et
[ADR-0004](0004-postgresql-analysis-worker.md). Leur runtime reste à vérifier.
