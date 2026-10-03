# Talent Engine — Spécification du moteur d’évaluation

> Complément au [cadrage produit](../product/project-overview.md).
>
> Statut : proposition d’implémentation à valider. Les poids, barèmes et dossiers fictifs ci-dessous servent à préciser et tester le comportement du moteur. Ils ne constituent pas des critères officiels de SKULLVI ni un modèle de sélection validé sur des candidatures réelles.

## 1. Résultat attendu

Pour chaque candidature, le moteur produit quatre informations distinctes :

1. **Admissibilité** : les conditions indispensables explicites sont-elles satisfaites ?
2. **Évaluation par exigence** : quels éléments du dossier renseignent chaque attente ?
3. **Adéquation documentée** : quel score résulte des appréciations disponibles ?
4. **Points à vérifier** : quelles inconnues empêchent de terminer l’évaluation ?

Le classement aide à organiser la revue. Il ne décide pas de la sélection et n’est pas une prédiction de réussite.

## 2. Ce que définit le responsable

Le responsable renseigne le type d’opportunité, le domaine, le niveau attendu, les exigences et leur caractère indispensable ou souhaité. Il associe ou confirme les questions et pièces proposées par le formulaire guidé.

Il ne définit pas de poids, de formule ou de barème numérique. Ces paramètres sont gérés dans les politiques internes du backend, consultables sous une explication lisible dans le produit.

### Exemple d’entrée métier

- Type : programme de formation.
- Domaine : développement backend.
- Niveau : débutant disposant de premières bases.
- Attentes : bases de programmation, première mise en pratique, démarche d’apprentissage.
- Condition indispensable : disponibilité sur les créneaux annoncés.

L’application ne doit pas ajouter « diplôme universitaire », « expérience professionnelle » ou « dépôt GitHub obligatoire » sans que le besoin le demande.

## 3. Transformer le besoin en plan d’évaluation

### 3.1 Exigences structurées

Chaque exigence contient :

| Champ | Fonction |
| --- | --- |
| Identifiant | Relier l’exigence aux réponses et résultats. |
| Famille | Compétence, réalisation, apprentissage, disponibilité ou autre condition. |
| Attente | Capacité ou condition concrète recherchée. |
| Importance métier | Indispensable ou souhaité, confirmé par le responsable. |
| Mode d’évaluation | Règle déterministe ou appréciation qualitative. |
| Sources attendues | Questions, documents ou liens associés. |
| Politique et barème | Version interne choisie pour cette exigence. |

Une exigence libre doit être rapprochée d’une famille prise en charge. Si elle ne peut pas être interprétée de façon fiable, demander une précision pendant la création ou la signaler pour revue manuelle. Ne pas appliquer silencieusement un barème arbitraire.

### 3.2 Conditions et compétences indispensables

Une disponibilité est une condition vérifiable à partir d’une réponse structurée. Une compétence indispensable reste une capacité à apprécier : elle ne doit pas devenir « absente » parce qu’un mot-clé n’a pas été retrouvé.

Une condition clairement non satisfaite produit une alerte d’admissibilité. Une compétence indispensable non documentée produit un point à vérifier. Aucun de ces résultats ne déclenche un rejet automatique.

### 3.3 Politique figée avant évaluation

Le backend choisit une politique selon le type d’opportunité et les familles d’exigences. Cette politique fixe les poids, les niveaux possibles et leurs descriptions avant de traiter les candidats.

Proposition MVP : commencer avec deux politiques, formation et recrutement, puis des barèmes réutilisables pour les familles de critères. Le domaine détermine les capacités concrètes recherchées ; il ne crée pas une nouvelle architecture de scoring.

Si plusieurs exigences appartiennent à la même famille, répartir son poids entre elles selon une règle explicite. Une répétition ou une reformulation ne doit pas augmenter le poids total de la famille. Une modification du nombre de critères doit produire une nouvelle version de configuration, avant les premières soumissions.

## 4. Collecter et qualifier les éléments du dossier

### 4.1 Sources

- Réponses structurées et textes libres du formulaire.
- Texte extrait du CV et des documents.
- Texte OCR lorsque nécessaire.
- Extraits des pages de portfolio fournies et récupérées.
- README, métadonnées et fichiers GitHub ciblés.

Chaque élément conserve sa source, son emplacement, sa date et son état d’extraction. Pour GitHub, conserver si possible la référence du commit lu ; pour les autres sources, une empreinte du contenu permet de savoir ce qui a réellement été analysé.

### 4.2 Nature des éléments

