# ADR-0001 — Application Next.js, FastAPI et PostgreSQL

**Statut :** accepté pour la stack de base ; versions et détails ouverts.  
**Date :** 2026-10-03  
**Décision source :** le mainteneur retient la proposition TypeScript/Python,
Next.js et composants associés de l'overview.

## Contexte

Talent Engine doit démontrer la création d'une campagne, une candidature
persistante, une évaluation sourcée et une revue humaine. Le cadrage propose
une interface Next.js/React et un backend FastAPI/Python avec PostgreSQL.
Une alternative entièrement TypeScript était également présentée.

## Décision

- Interface : Next.js, React et TypeScript.
- API et logique métier : FastAPI et Python.
- Persistance relationnelle : PostgreSQL, conformément à la proposition retenue.
- Le calcul et les politiques ont une seule implémentation métier côté backend.
- Les versions, l'exécution des tâches et le détail du monorepo restent ouverts.

Le maintien d'un worker persistant est une proposition distincte à détailler.
Cette ADR ne valide pas des commandes, une installation ou un runtime existants.

## Alternatives considérées

Une application entièrement TypeScript était proposée pour éviter deux
langages. Le mainteneur a choisi la proposition TypeScript/Python ; aucune
supériorité mesurée de cette stack n'est affirmée.

## Conséquences

Les contrats API devront aligner les validations serveur et les types du client.
Le démarrage local devra couvrir frontend, API, base et exécution des analyses.
Les adaptateurs LLM resteront côté serveur ; le FreeLLMAPI installé est la
piste d'intégration actuelle, avec disponibilité et modèles à vérifier.
