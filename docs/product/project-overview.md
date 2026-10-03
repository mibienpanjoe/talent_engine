# Talent Engine — Project Overview

> Mini-challenge développeurs SKULLVI · GevConsulting — Human Capital Program
>
> Document de cadrage produit, fonctionnel, technique et visuel. Les fonctionnalités décrites constituent la cible de réalisation, pas un état d’implémentation. « Talent Engine » est le nom de travail.

## 1. Vision

Talent Engine permet à un responsable de définir une opportunité, publier un formulaire de candidature et retrouver des dossiers qualifiés, scorés et classés avec des explications consultables.

La promesse : **passer d’un ensemble de candidatures hétérogènes à une file de dossiers dont on comprend l’adéquation au besoin et les points à vérifier.**

Le produit couvre des programmes de formation et des recrutements. Il doit fonctionner pour la programmation, le marketing et d’autres domaines, sans exiger de modifier le code pour chaque nouvelle campagne.

L’IA intervient dans la compréhension et l’exploitation des informations. Les règles de qualification, le calcul du score et les politiques d’évaluation sont gérés dans le backend. Le responsable exprime son besoin ; il ne construit pas une grille de pondération technique.

## 2. Contexte et objectifs

Le challenge demande de recevoir les candidatures, collecter les informations essentielles, qualifier les profils, attribuer un score, classer les candidats et identifier les dossiers à examiner en priorité.

### Objectifs produit

- Rendre le responsable autonome dans la création et la publication d’une campagne.
- Proposer au candidat un formulaire clair, rapide à comprendre et utilisable sur mobile.
- Relier les informations collectées aux exigences réellement recherchées.
- Exploiter les réponses, documents et liens pertinents dans un dossier commun.
- Expliquer les résultats par critère et conserver leurs sources.
- Permettre une correction et une décision humaines.

### Objectifs de démonstration

- Montrer un parcours fonctionnel de bout en bout.
- Illustrer la flexibilité avec une formation en développement et un recrutement marketing.
- Défendre des choix de données, de scoring et d’architecture compréhensibles.
- Livrer une interface soignée, cohérente et agréable à utiliser.
- Fournir un dépôt documenté et reproductible en local, avec éventuellement une démo hébergée.

## 3. Décisions retenues et propositions ouvertes

| Sujet | Position |
| --- | --- |
| Création des campagnes | Interface guidée permettant au responsable d’être autonome. |
| Collecte | Formulaire public intégré et lien propre à chaque campagne. |
| Formulaires externes | Pas de dépendance à Tally ou à un autre fournisseur dans le MVP. |
| Domaines | Exigences configurables ; développement et marketing servent de cas de démonstration. |
| Évaluation | Logique et politiques côté backend ; aucun écran imposant poids et barèmes au responsable. |
| IA | Modèles spécialisés et LLM selon le besoin, consommés prioritairement par API. |
| Exécution | Application et base en local ; accès Internet nécessaire aux API et aux sources web. |
| Liens | Lecture ciblée des portfolios et des dépôts GitHub incluse dans le MVP. |
| Livrable | Dépôt local clair, documenté, avec données de démonstration ; déploiement facultatif. |
| Design | Direction sobre inspirée de Vercel et de la simplicité de Tally, avec shadcn/ui. |
| Stack retenue | Next.js / React / TypeScript, FastAPI / Python et PostgreSQL. Versions et détails à préciser. |
| Dépôt | Monorepo avec `apps/web/`, `apps/api/`, documentation et fixtures communes ; structure interne en discussion. |
| Thème | Le clair comme thème principal est écarté ; préférence pour une proposition sombre par défaut. |
| Intégration LLM | FreeLLMAPI déjà installé localement est la piste prioritaire ; disponibilité et modèles à vérifier. |
| Organisation | Mainteneur seul avec l'assistant ; périmètre MVP complet conservé. |
| À valider | Versions techniques, modèles, budget API, barèmes chiffrés, délai et volumes de référence. |

## 4. Utilisateurs et terminologie

**Responsable :** crée les campagnes, précise les exigences, consulte et révise les évaluations, prend les décisions de sélection.

**Candidat :** consulte une opportunité et soumet ses réponses, documents et réalisations. Proposition MVP : aucun compte candidat nécessaire.

