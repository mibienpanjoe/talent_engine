# Talent Engine — Carte documentaire et organisation proposée

**Date :** 2026-10-03  
**Statut :** structure documentaire ; contrats T01–T06 présents, runtime non créé.
Les fichiers non signalés comme présents restent des cibles.

## 1. Point d'entrée actuel

Lire dans cet ordre :

1. [Project overview](product/project-overview.md) : vision, parcours et périmètre source.
2. [Evaluation engine specification](evaluation/evaluation-engine-spec.md) : complément proposé pour le moteur.
3. [Analyse initiale](product/project-analysis.md) : objectifs, points solides et contrats manquants.
4. [Registre des décisions](product/decision-register.md) : arbitrages à traiter.
5. [Cadrage MVP](product/mvp-requirements-and-acceptance.md) : exigences et acceptation proposées.
6. [Structure du dépôt proposée](architecture/repository-structure.md) : arborescence, responsabilités et choix à trancher.
7. [Contrat campagne/formulaire](campaigns/campaign-and-form-contract.md) : snapshots, gel, questions, publication et concurrence ; comportement à implémenter.

Le cadrage produit est classé sous `docs/product/` et la spécification du moteur
sous `docs/evaluation/`. Ils restent utiles : le premier porte la vision et
le parcours global ; le second détaille le moteur et ses exemples. Le cadrage est mis à jour pour
refléter les décisions explicites ; les propositions du moteur restent ouvertes.
Les nouveaux documents restent en français pour suivre la langue des sources ;
cette convention est révisable.

## 2. Structure documentaire cible

Cette arborescence décrit la cible ; elle ne représente pas les fichiers
présents sur disque.

```text
README.md                                 présentation et démarrage vérifié
CONTRIBUTING.md                            présent : contribution et définition de terminé
SECURITY.md                                présent : accès, collecte et purge
docs/
  documentation-map.md                    présent : navigation et structure proposée
  product/
    project-overview.md                   présent : vision et cadrage source
    project-analysis.md                   présent : analyse des sources
    decision-register.md                  présent : décisions ouvertes
    mvp-requirements-and-acceptance.md     présent : exigences et critères proposés
    roadmap.md                            tranches démontrables et dépendances
  campaigns/
    campaign-and-form-contract.md         présent : besoin, questions, versions et publication
  applications/
    submission-contract.md                présent : réception, fichiers et idempotence
  evaluation/
    evaluation-engine-spec.md             présent : spécification source du moteur
    evaluation-contract.md                présent : états, admissibilité et score
    policies-and-rubrics.md                présent : compilation, poids et barèmes
    evidence-and-provenance.md             extraits, références et sources répétées
  review/
    review-and-corrections.md              présent : files, corrections et versions
  data/
    canonical-model.md                    présent : entités, relations et invariants
    data-dictionary.md                    présent : types, nullabilité et versions
  architecture/
    repository-structure.md               présent : proposition d'organisation du code
    system-architecture.md                présent : modules, outils et runtime cible
    api-contract.md                       présent : routes et OpenAPI de conception
  integrations/
    document-and-web-extraction.md        PDF, OCR, portfolios et GitHub bornés
    ai-adapters.md                        génération, embeddings et OCR
    local-freellmapi.md                    présent : installation et limites vérifiées
  operations/
    analysis-lifecycle.md                 présent : tâches, tentatives et reprise
    local-development.md                  démarrage réel et modes de démonstration
  design/
    visual-identity.md                    présent : direction sombre proposée
    brand-assets.md                       présent : assets, usages et vérifications
    references/
      talent-engine-signal-identity.png   présent : référence fournie par le mainteneur
  testing/
    acceptance-and-reference-cases.md     fixtures, oracles, parcours et essais modèles
  adr/
    0001-application-nextjs-fastapi-postgresql.md  présent : stack retenue
    0002-monorepo-web-et-api.md            présent : monorepo retenu
    0003-tooling-and-contract-generation.md      présent : outils et génération
    0004-postgresql-analysis-worker.md            présent : worker durable
    NNNN-title.md                         décisions suivantes
```

Créer chaque document lorsqu'il possède un contenu utile, des dépendances
identifiées et un propriétaire de contrat. Éviter les fichiers vides et les
copies de l'overview.

