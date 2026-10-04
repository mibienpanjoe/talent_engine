# Recette du MVP

Recette du 4 octobre 2026, après T32–T34.
Les [exigences](../product/mvp-requirements-and-acceptance.md) restent le périmètre
retenu. Le tableau distingue les tests isolés, PostgreSQL réel et le runtime
Compose avec fournisseur externe. Il ne constitue pas une validation de
production ou une calibration de sélection.

## Couverture

Les chemins de tests ci-dessous sont relatifs à `apps/api/`.

| Exigence | Preuve exécutée | Limite de la preuve |
| --- | --- | --- |
| REQ-ACC-01 | `integration/test_access.py` : sessions, CSRF, révocation, accès étranger refusé. Connexion réelle dans Compose. | Accès responsable local, pas de gestion multi-entreprises. |
| REQ-CAM-01 | `integration/test_campaigns.py` ; duplication, modification et sauvegarde visibles dans le navigateur courant. | Une campagne guidée fictive, pas une étude d’utilisabilité. |
| REQ-CAM-02 | `tests/test_campaign_schema.py`, `integration/test_campaigns.py` : sources liées et configuration incohérente refusée. | Contrats et validation serveur ; contrôle UI partagé. |
| REQ-CAM-03 | `integration/test_campaigns.py`, `integration/test_submissions.py` : transitions et courses publication/réception. Nouvelle campagne dupliquée et publiée dans Compose. | Configuration figée au premier dépôt réel ; titre affiché corrigible. |
| REQ-FRM-01 | Aperçu puis formulaire public courant : mêmes sept questions, ordre et contraintes. Même `QuestionRenderer`. | Le champ contact est propre au dépôt. |
| REQ-SUB-01 | `integration/test_submissions.py`, `integration/test_worker.py` : confirmation et persistance indépendantes du modèle. Dépôt public confirmé avant revue. | Aucun résultat inventé lors d’une panne. |
| REQ-SUB-02 | `integration/test_submissions.py` : rejeu, concurrence, conflit et reprise. Double clic navigateur : un dossier reçu. | La clé doit être réutilisée pour le même dépôt réseau. |
| REQ-SRC-01 | `integration/test_sources.py`, `integration/test_ocr_pipeline.py`. Runtime : PDF textuel et trois pages OCR du scan fictif d’Amina. | Transcription OCR à vérifier, budgets bornés. |
| REQ-SRC-02 | `tests/test_portfolio.py`, `tests/test_github.py` et intégrations correspondantes. Runtime : portfolio fourni et GitHub au commit identifié. | Texte accessible sans JavaScript ; lecture ciblée, contribution non déduite. |
| REQ-EVA-01 | `integration/test_campaigns.py`, `integration/test_evaluations.py` : snapshot et politique versionnés, poids compilés côté serveur. | Familles prédéfinies du MVP. |
| REQ-EVA-02 | `tests/test_assessments.py`, `integration/test_evaluations.py` : bornes, références, inconnues et zéro contrôlés. Citations réelles comparées aux pages, offsets et empreintes conservées. | Une citation valide ne garantit pas l’interprétation du modèle. |
| REQ-EVA-03 | `tests/test_evaluation.py`, `integration/test_reviews.py`, `integration/test_demo_seeding.py`. Chloé : score absent, couverture 65 %, bornes 58,75–93,75. | Cas fictif déterministe, pas une analyse externe. |
| REQ-EVA-04 | `tests/test_evaluation.py` : arithmétique rationnelle, répétitions sans bonus, rangs 1/1/3. Amina préchargée : 81,25. | Scores comparables au sein d’une politique commune seulement. |
| REQ-EVA-05 | `integration/test_reviews.py`, seed David : 93,75 et condition non satisfaite visibles simultanément dans Compose. | Aucun rejet automatique. |
| REQ-REV-01 | `integration/test_reviews.py` : files qui peuvent se recouper, rang global exact avant filtres, pagination liée au propriétaire et à la révision. Liste vide et liste reçue inspectées dans le navigateur. | Ordre de réception pour les dossiers à vérifier ; pas de classement de mérite dans cette file. |
| REQ-REV-02 | `integration/test_human_review.py`, `integration/test_review_reanalysis.py`. Corrections réelles Amina/Fatou et historique ; nouvelle valeur réouverte sans ancien défaut de niveau 3. | Base automatique conservée ; activation de réanalyse explicite. |
| REQ-REV-03 | `integration/test_human_review.py`. Amina présélectionnée ; Fatou non retenue avec score effectif absent. | Choix humains fictifs de recette. |
| REQ-JOB-01 | `integration/test_worker.py` : processus réellement tué, deux remplaçants, checkpoint réutilisé, fencing, tentatives bornées. `integration/test_review_reanalysis.py` : relance sans écraser la version effective. | Fournisseur absent dans le test de crash ; les appels externes sont prouvés séparément. |
| REQ-UX-01 | Runtime Next.js construit : formulaire public, liste, fiche et correction à 320px ; fiche à 768/1024/1440px. Dialogue : Tab/Shift+Tab piégés, Escape restitue le focus. 404 française et lien « Aller au contenu » ; API arrêtée temporairement : écran d’indisponibilité puis reprise de la liste après redémarrage. | Vérification ciblée, pas audit exhaustif de conformité WCAG ni lecteur d’écran. |
| REQ-DEMO-01 | `integration/test_demo_seeding.py`, deux seeds Compose identiques sans clé, puis deux nouvelles analyses développement/marketing avec fournisseur effectif identifié. | Fixtures pédagogiques distinctes des analyses réelles. |
| REQ-REL-01 | Archive propre du commit 8d5d9b6, nouvelles dépendances/env/volumes : install, images, migrations, accès et deux seeds identiques. Parcours sans clé puis deux nouveaux dossiers avec Groq, citations et revue navigateur. | Recette locale Compose, pas un déploiement Internet ; cache Docker et réseau fournisseur disponibles. |