Une **campagne** correspond à une opportunité ouverte aux candidatures. Une **exigence** décrit un élément recherché. Un **élément justificatif** est une réponse, un extrait de document ou de page qui renseigne cette exigence. Une **évaluation** rassemble les appréciations, les résultats calculés et les points à vérifier.

Le score exprime une adéquation documentée à une campagne. Il ne mesure pas la valeur générale d’une personne et ne se compare pas entre campagnes différentes.

## 5. Création guidée d’une campagne

### Étape 1 — Décrire l’opportunité

Champs : type d’opportunité, titre, domaine, description, niveau visé et date limite facultative.

Deux points de départ : **formation** et **recrutement**. Le vocabulaire et les suggestions s’adaptent : prérequis et objectifs d’apprentissage pour une formation ; missions et compétences attendues pour un recrutement. Le domaine reste extensible.

### Étape 2 — Préciser le profil recherché

Le responsable ajoute des exigences sous forme de blocs simples : compétence, expérience ou réalisation, disponibilité, autre condition.

Il décrit une attente concrète et choisit « indispensable » ou « souhaité ». Quand cela a du sens, une saisie adaptée précise le niveau ou la condition attendue. Exemple : une date pour la disponibilité, une capacité observable pour une compétence.

Exemples : « créer une API simple », « analyser les résultats d’une campagne marketing », « être disponible le samedi matin ». Les suggestions doivent être confirmées ; aucun critère n’est ajouté silencieusement par l’IA.

### Étape 3 — Ajuster le formulaire proposé

L’application assemble un formulaire à partir du besoin et de modèles de questions. Un même bloc de réalisation peut renseigner plusieurs exigences pour éviter un questionnaire trop long.

Types de champs MVP : texte court, texte long, email, nombre, date, choix simple ou multiple, URL et fichier. Le responsable peut ajouter, modifier, supprimer et réordonner les questions, puis définir celles qui sont obligatoires.

Chaque exigence est reliée en interne à une ou plusieurs sources attendues. Si une modification laisse une exigence sans source exploitable, l’interface propose une action : ajouter une question, associer une source ou revoir l’exigence.

Pas de constructeur visuel complexe nécessaire : liste éditable de questions et aperçu suffisent. Les suggestions initiales peuvent provenir de règles et de modèles de questions, sans appel LLM systématique.

### Étape 4 — Vérifier et publier

Récapitulatif de l’opportunité, des exigences et du formulaire ; aperçu mobile et ordinateur ; candidature de test identifiée comme telle ; publication et copie du lien public.

Le brouillon est enregistré automatiquement, avec un état visible. Proposition MVP : figer exigences et structure du formulaire après la première candidature réelle. Les changements descriptifs sans effet sur l’évaluation restent possibles ; une refonte du besoin passe par une duplication de campagne.

## 6. Parcours candidat

1. Ouvrir le lien public et comprendre l’opportunité, les attentes et les pièces demandées.
2. Renseigner les informations de contact et les réponses métier.
3. Ajouter les documents utiles et, si demandé, une ou deux réalisations pertinentes.
4. Pour chaque réalisation : titre, lien, contribution personnelle et bref contexte.
5. Vérifier puis envoyer ; obtenir une confirmation de réception indépendante de la fin de l’analyse.

Le formulaire est organisé en quelques sections lisibles. Une progression apparaît seulement si sa longueur le justifie. La validation conserve les réponses lors d’une erreur et indique exactement les champs à corriger.

Proposition de formats initiaux : PDF pour les CV et pièces principales, PNG/JPEG pour les scans. Les limites de taille et de nombre sont annoncées avant l’envoi. DOCX pourra être ajouté si nécessaire, sans devenir une dépendance du premier parcours fonctionnel.

Une candidature reçue reste enregistrée même si une API d’analyse est indisponible. Le candidat est informé de l’analyse automatisée et du recours éventuel à des prestataires externes.

## 7. Collecte et enrichissement des dossiers

### Réponses et documents

Les réponses structurées constituent la première source. Le texte des PDF est extrait directement quand il est exploitable. L’OCR intervient pour les pages scannées ou dépourvues de texte utilisable. Un résultat illisible produit une information à vérifier, pas une conclusion négative sur le candidat.

### Portfolios et sites publics