| Nature | Exemple | Interprétation |
| --- | --- | --- |
| Déclaration | « Je connais Python. » | Le candidat affirme une compétence. |
| Explication contextualisée | Description d’un problème et de la solution réalisée. | Le dossier apporte du contexte sur une démarche. |
| Réalisation consultable | Dépôt ou document montrant des éléments cohérents. | L’artefact étaye l’existence d’une réalisation. |
| Vérification humaine | Note confirmée par un examinateur après revue. | Une personne assume l’appréciation enregistrée. |

Ces catégories ne constituent pas une échelle automatique de bonus. Un portfolio peut être précis sans dépôt public, et la contribution personnelle à un dépôt reste à établir.

### 4.3 Rôle des embeddings et du LLM

Les embeddings aident à sélectionner des passages susceptibles de renseigner une exigence. Le LLM, lorsque nécessaire, propose une appréciation parmi les niveaux autorisés et cite ces passages.

Le backend valide la structure, les identifiants des sources et les bornes des niveaux. Une citation existante ne garantit pas à elle seule que l’interprétation est correcte : la revue humaine et les exemples de validation restent nécessaires.

Ne pas utiliser une similarité cosinus comme note de compétence. Ne pas demander au LLM de choisir les poids ou d’inventer une nouvelle grille pour chaque candidat.

## 5. Contrat d’évaluation par critère

Proposition de structure de sortie interne :

```json
{
  "criterion_id": "learning_approach",
  "status": "evaluated",
  "level": 3,
  "scale_max": 4,
  "evidence_ids": ["answer_7_excerpt_1"],
  "rationale": "La réponse décrit une difficulté, une ressource utilisée et son application dans un projet.",
  "uncertainties": ["Le résultat final reste déclaré par le candidat."],
  "policy_version": "training-demo-v1",
  "rubric_version": "learning-demo-v1"
}
```

Les identifiants illustratifs sont fictifs. Le contrat doit utiliser de véritables références au moment de l’implémentation.

### États autorisés

| État | Niveau numérique | Conséquence |
| --- | --- | --- |
| `evaluated` | Entier de 0 à 4 | Participe au calcul. |
| `insufficient_information` | `null` | Information insuffisante ; score final indisponible. |
| `conflicting_information` | `null` | Sources contradictoires ; revue nécessaire. |
| `source_unavailable` | `null` | Source indispensable à cette appréciation indisponible. |

Si une autre source suffit, un portfolio indisponible n’empêche pas nécessairement le critère d’être évalué. L’incident reste enregistré au niveau de la source.

Une absence de mention produit une inconnue, pas un zéro. Un niveau zéro nécessite une réponse ou un constat explicite compatible avec le barème et sans contradiction non résolue. Le maximum d’une échelle signifie « attente documentée au niveau prévu », jamais « expert absolu ».

## 6. Calcul et présentation

Soit `w_i` le poids fixé par la politique et `l_i` le niveau entre 0 et 4. Les poids d’une campagne totalisent 100.

### Dossier entièrement évaluable

`score = somme(w_i × l_i / 4)`

Conserver la précision de calcul ; afficher une décimale dans l’interface. Un arrondi ne doit pas créer une différence de rang artificielle. Des scores identiques restent ex æquo.

### Dossier partiellement évaluable

`couverture = somme(poids des critères évalués)`

`borne basse = somme(w_i × l_i / 4 pour les critères évalués)`

`borne haute = borne basse + somme(poids des critères inconnus)`

L’intervalle représente les résultats mathématiquement possibles si les inconnues sont résolues, sans probabilité associée. La borne basse n’est pas affichée comme une mauvaise note. Ne pas renormaliser les seuls critères connus pour produire un score final artificiellement élevé.

Dans le MVP, l’affichage principal peut se limiter à « Évaluation partielle — couverture 65 % ». L’intervalle apparaît dans le détail s’il aide à la revue. La couverture décrit la disponibilité de l’évaluation, pas la fiabilité du modèle.

### Conditions d’admissibilité

- Au moins une condition explicitement non satisfaite : `condition_unmet`.
- Sinon, au moins une condition non résolue : `needs_review`.
- Toutes satisfaites : `eligible`.
- Aucune condition définie : `not_applicable`.

Conserver le détail de toutes les conditions, même lorsqu’une autre détermine déjà l’état global.

## 7. Exemple A — Formation en développement

### Politique fictive de démonstration

| Critère | Poids | Sources attendues |
| --- | ---: | --- |
| Bases de programmation | 40 | Réponse technique courte et explication de démarche. |
| Mise en pratique | 35 | Description de réalisation et artefact facultatif. |
| Démarche d’apprentissage | 25 | Difficulté rencontrée, démarche et réutilisation. |