## Contrôles de la version courante

`make check` passe : 81 tests unitaires, Ruff, ESLint, contrat OpenAPI généré,
types TypeScript et build Next.js. La suite unitaires + intégrations PostgreSQL
authentifié passe : 157 tests (81 + 76). Le test de crash lance et arrête de vrais
processus ; les pannes, réponses invalides et quotas fournisseurs restent des
scénarios contrôlés dans les tests d’adaptateurs. La CI distante doit être
vérifiée sur le SHA exact de la PR avant fusion.

Les couleurs effectives du navigateur donnent les contrastes suivants : texte
17,21:1 ; texte secondaire sur surface relevée 7,29:1 ; liens 8,97:1 ; bouton
principal 17,21:1 ; bordure des champs 3,85:1 ; focus 7,28:1. Ces mesures portent
sur les couples de couleurs utilisés, pas sur tous les états possibles.
Les captures 320px et 1440px ont été inspectées. Les dialogues restent dans
le viewport, avec défilement interne pour les formulaires longs.

Les corrections de recette portent sur la valeur initiale des corrections
humaines, leur réinitialisation après changement de révision, la lisibilité
des titres de dialogue, la ponctuation, les libellés des dossiers préchargés,
la page introuvable et le bouton Réessayer après une panne serveur. Ce dernier
refait une navigation complète au lieu de rejouer le rendu client en erreur. Le formulaire rend lui-même le statut facultatif ;
les libellés des nouvelles démonstrations ne le répètent plus.

## Pertinence et provenance

Les deux analyses réelles décrites dans les [démonstrations](demonstrations.md)
ont des citations appartenant à leur manifeste, reliées aux passages conservés
avec offsets et empreintes vérifiés. Le texte des appréciations a été comparé
aux exigences et aux passages : les lacunes de canal ou de contribution restent
identifiables. Marketing obtient 58,75 en réel contre 77,50 dans le jeu préchargé ;
cette différence reste visible et ne prouve pas une calibration.

Les appréciations peuvent varier entre appels et fournisseurs. Les corrections
humaines et inconnues restent nécessaires ; le modèle ne décide ni les poids,
ni le calcul, ni la sélection. Les limites réseau, OCR, tokens, sources omises
et modèles effectifs restent consultables dans le dossier.

## Installation propre

Une archive Git du commit `8d5d9b6`, sans `.env`, plans ni dépendances du
workspace, a été installée dans un répertoire séparé. `make install`,
`docker compose build`, `make migrate`, `make seed-access`, `make up` puis
deux `make seed-demo` ont réussi. Les migrations aboutissent à
`0018_action_lookup` ; les 26 tables et types/nullabilités de colonnes
correspondent au modèle. `make check` passe depuis cette installation.
Les identifiants, ports et volumes étaient propres à la recette.

Sans clé, les sept résultats préchargés sont consultables avec leur provenance
explicite. Deux dossiers neufs en mode live sans passerelle échouent avec
`llm_not_configured`, sans évaluation ni perte des pièces privées. Le navigateur
montre l’incident et propose la relance.

Après raccordement du worker à la passerelle existante, deux autres dossiers
neufs terminent avec Groq / openai/gpt-oss-120b : développement 91,25 et
marketing 58,75. Développement contient PDF textuel, scan OCR, portfolio et
GitHub ; marketing PDF et réponses. Les citations originales sont vérifiées
par page/chemin, offsets et empreintes. La revue navigateur corrige Amina au
niveau 2 (82,50) et la présélectionne ; Fatou passe à couverture 75 %, score
absent, puis Non retenu. Les événements persistent dans l’historique.

L’installation propre utilise une source applicative identique au dernier
code livré ; les changements T34 ultérieurs portent sur documentation et
commentaire de module. Les services de recette et leurs seuls volumes fictifs
sont retirés après validation ; le runtime de travail demeure distinct.