- Lire d’abord la page explicitement fournie.
- Extraire le texte principal : réalisations, rôle, démarche, technologies et résultats déclarés.
- Si nécessaire, suivre quelques pages de projets du même site. Proposition initiale : trois pages maximum, profondeur un.
- Conserver URL, date de récupération et extraits utilisés.
- Signaler les pages inaccessibles, protégées ou dépendantes d’un rendu JavaScript non pris en charge.

L’analyse automatique initiale porte sur le texte. Une évaluation visuelle approfondie, particulièrement utile dans certains métiers créatifs, reste à la charge du responsable dans le MVP.

### GitHub

Utiliser l’API officielle pour les dépôts publics explicitement fournis : description, README, langages et arborescence, puis quelques fichiers ciblés si un critère le nécessite [S8].

Privilégier des liens vers des projets précis. Si seul un profil est fourni, inviter le candidat à sélectionner ses réalisations plutôt que parcourir tous ses dépôts. Ne pas exécuter le code téléchargé.

La présence de routes API dans un dépôt peut étayer l’existence d’une réalisation. Elle ne prouve pas à elle seule la contribution du candidat ni sa maîtrise. Le nombre d’étoiles, d’abonnés ou de commits ne constitue pas une note de compétence.

### Règles communes

- Un lien fourni valide la présence d’une information demandée ; son contenu doit être examiné pour étayer une compétence.
- Réponses, CV et portfolio décrivant le même projet ne créent pas trois réalisations distinctes.
- Une source externe enrichit un critère existant ; elle ne donne pas de bonus arbitraire lié au support choisi.
- Une indisponibilité technique reste distincte d’une exigence non satisfaite.
- Les collectes sont limitées, mises en cache et relançables, sans exploration générale de la présence en ligne du candidat.

## 8. Qualification, score et classement

### 8.1 Séparer trois résultats

| Résultat | Fonction |
| --- | --- |
| Admissibilité | Vérifier les conditions indispensables explicites : remplies, non remplies, à vérifier. |
| Adéquation documentée | Apprécier les exigences à partir des éléments effectivement disponibles. |
| Couverture de l’évaluation | Montrer la part des critères évaluables et les informations encore manquantes. |

Une condition obligatoire explicitement non satisfaite doit rester visible, même si d’autres critères obtiennent de bons résultats. Une information absente ne vaut pas automatiquement zéro.

### 8.2 Politique interne

Le backend sélectionne une politique selon le type d’opportunité et les exigences confirmées. Une formation débutante et un recrutement opérationnel ne doivent pas attribuer la même importance à l’expérience préalable.

Chaque politique définit : règles applicables, barèmes, poids internes, traitement des inconnues et conditions de classement. Elle est versionnée et documentée. Les valeurs chiffrées restent à calibrer sur les cas de démonstration ; ce document ne présente pas une pondération comme déjà validée.

L’importance « indispensable / souhaité » exprime le besoin du responsable. Elle ne doit pas être confondue avec une note choisie manuellement. Les critères hors sujet ou les caractéristiques personnelles sans rapport avec l’opportunité n’entrent pas dans le score.

### 8.3 Chaîne de traitement

1. Enregistrer la candidature et lancer une tâche persistante.
2. Extraire et normaliser les réponses, documents et sources externes.
3. Retrouver les passages pertinents pour chaque exigence : correspondances explicites et embeddings si utiles.
4. Appliquer les règles déterministes aux conditions structurées.
5. Pour les critères qualitatifs, produire une appréciation structurée et justifiée, avec un modèle lorsque nécessaire.
6. Valider le format, les références et les valeurs autorisées ; conserver les incertitudes.
7. Calculer le résultat et produire l’explication consultable.

La similarité sémantique aide à retrouver un passage ; elle ne devient pas directement un pourcentage de compétence. Une déclaration, une réalisation documentée et une compétence vérifiée lors d’une épreuve restent des niveaux de preuve différents.

### 8.4 Proposition de calcul à valider

Pour un dossier dont tous les critères pondérés sont évaluables :

`score = 100 × somme(poids_i × niveau_i) / somme(poids_i)`

Les niveaux sont normalisés entre 0 et 1 à partir de barèmes propres aux critères. Chaque niveau possède une description observable et des références justificatives. La même politique est appliquée à tous les candidats d’une campagne.