Condition séparée : disponibilité pour les créneaux de formation.

### Barèmes indicatifs

| Niveau | Bases de programmation | Mise en pratique | Démarche d’apprentissage |
| --- | --- | --- | --- |
| 0 | Réponse établissant que les prérequis visés ne sont pas acquis. | Le candidat indique n’avoir encore réalisé aucun exercice ou projet. | Le candidat indique ne pas pouvoir donner de démarche d’apprentissage sur la période demandée. |
| 1 | Quelques notions identifiées, compréhension très partielle dans la réponse. | Exercice guidé décrit avec contribution limitée. | Activité d’apprentissage citée sans démarche détaillée. |
| 2 | Concepts de base expliqués sur un cas simple, avec lacunes identifiées. | Petite réalisation décrite avec rôle personnel identifiable. | Objectif et ressources décrits, application peu détaillée. |
| 3 | Raisonnement cohérent sur le cas et explication des étapes. | Réalisation décrite avec contribution, choix et résultat. | Difficulté, ressource et application concrète décrites. |
| 4 | Réponse cohérente incluant vérification et cas limites adaptés au niveau débutant. | Réalisation incluant difficulté résolue et vérification du résultat. | Démarche incluant essai, retour, ajustement et réutilisation. |

Si la réponse ne permet pas de choisir un niveau, la valeur reste inconnue. Le style littéraire, la longueur et l’aisance à se vendre ne doivent pas remplacer le contenu recherché. Les niveaux évaluent ici ce que le dossier documente.

### Résultats fictifs

| Dossier | Bases /4 | Pratique /4 | Apprentissage /4 | Score | Couverture | Disponibilité |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Amina | 3 | 3 | 4 | 81,25 | 100 % | Compatible |
| Boris | 2 | 3 | 3 | 65,00 | 100 % | Compatible |
| Chloé | 4 | Inconnu | 3 | Partiel : 58,75–93,75 | 65 % | Compatible |
| David | 4 | 4 | 3 | 93,75 | 100 % | Incompatible |

Calcul Amina : `40 × 3/4 + 35 × 3/4 + 25 × 4/4 = 81,25`.

Chloé décrit un projet collectif sans préciser sa contribution ; le critère pratique reste inconnu. Question proposée : « Qu’avez-vous personnellement réalisé dans ce projet ? »

David possède le score d’adéquation documentée le plus élevé, mais sa disponibilité est incompatible. Son dossier figure parmi les conditions à examiner et n’est pas rejeté automatiquement.

Dans la file des dossiers complets avec conditions satisfaites, Amina précède Boris. Chloé apparaît dans la file de vérification, sans faux rang comparable aux dossiers complets.

## 8. Exemple B — Recrutement marketing junior

### Politique fictive de démonstration

| Critère | Poids | Sources attendues |
| --- | ---: | --- |
| Compréhension d’une audience | 40 | Étude de cas et justification des choix. |
| Analyse de résultats | 35 | Exemple de campagne, indicateurs et interprétation. |
| Production de contenu | 25 | Contenus et rôle personnel, via fichier ou portfolio. |

Condition séparée : disponibilité à la date annoncée. La production de contenu peut être documentée sans site personnel.

### Barème indicatif pour « analyse de résultats »

- **0 :** la réponse établit que le candidat ne sait pas interpréter les indicateurs demandés.
- **1 :** indicateurs cités sans interprétation utile.
- **2 :** indicateurs reliés à un objectif, avec interprétation limitée.
- **3 :** résultats interprétés et proposition d’action cohérente.
- **4 :** comparaison contextualisée, limites identifiées et recommandation justifiée.
- **Inconnu :** pas assez d’informations pour attribuer l’un de ces niveaux.

Les autres critères doivent avoir leurs propres niveaux décrits avant l’implémentation. Les valeurs suivantes illustrent le calcul et ne remplacent pas cette rédaction.

### Résultats fictifs

| Dossier | Audience /4 | Résultats /4 | Contenu /4 | Score | Couverture |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fatou | 3 | 4 | 2 | 77,50 | 100 % |
| Karim | 4 | 2 | 3 | 76,25 | 100 % |
| Lina | 3 | Inconnu | 4 | Partiel : 55,00–90,00 | 65 % |

Fatou décrit des actions reliées à des indicateurs et fournit une interprétation argumentée. Karim présente une bonne compréhension de l’audience mais explique moins bien les résultats. Les notes sont des données fictives de test, pas des conclusions tirées de personnes réelles.

Lina fournit un portfolio utile pour les contenus, mais aucune information exploitable sur les résultats. Le portfolio ne lui donne pas de points supplémentaires au-delà des critères concernés.

