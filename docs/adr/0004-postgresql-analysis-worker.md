# ADR-0004 — Worker Python et tâches PostgreSQL

**Statut :** retenu pour implémentation ; exécution et reprise non vérifiées.
**Date :** 2026-10-03.
**Décision source :** phase contrats demandée par le mainteneur ; réception
durable et reprise imposées par REQ-SUB-01/02 et REQ-JOB-01.

## Contexte

La confirmation candidat doit survivre aux pannes externes. Une tâche en
mémoire ou envoyée après commit peut perdre l'analyse. Le petit MVP n'a pas
besoin d'un broker supplémentaire, mais requiert des garanties explicites.

## Décision

API et worker exécutent le même package/image Python dans deux processus.
Réception et tâche initiale sont committées ensemble dans PostgreSQL. Le worker
acquiert avec SKIP LOCKED, lease/génération, checkpoints et tentatives bornées
suivant le [contrat d'exécution](../operations/analysis-lifecycle.md).

Appels externes hors transaction ; chaque finalisation vérifie fencing et
dossier non supprimé. Une réanalyse produit une base immuable disponible à
activer, sans effacer les corrections. Purge durable/reprenable via la même
infrastructure de contrôle, avec budgets de nettoyage distincts d'une analyse.

## Alternatives considérées

BackgroundTasks/in-memory ne garantissent pas reprise après redémarrage.
Redis/Celery ou un autre broker peuvent devenir pertinents pour volumes
supérieurs, mais ajoutent une coordination inutile au chemin de réception
initial. L'analyse synchrone rendrait la confirmation dépendante des API.

## Conséquences

Les tests d'acquisition, concurrence, crash, clôture et suppression emploient
PostgreSQL réel ; SQLite n'est pas une preuve de ses verrous. Les appels
externes peuvent se répéter après crash ; l'effet persistant est unique, sans
promesse d'exactly-once fournisseur. SQL et stockage privé nécessitent une
purge idempotente, pas une transaction distribuée supposée.
