<p align="center">
  <img src="assets/brand/app-icon-dark-accent.png" width="112" height="112" alt="Icône Talent Engine : trois cercles et un signal bleu" />
</p>

<h1 align="center">Talent Engine</h1>

<p align="center">
  <strong>Des candidatures compréhensibles, une revue éclairée.</strong><br />
  Qualification explicable pour les programmes de formation et les recrutements.
</p>

<p align="center">
  <a href="docs/operations/local-runtime.md"><strong>Démarrer en local</strong></a>
  · <a href="docs/documentation-map.md">Documentation</a>
  · <a href="docs/evaluation/evaluation-engine-spec.md">Moteur d'évaluation</a>
  · <a href="docs/product/decision-register.md">Décisions</a>
</p>

Talent Engine aide un responsable à décrire une opportunité, recueillir des
candidatures et comprendre l'adéquation des dossiers à son besoin. Chaque
appréciation retrouve ses éléments justificatifs ; les informations manquantes
restent visibles, et la décision de sélection appartient au responsable.

Le projet est préparé pour le mini-challenge développeurs SKULLVI du Human
Capital Program de GevConsulting. La démonstration cible une formation en
développement et un recrutement marketing junior.

## État du projet

Les contrats métier et HTTP sont documentés. Les fondations proposent une
API FastAPI, PostgreSQL avec migrations, un frontend Next.js, un accès
responsable par session serveur et un runtime Docker Compose. Le client
TypeScript est généré depuis l’API réellement implémentée.

Les campagnes, candidatures, sources et évaluations du parcours ci-dessous
restent à implémenter. L’accès responsable est le parcours actuellement
exécutable ; il ne constitue pas encore une démonstration complète du MVP.

Le périmètre complet est décrit dans les
[exigences et critères d'acceptation](docs/product/mvp-requirements-and-acceptance.md).
Les barèmes chiffrés sont des exemples fictifs à calibrer.

## Démarrer les fondations

Docker Compose est requis. Copier `.env.example` vers `.env`, renseigner deux
secrets aléatoires distincts pour la base et CSRF ainsi que les identifiants du
responsable, puis :

```sh
make up
make migrate
make seed-access
```

Ouvrir <http://localhost:3003> et se connecter. `make down` conserve les données.
Voir le [guide local](docs/operations/local-runtime.md) pour les prérequis,
origines, limites du proxy local et tests. Les secrets restent hors Git.

## Parcours visé

```text
Créer une campagne et préciser les exigences
  → publier un formulaire adapté
  → enregistrer durablement une candidature
  → extraire documents, portfolios et dépôts GitHub fournis
  → apprécier les critères avec des éléments sourcés
  → consulter admissibilité, couverture et score éventuel
  → corriger une appréciation et prendre une décision humaine
```

Les capacités prévues comprennent la création guidée de campagnes, les
formulaires publics, l'extraction documentaire avec OCR conditionnel, la lecture
ciblée de liens et la revue des candidatures.

L'IA aide à extraire et apprécier les informations. Le backend possède les
politiques et calcule les scores. Une information absente n'est pas une note
zéro ; une panne d'analyse ne fait pas disparaître la candidature. Les scores
s'interprètent dans une campagne et servent à organiser la revue.

## Stack et organisation

| Élément | Choix retenu |
| --- | --- |
| Interface | Next.js, React et TypeScript |
| Métier et API | FastAPI et Python |
| Base de données | PostgreSQL |
| Dépôt | Monorepo avec `apps/web/` et `apps/api/` |
| Direction visuelle | Thème sombre, identité « Signal » |

La [structure détaillée](docs/architecture/repository-structure.md) et
l'[architecture système](docs/architecture/system-architecture.md) fixent les
responsabilités, pnpm/uv, les versions cibles et le worker Python avec tâches
PostgreSQL. Les commandes des fondations sont décrites dans le guide local ;
le worker arrivera avec les tâches d’analyse.

```text
assets/brand/    Logos, symboles, icône d'application et manifest
docs/           Produit, évaluation, architecture, design et décisions
apps/web/       Frontend Next.js et primitives accessibles
apps/api/       API FastAPI, accès responsable et migrations
```

FreeLLMAPI est la piste d'intégration côté serveur pour les appels LLM.
L'intégration et les modèles restent à vérifier ; la passerelle sera démarrée
lorsque nécessaire. Voir la [note d'intégration](docs/integrations/local-freellmapi.md).

## Documentation

- [Cadrage produit](docs/product/project-overview.md) : objectifs, parcours et périmètre.
- [Analyse initiale](docs/product/project-analysis.md) : points solides et contrats à préciser.
- [Spécification du moteur](docs/evaluation/evaluation-engine-spec.md) : états, calcul et cas de référence.
- [Registre des décisions](docs/product/decision-register.md) : choix retenus et arbitrages ouverts.
- [Identité visuelle](docs/design/visual-identity.md) et [assets de marque](docs/design/brand-assets.md).
- [Carte documentaire](docs/documentation-map.md) : navigation et documents à produire.

## Contribution

Le projet est développé par un mainteneur avec l'assistance d'outils de
développement. Les contrats et décisions servent de base au travail ; les
comportements implémentés devront être prouvés par des vérifications exécutées.
Les données de démonstration sont fictives et les secrets restent hors du dépôt.

## Licence

Aucune licence de réutilisation n'est définie à ce stade.