L’écart entre Fatou et Karim organise la revue selon la politique choisie ; il ne prouve pas que Fatou sera meilleure dans le poste. L’interface doit exposer leurs profils par critère, pas seulement leur rang.

## 9. Files de revue et interface

Proposer trois vues filtrées au sein d’une même campagne :

| Vue | Contenu | Organisation |
| --- | --- | --- |
| Prêts à examiner | Critères évalués et conditions satisfaites ou non applicables. | Score décroissant, avec ex æquo visibles. |
| À vérifier | Information manquante, contradiction ou condition non résolue. | Motif visible et filtres ; pas de pseudo-classement final. |
| Conditions non satisfaites | Au moins une condition explicitement incompatible. | Condition concernée, dossier toujours consultable. |

La vue « Toutes les candidatures » permet de ne perdre aucun dossier entre les catégories. La décision humaine — à examiner, présélectionné ou non retenu — est indépendante de ces vues.

Dans la fiche, chaque critère présente : attente, appréciation, justification, extraits sourcés et action de correction. Le calcul est consultable mais ne devient pas une interface de configuration de poids pour le responsable.

Ne pas exposer au candidat son score de présélection dans le MVP. Sa confirmation porte sur la bonne réception de sa candidature.

## 10. Résilience et versions

### États de traitement

`queued`, `collecting`, `evaluating`, `completed`, `completed_partial`, `failed`.

Ces états décrivent l’exécution. Une analyse peut être terminée tout en concluant que le dossier manque d’informations. Ne pas confondre « le modèle n’a pas répondu » avec « le candidat n’a pas les compétences ».

### Reprises

- Réessayer de façon limitée les erreurs techniques temporaires.
- Mettre en attente une analyse soumise à un quota API, avec un motif consultable.
- Réutiliser les extractions et embeddings inchangés.
- Ne pas relancer automatiquement toutes les sources lorsqu’une seule a échoué.
- Identifier un traitement par la candidature, les versions de configuration et les empreintes des sources.

Une empreinte identique permet de réutiliser un résultat ; une nouvelle version crée une nouvelle évaluation. Les résultats précédents restent disponibles. Les appréciations humaines ne sont jamais remplacées sans trace par une relance automatique.

### Correction humaine

Conserver auteur, date, ancien résultat, nouveau résultat et motif. Recalculer le score avec la même formule. Une correction peut également transformer un critère inconnu en évalué et augmenter la couverture.

Les modèles et prompts sont enregistrés avec leur version. Même avec des réglages stables, une analyse générative ne doit pas être promise comme parfaitement déterministe. Le calcul numérique, lui, doit l’être pour des entrées identiques.

## 11. Vérification avant démonstration

### Tests de règles et de calcul

- Amina obtient exactement 81,25 avec les données indiquées.
- Chloé garde un score final nul, une couverture de 65 % et un intervalle de 58,75 à 93,75.
- David conserve une alerte de disponibilité malgré un score de 93,75.
- Une répétition du même projet dans trois sources n’ajoute aucun critère ni bonus.
- Une erreur réseau ne génère pas un niveau zéro.
- Une correction humaine produit le score attendu et un historique.
- Deux niveaux hors bornes ou des références de sources inexistantes sont refusés.
- Deux scores identiques restent ex æquo.

### Vérification des modèles

Construire un petit jeu de dossiers fictifs comprenant des paraphrases, des absences d’information, des contradictions et des liens inaccessibles. Rédiger d’abord les éléments attendus et les questions à vérifier, puis examiner les sorties du modèle.

Observer séparément : récupération des bons passages, extraction correcte, justification des niveaux, références inventées, variation entre exécutions, temps et coût. Une réussite sur ce petit jeu permet de préparer une démonstration ; elle ne valide pas un système de recrutement à grande échelle.

Inclure des contenus qui tentent de donner des instructions au modèle dans un CV ou un README. Le moteur doit les traiter comme des données du dossier et conserver sa politique d’évaluation.

## 12. Décisions restant à valider

1. Les familles de critères réellement proposées dans les deux politiques initiales.
2. Les poids de démonstration et les descriptions complètes des niveaux pour chaque famille.
3. La manière de signaler une compétence indispensable insuffisamment documentée dans l’interface.
4. L’affichage ou non des intervalles pour les dossiers partiels.
5. Les modèles et fournisseurs, après essais sur les mêmes exemples.

Cette spécification fixe une structure exploitable sans figer prématurément les choix numériques. Elle permet de construire le moteur, ses données et ses écrans autour d’un contrat commun.