Les schémas HTTP typés se trouvent dans
[contracts/api-design.openapi.json](../contracts/api-design.openapi.json),
contrat manuel de conception distinct du futur export serveur. Les oracles
numériques fictifs sont sous `fixtures/expected-results/`.

## 3. Ordre de rédaction et provenance

| Ordre | Documents | Sources initiales | Décisions nécessaires |
| --- | --- | --- | --- |
| 1 | Exigences MVP et acceptation | Overview §§1–9, 14 et 16 ; moteur §§1–2 et 9. | DEC-01. |
| 2 | Campagne, soumission, évaluation et revue | Overview §§5–9 ; moteur §§3–10. | DEC-02 à DEC-07 ; détails de DEC-09. |
| 3 | Modèle canonique et dictionnaire | Overview §13 et contrats de l'étape 2. | Identifiants, relations, versions et nullabilité. |
| 4 | Architecture, API, exécution et sécurité | Overview §§11–15 ; moteur §10 ; contrats précédents. | DEC-08 à DEC-10. |
| 5 | Extraction et adaptateurs IA | Overview §§7 et 12 ; moteur §§4 et 11. | DEC-10 et DEC-11 après essais. |
| 6 | Design, fixtures et acceptation du parcours | Overview §§10 et 16 ; moteur §§7–9 et 11. | DEC-05, DEC-06 et DEC-12. |
| 7 | Roadmap, contribution et documentation de démarrage | Ensemble des contrats ; commandes réellement disponibles. | DEC-01, DEC-13 et preuves d'exécution. |

Les cas attendus et les parcours d'écran peuvent se préciser dès l'étape 1.
La documentation des commandes attend une application exécutable : aucun
script de build, test ou démarrage ne doit être présenté comme existant avant
sa création et sa vérification.

## 4. Conventions de documentation

- Distinguer position source, proposition, décision acceptée et comportement vérifié.
- Définir les exigences avec un identifiant stable, leur source et une acceptation observable.
- Donner à chaque contrat une responsabilité principale ; les autres documents y renvoient.
- Conserver inconnues, échecs techniques et décisions humaines comme états distincts.
- Documenter les versions de configuration, politique, modèle, prompt et sources.
- Résoudre explicitement un conflit entre sources ; ne pas appliquer une priorité implicite.
- Consigner les choix techniques coûteux dans des ADR proposées puis acceptées.
- Mettre à jour le document propriétaire lorsque son contrat change.
- Signaler les fixtures préchargées et les essais réellement exécutés.

## 5. Structure applicative indicative

L'overview propose `apps/web/`, `apps/api/`, `fixtures/`, `.env.example` et
`compose.yaml`. Cette base est cohérente avec la stack Next.js/FastAPI retenue.
La [proposition de structure](architecture/repository-structure.md) précise les
emplacements, les responsabilités et les choix à trancher. Aucun squelette
applicatif n'est créé pendant cette discussion.

Le découpage métier de l'analyse organise les responsabilités à l'intérieur
de l'application. Il n'impose pas un service distinct par domaine. Une table
de tâches persistante reste à concevoir selon les garanties du parcours.

Le dossier `tasks/`, s'il est utilisé ultérieurement pour le travail local,
reste distinct de la documentation durable sous `docs/`.

Les assets partagés de marque sont conservés dans `assets/brand/` et décrits
dans [le guide des assets](design/brand-assets.md). Leurs intégrations dans le
frontend seront ajoutées au bootstrap.

## 6. Lecture de la phase contrats terminée

Après le contrat de campagne, lire :

- [Politiques et barèmes](evaluation/policies-and-rubrics.md),
  [évaluation](evaluation/evaluation-contract.md),
  [revue/corrections](review/review-and-corrections.md).
- [Réception](applications/submission-contract.md),
  [exécution](operations/analysis-lifecycle.md), [sécurité](../SECURITY.md).
- [Modèle](data/canonical-model.md), [dictionnaire](data/data-dictionary.md),
  [API](architecture/api-contract.md).
- [Architecture](architecture/system-architecture.md),
  [contribution](../CONTRIBUTING.md), ADR-0003/0004.

Les textes initialement proposés conservent leur contexte historique ; les
contrats propriétaires détaillés fixent maintenant les règles de réalisation.
Les capacités d’intégration et de runtime attendent leurs preuves dédiées.