Pour les dossiers incomplets, afficher une évaluation partielle et sa couverture ; ne pas les classer comme s’ils disposaient d’un score final comparable. Une option ultérieure est d’afficher un intervalle de score possible, sans imputer artificiellement les inconnues.

Présenter deux files utiles : dossiers évalués à examiner et dossiers nécessitant une vérification. Les conditions d’admissibilité non satisfaites restent filtrables et visibles. Aucun score n’est présenté comme une probabilité de réussite.

### 8.5 Intervention humaine

Le responsable peut consulter les sources, corriger une appréciation avec un motif et prendre une décision. Conserver l’évaluation initiale, la correction et le recalcul. Les statuts de décision sont distincts de ceux du traitement : à examiner, présélectionné, non retenu.

Une question de suivi ciblée peut être proposée à partir d’une incertitude. Le MVP l’affiche ; il n’envoie pas automatiquement de message au candidat.

## 9. Dashboard et fonctionnalités de revue

### Vue campagnes

Liste des campagnes avec titre, type, statut, nombre de candidatures et date limite. Actions : créer, ouvrir, dupliquer, fermer les soumissions. Les chiffres servent à orienter le travail, sans multiplier les graphiques décoratifs.

### Vue d’une campagne

En-tête avec lien public et état de la campagne. Onglets proposés : candidatures, configuration, aperçu du formulaire.

Tableau avec recherche, tri et filtres : candidat, score final ou état partiel, admissibilité, critères à vérifier, date de dépôt et décision. Les dossiers en cours d’analyse affichent un état réel ; un score zéro ne remplace jamais un résultat indisponible.

### Fiche candidat

Résumé du dossier, détail des exigences, éléments justificatifs, documents, liens et historique des corrections. Ouvrir un extrait doit permettre de retrouver sa source.

Actions principales : présélectionner, marquer non retenu, corriger une appréciation et relancer une analyse en échec. Une nouvelle analyse conserve sa version et ne supprime pas silencieusement les corrections humaines.

## 10. Direction visuelle et expérience

### Intention

Une application calme, précise et professionnelle. L’inspiration Vercel concerne la hiérarchie typographique, les surfaces neutres et la netteté des composants ; l’inspiration Tally concerne la simplicité de rédaction et le confort des formulaires [S1, S2]. Ces références orientent une identité propre à Talent Engine.

L’interface doit paraître aboutie dès les écrans utiles. La création de campagne et la revue d’un dossier reçoivent autant d’attention que le dashboard.

Le mainteneur fournit une direction de logo et d'icône « Signal » : trois
cercles et une étoile à quatre branches en grille, avec un wordmark minuscule
et des variantes monochrome et bleue. La référence et les déclinaisons sombres
proposées sont décrites dans la [direction visuelle](../design/visual-identity.md#2-logo-et-icône--direction--signal-).

### Système visuel proposé

| Élément | Direction |
| --- | --- |
| Thème initial | Proposition sombre par défaut ; éventuel thème clair secondaire à décider. |
| Fonds | Surfaces anthracite avec niveaux distincts pour navigation, contenu et éléments flottants. |
| Texte | Blanc cassé pour le contenu principal ; gris suffisamment contrasté pour les informations secondaires. |
| Accent | Bleu sobre, réservé au focus, à la sélection et à quelques actions. |
| Bouton principal | Surface claire et texte sombre dans le thème sombre, libellé court décrivant l’action. |
| États | Vert, ambre et rouge accompagnés de textes ou icônes ; aucune information portée par la couleur seule. |
| Typographie | Geist Sans ; Geist Mono uniquement pour quelques valeurs ou identifiants utiles. |
| Échelle | Corps de formulaire autour de 16 px, titres de page autour de 28–32 px, libellés lisibles et hiérarchisés. |
| Espacement | Base de 4 px ; marges confortables, regroupements nets entre sections. |
| Composants | Bordures fines, rayons modérés, ombres légères pour les éléments flottants. |
| Icônes | Lucide, taille et épaisseur cohérentes, toujours au service d’une action. |
| Mouvement | Transitions courtes et discrètes ; respect du réglage de réduction des animations. |

Ces valeurs sont des propositions de design, à vérifier sur les écrans réels, notamment pour le contraste et la densité. La [direction visuelle détaillée](../design/visual-identity.md) reprend la préférence exprimée pour le sombre.

### Composition des écrans

**Espace responsable :** navigation latérale compacte, contenu centré dans une largeur généreuse, titre et action principale immédiatement visibles. Une table lisible est préférable à une accumulation de cartes pour comparer les candidats.

**Création guidée :** zone de saisie principale autour de 720 px ; repère des quatre étapes ; aide courte et contextuelle ; aperçu sur le côté lorsque la largeur le permet. Sur mobile, l’aperçu devient une vue dédiée. Retour possible entre étapes sans perte de saisie.

**Formulaire public :** une colonne d’environ 640–720 px, en-tête sobre, description concise, questions espacées et pièces demandées annoncées clairement. Une expérience inspirée d’un document bien rédigé, sans navigation d’administration.

**Fiche candidat :** synthèse et actions en haut ; critères et preuves dans la zone principale ; métadonnées et documents dans une colonne secondaire sur grand écran. Sur mobile, les sections se suivent dans un ordre logique.

### Usage de shadcn/ui

Utiliser shadcn/ui comme base personnalisable de composants, avec des tokens communs [S3]. Composants utiles : Button, Input, Textarea, Select/Combobox, Badge, Tabs, Table, Dialog, Sheet, Skeleton et composants de formulaire.

Créer les composants métier : bloc d’exigence, éditeur de question, aperçu du formulaire, ligne candidat, appréciation de critère et extrait sourcé. Partager le même moteur d’affichage entre aperçu et formulaire public.

### Qualité des interactions

- Afficher « Brouillon enregistré », « Enregistrement… » et les erreurs de sauvegarde.
- Rendre explicites les états vides avec une action utile : créer une campagne, partager le lien, retirer un filtre.
- Distinguer analyse en attente, en cours, partielle, terminée et en échec.
- Afficher les étapes réellement exécutées, sans faux pourcentage de progression.
- Préserver les données lors d’une erreur et permettre une reprise ciblée.
- Fournir labels, navigation clavier, focus visible et messages d’erreur associés aux champs.
- Utiliser un français direct : « Compétences recherchées », « Points à vérifier », « Voir les éléments du dossier ».

Éviter les grands dégradés, effets de verre, badges IA omniprésents, jauges sans signification, fonds animés et tableaux de bord surchargés. La sophistication doit venir de la cohérence et de la qualité des détails.

## 11. Stack technique retenue

### Choix de base

**Next.js / React / TypeScript pour l’interface, FastAPI / Python pour le métier et l’analyse, PostgreSQL pour les données.** Cette combinaison sépare une interface riche du traitement documentaire et du moteur de qualification [S4, S5]. Le mainteneur retient la stack proposée ; les versions et détails d'intégration restent à préciser. Voir [ADR-0001](../adr/0001-application-nextjs-fastapi-postgresql.md).

| Couche | Suggestion | Rôle |
| --- | --- | --- |
| Frontend | Next.js, React, TypeScript | Pages publiques, dashboard, navigation et formulaires. |
| Design system | Tailwind CSS, shadcn/ui, Lucide, Geist | Composants cohérents et direction visuelle maîtrisée. |
| Formulaires | React Hook Form et Zod | Édition et validation côté interface ; validation serveur indépendante. |
| Tables et données | TanStack Table, TanStack Query si nécessaire | Tri, filtres, pagination et rafraîchissement des analyses. |
| API métier | FastAPI et Pydantic | Campagnes, candidatures, validation, évaluations et intégrations. |
| Persistance | PostgreSQL, SQLAlchemy, Alembic | Données relationnelles, migrations et historique. |
| Documents | pypdf, httpx, BeautifulSoup ou Trafilatura | Extraction PDF, récupération HTTP, nettoyage du texte web. |
| GitHub | API REST officielle via client HTTP | Métadonnées, README et fichiers publics ciblés. |
| Traitements différés | Processus worker Python et table de tâches PostgreSQL | Analyses persistantes, reprises et tentatives limitées. |
| Fichiers | Volume local privé derrière l’API | Pièces jointes pour le développement et la démonstration. |
| Environnement | Docker Compose et fichiers de dépendances verrouillés | Démarrage reproductible de l’interface, de l’API, du worker et de la base. |
| Tests | pytest ; Playwright pour le parcours principal | Scoring, intégrations simulées et démonstration de bout en bout. |

L’API Python porte la logique métier. Next.js ne doit pas héberger une deuxième implémentation des règles. Le schéma OpenAPI peut servir à générer les types du client TypeScript.

Pour le petit volume du challenge, des calculs de similarité en mémoire suffisent ; une base vectorielle dédiée n’est pas nécessaire. Redis et une plateforme de tâches spécialisée peuvent attendre. Le worker doit toutefois gérer les verrous, les tâches interrompues et l’idempotence ; une tâche uniquement conservée en mémoire ne suffit pas.

Proposition d’authentification : un compte responsable initialisé pour la démo, session serveur avec cookie HttpOnly et contrôle d’accès sur toutes les routes privées. Pas d’inscription multi-entreprises dans le MVP.

### Alternative considérée

La proposition initiale décrivait une réalisation entièrement TypeScript avec Next.js, PostgreSQL et un worker Node. Le mainteneur a retenu la combinaison TypeScript/Python ; cette alternative n'est pas la direction actuelle.

## 12. Modèles et fournisseurs à évaluer

### Principe retenu

Le mainteneur dispose déjà d'un FreeLLMAPI local avec des fournisseurs configurés.
Cette passerelle constitue la piste prioritaire pour les appels LLM depuis le
backend. Le container existant est arrêté lors du contrôle du 3 octobre 2026.
La [note d'intégration](../integrations/local-freellmapi.md) distingue cette
installation des capacités restant à vérifier. Un point d'accès local peut
relayer les requêtes à des fournisseurs externes ; il ne signifie pas que les
modèles s'exécutent localement.

Pas de téléchargement de poids requis pour la démo. Les API sont appelées uniquement côté serveur. Un modèle à poids ouverts n’implique pas une API gratuite ; la présence sur Hugging Face n’implique pas qu’un fournisseur le serve actuellement.

| Besoin | Proposition | Conditions de sélection |
| --- | --- | --- |
| Génération et extraction structurée | **GPT-OSS 20B via Groq**, candidat initial actuellement listé dans son catalogue | Tester les réponses françaises, le respect du schéma et les citations de sources. Quotas selon le compte [S6]. |
| Comparaison générative | **Qwen3-4B-Instruct-2507** ou un Qwen Instruct hébergé compatible | Modèle ouvert candidat ; disponibilité d’une API et conditions à vérifier avant de le retenir [S10]. |
| Embeddings multilingues | **BAAI/bge-m3** ou **Qwen3-Embedding-0.6B** via un fournisseur qui les expose | Tester la récupération de passages français/anglais et vérifier l’endpoint exact. Leur hébergement gratuit n’est pas garanti [S7, S11, S12]. |
| OCR | **Mistral OCR**, API spécialisée à évaluer | Usage limité aux scans ; accès et coût à confirmer. La documentation expose l’alias `mistral-ocr-latest` [S9]. |
| PDF avec texte | Extraction locale classique | Aucun appel modèle nécessaire. |
| Règles et score | Code backend | Aucun appel génératif nécessaire au calcul. |

Les offres gratuites sont une préférence de coût, pas une garantie de fonctionnement illimité. Hugging Face propose des crédits d’essai limités ; vérifier les montants, modèles servis et quotas au moment de l’intégration [S7]. Pour l’OCR, aucun accès gratuit durable n’est présumé.

### Contrat technique des intégrations

Prévoir trois adaptateurs simples : génération structurée, embeddings et OCR. Leur configuration précise fournisseur, identifiant du modèle, délai maximal et limites d’usage. Ne pas construire un framework multi-fournisseurs généraliste.

Enregistrer avec l’analyse : modèle utilisé, version de prompt, version de politique, empreinte des sources et date. Mettre en cache extraction et embeddings avec la version du modèle ; ne pas comparer des vecteurs issus de modèles différents.

Valider les réponses générées avec un schéma strict. Les références justificatives doivent pointer vers des extraits réellement récupérés. Les contenus des CV et pages web restent des données non fiables, jamais des instructions autorisées à changer les règles.

Avant sélection définitive, comparer les modèles sur les mêmes dossiers fictifs : pertinence des passages retrouvés, exactitude de l’extraction, éléments inventés, stabilité, latence et coût. Les benchmarks généraux ne remplacent pas cette vérification métier.

## 13. Modèle de données proposé

| Entité | Informations principales |
| --- | --- |
| Responsable | Identité de connexion et session. |
| Campagne | Titre, description, type, domaine, statut, lien public et échéance. |
| Exigence | Nature, attente, caractère indispensable/souhaité et sources associées. |
| Question | Type, libellé, contraintes, options et ordre. |
| Candidature | Campagne, coordonnées, date de dépôt, état d’analyse et décision. |
| Réponse | Question, valeur et version du formulaire. |
| Source | Document ou URL, empreinte, contenu extrait, date et état de récupération. |
| Élément justificatif | Extrait, localisation et exigence renseignée. |
| Évaluation | Politique, modèle, résultats, couverture, score et version. |
| Appréciation par critère | Niveau, justification, sources et informations à vérifier. |
| Correction humaine | Valeur initiale, nouvelle valeur, motif, auteur et date. |
| Tâche d’analyse | Étape, tentatives, délai de reprise et erreur technique. |

Les données structurées restent séparées des réponses brutes des fournisseurs. Les champs variables du formulaire peuvent utiliser du JSON validé, tout en conservant des relations explicites entre campagne, questions et exigences.

## 14. Périmètre du MVP

### Inclus

- Accès responsable protégé.
- Création guidée, brouillons, publication, fermeture et duplication.
- Formulaires dynamiques publics et réception de documents.
- Exigences flexibles, sans écran de pondération pour le responsable.
- Extraction documentaire et OCR conditionnel par API.
- Lecture limitée des portfolios et dépôts GitHub fournis.
- Qualification hybride, score explicable et traitement des inconnues.
- Tableau de candidatures, filtres, fiche détaillée et décisions humaines.
- Reprise des analyses en échec et résultats de démo préchargés identifiés.
- Documentation, migrations, données fictives et tests ciblés.

### Hors périmètre initial

- Constructeur de formulaires reproduisant toute la richesse de Tally.
- Intégrations Tally, Google Forms, messageries ou ATS tiers.
- Analyse exhaustive ou exécution du code des candidats.
- Exploration générale des profils sociaux ou accès à des espaces privés.
- Évaluation visuelle automatisée approfondie des portfolios.
- Comptes candidats, rendez-vous et emails automatiques.
- Multi-entreprises, facturation, permissions fines et gestion d’équipes.
- Entraînement d’un modèle de classement et automatisation des décisions finales.

## 15. Fiabilité et protection des données

- Conserver la candidature avant tout appel externe ; rendre les tâches relançables sans doublons.
- Limiter les délais, tentatives, pages et volumes traités ; respecter les quotas des services.
- Protéger les clés dans l’environnement serveur ; ne pas les inclure dans le dépôt ni les journaux.
- Vérifier type et taille des fichiers ; ne pas exposer le répertoire de pièces jointes publiquement.
- Pour les URL : autoriser HTTP/HTTPS, bloquer les adresses locales, privées et de métadonnées, revérifier les destinations après résolution et redirection.
- Respecter les restrictions d’accès des sites ; ne pas contourner une authentification ou un blocage.
- Minimiser les données envoyées aux API ; éviter les coordonnées si elles ne servent pas à la tâche.
- Prévoir une suppression cohérente des candidatures, documents, extractions et résultats associés.
- Journaliser les événements utiles sans recopier des CV ou secrets dans les logs.
- Utiliser des profils fictifs pour la démonstration et distinguer les résultats préchargés des analyses exécutées en direct.

## 16. Livrable et démonstration

### Organisation indicative du dépôt

| Emplacement | Contenu |
| --- | --- |
| `README.md` | Présentation, installation, variables nécessaires, commandes et scénario de démonstration. |
| `docs/product/project-overview.md` | Cadrage produit et technique. |
| `apps/web/` | Interface et formulaires publics. |
| `apps/api/` | API, logique métier, migrations, worker et tests Python. |
| `docs/` | Architecture, scoring, décisions, limites et captures utiles. |
| `fixtures/` | Campagnes et candidatures fictives, réponses API de test identifiées. |
| `.env.example` | Variables documentées sans secrets. |
| `compose.yaml` | Services locaux, volumes et configuration de démarrage. |

### Scénario de présentation

1. Créer ou ouvrir une campagne de formation en développement.
2. Ajuster les exigences et constater les questions proposées.
3. Publier puis déposer une candidature depuis le formulaire public.
4. Montrer la progression réelle de l’analyse et l’apparition du dossier.
5. Examiner un score et ouvrir ses sources, dont un dépôt GitHub ou un portfolio.
6. Comparer un dossier complet à un dossier nécessitant une vérification.
7. Corriger une appréciation et montrer le recalcul avec historique.
8. Ouvrir le cas marketing pour montrer que le moteur ne dépend pas de critères codés pour les développeurs.

Un jeu de résultats préchargés permet d’explorer le produit sans clé API. Le mode réel nécessite les services configurés et Internet. L’absence de clé doit être expliquée clairement, sans simuler une analyse exécutée.

### Critères d’acceptation

- Le responsable crée une nouvelle campagne sans modifier de code et sans définir de poids techniques.
- L’aperçu correspond au formulaire publié.
- Une soumission valide est enregistrée une seule fois, même en cas de double clic ou de reprise réseau.
- Un échec de scraping ou d’API n’entraîne pas la perte de candidature.
- Chaque appréciation qualitative possède une source ou un statut « à vérifier ».
- Deux évaluations complètes d’une campagne utilisent la même version de politique.
- Les informations absentes ne sont pas assimilées à une absence de compétence.
- Les sources répétées n’augmentent pas artificiellement le score.
- Le parcours principal fonctionne au clavier et sur mobile ; les états vides et erreurs sont traités.
- Le dépôt peut être lancé depuis les instructions sur un environnement propre.

## 17. Ordre de réalisation proposé

1. Définir deux campagnes fictives et quelques dossiers attendus pour préciser la qualification.
2. Poser les tokens de design, les composants et les écrans principaux.
3. Implémenter la création guidée, la publication et la réception persistante.
4. Construire le moteur de règles, les états d’analyse et la fiche de résultats.
5. Ajouter l’extraction documentaire, les portfolios, GitHub et les modèles par API.
6. Vérifier les évaluations sur les dossiers de référence, corriger les incohérences et finaliser l’interface.
7. Documenter le démarrage, les arbitrages et la démonstration ; ajouter un lien hébergé si utile.

Le délai de réalisation reste à préciser. Le mainteneur construit le MVP seul
avec l'assistant et conserve son périmètre complet. Les barèmes exacts et les
modèles seront arrêtés après les premiers essais, en privilégiant l'installation
FreeLLMAPI disponible. La lecture ciblée de GitHub et des portfolios fait partie
du périmètre retenu.

## 18. Références techniques et visuelles

Sources officielles consultées le 3 octobre 2026. Les capacités documentées ne garantissent ni leur disponibilité sur un compte particulier ni leur gratuité future. Les choix de produit et de design ci-dessus sont des propositions propres au projet.

- **[S1]** [Vercel — Geist Design System](https://vercel.com/geist/introduction).
- **[S2]** [Tally — référence de simplicité des formulaires](https://tally.so/).
- **[S3]** [shadcn/ui — introduction et composants](https://ui.shadcn.com/docs).
- **[S4]** [Next.js — documentation](https://nextjs.org/docs).
- **[S5]** [FastAPI — documentation](https://fastapi.tiangolo.com/).
- **[S6]** [Groq — catalogue de modèles](https://console.groq.com/docs/models) et [quotas](https://console.groq.com/docs/rate-limits).
- **[S7]** [Hugging Face — extraction de features par API](https://huggingface.co/docs/inference-providers/tasks/feature-extraction) et [tarification des fournisseurs](https://huggingface.co/docs/inference-providers/pricing).
- **[S8]** [GitHub — lecture des contenus et README](https://docs.github.com/en/rest/repos/contents) et [quotas REST](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).
- **[S9]** [Mistral — OCR et traitement documentaire](https://docs.mistral.ai/studio/document-processing/basic_ocr).
- **[S10]** [Qwen3-4B-Instruct-2507 — fiche du modèle](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507).
- **[S11]** [Qwen3-Embedding-0.6B — fiche du modèle](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).
- **[S12]** [BAAI/bge-m3 — fiche du modèle](https://huggingface.co/BAAI/bge-m3).
