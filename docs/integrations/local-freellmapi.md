# Intégration au FreeLLMAPI local

**Vérification : 2026-10-04, étape T21.** La passerelle existante a été
démarrée pour l'intégration. Aucun fournisseur ni clé fournisseur n'a été
ajouté ou modifié. Son accès hôte reste limité à `127.0.0.1:3001`.

## Installation effectivement utilisée

- Container : `freellmapi-freellmapi-1`.
- Image installée : `sha256:68f100da8670d0f9f00c3a037cb6d17dbde31d29f7b9992586892f5d5c2aaef2`.
- Commit déclaré par l'image : `f2d0070ddd81d8b6233d9227550bea3195513db2`.
- Configuration retrouvée : `/app/server/data/freeapi.db`, volume
  `freellmapi_freellmapi-data`. Lecture des métadonnées en mode lecture seule.
- Fournisseurs configurés avec clés activées : Cerebras, Google, Groq,
  NVIDIA et OpenRouter. Leurs états enregistrés ne prouvent pas qu'un appel
  actuel réussit chez chacun.

La documentation du checkout local peut être plus récente que l'image.
Les constats suivants viennent des appels réellement exécutés dans le worker,
pas d'une liste de capacités annoncées.

## Appels réels depuis le worker Docker

| Test | Résultat observé |
| --- | --- |
| `GET /v1/models` | 200, 245 entrées de catalogue ; ce nombre ne prouve pas 245 modèles utilisables. |
| Chat minimal `auto:fast` | 200 en 2,80 s ; `openrouter/dots-studio/dots-3-note-preview:free`, JSON demandé reçu. |
| Embeddings `auto` | 200 en 0,88 s ; modèle `gemini-embedding-001`, dimension 3 072. Aucun `X-Routed-Via` reçu : fournisseur effectif non établi par ce test. |
| Premier essai vision/OCR | 200 en 11,81 s ; sortie commentée et tronquée, transcription non conforme. |
| Chat via l'adaptateur livré | JSON validé, 5,61 s ; `google/gemma-4-26b-a4b-it`. |
| Second essai vision/OCR via l'adaptateur | Texte fictif `TALENT TEST 42` exactement transcrit en 0,98 s ; `google/gemini-3.5-flash-lite`. |

Ces délais sont des observations ponctuelles, pas une mesure de performance.
Aucun quota 429 n'a été rencontré pendant ces sondes. La variabilité du
routage est visible : conserver le fournisseur et le modèle effectifs à
chaque appréciation. Le petit test OCR ne prouve pas la qualité sur des CV
scannés ; le pipeline OCR et sa recette appartiennent à T24. L'intégration
vectorielle et la traçabilité de sa famille appartiennent à T27.

## Configuration serveur

L'adaptateur est `talent_engine.integrations.llm.Gateway`. Il lit uniquement
les variables serveur `TALENT_LLM_BASE_URL`, `TALENT_LLM_API_KEY`,
`TALENT_LLM_MODEL`, `TALENT_LLM_OCR_MODEL`, `TALENT_LLM_EMBEDDING_MODEL`,
`TALENT_LLM_EMBEDDING_DIMENSIONS` et `TALENT_LLM_TIMEOUT_SECONDS`. Sans URL ou clé,
`llm_not_configured` est un échec explicite. Aucun secret n'est transmis au
web, inclus dans un prompt, conservé dans le dépôt ou journalisé.

`compose.llm.yaml` est un complément facultatif au Compose de base :

```sh
# Fournir TALENT_LLM_API_KEY dans l'environnement serveur par le gestionnaire
# de secrets existant ; ne pas inscrire sa valeur dans cette commande.
docker compose -f compose.yaml -f compose.llm.yaml up -d worker
```

Il raccorde seulement le worker au réseau externe existant
`freellmapi_default` et utilise `http://freellmapi:3001/v1`.
`TALENT_LLM_NETWORK` permet de configurer le nom du réseau. Dans Docker,
localhost désigne le container appelant. Aucune exposition publique de la
passerelle n'est nécessaire. Pour les sondes locales, la clé de passerelle
existante a été transmise en mémoire puis dans l'environnement du worker,
sans fichier de copie ni extraction des clés fournisseur.

L'adaptateur demande `stream: false`, température zéro, limite de sortie et
désactive compression de prompt/cache. Il exige un `X-Routed-Via` exploitable
pour le chat et conserve également le modèle de la réponse. La politique,
les niveaux et références sont validés par le moteur, jamais par le transport.

Délai réseau : 30 secondes par opération bloquante, configurable jusqu'à 30 ;
la réponse est bornée à 1 MiB et refusée si la durée observée dépasse ce délai.
Le worker conserve son plafond global de 60 secondes et son fencing. Les
redirections et proxys hérités sont désactivés. La clé est un `SecretStr` ;
les corps d'erreur fournisseur ne sont ni affichés ni persistés. 429 et 5xx
sont reprenables par le worker avec ses budgets existants ; 401/403 et sorties
non conformes échouent explicitement. Voir le comportement officiel de
[urllib.request](https://docs.python.org/3.13/library/urllib.request.html).

Les tests HTTP locaux couvrent clé côté serveur, requête minimisée,
provenance, 429/Retry-After, 503 et métadonnées absentes. Ils complètent les
sondes réelles ci-dessus et ne les remplacent pas.

## Modèle retenu pour l’appréciation de démo

T22 utilisait par défaut `gemini-3.5-flash-lite`, vérifié sur le PDF fictif
détaillé : fournisseur Google, niveaux observés 4/3/4 en 2,68 s. Sur les mêmes
preuves, le routage `auto:fast` avait donné 4/4/4 avec Groq. Ce constat motive
un modèle demandé explicite ; il ne constitue pas une calibration ni une
reproduction de l’oracle contrôlé 3/3/4. Le fournisseur/modèle effectifs restent
conservés à chaque appel et peuvent être comparés aux preuves en revue.
`TALENT_LLM_MODEL` permet une configuration serveur explicite différente.
Le parcours intégré final, avec ce même modèle demandé, a ensuite produit
3/3/4 et 81,25 sur le PDF fictif Amina ; chaque citation a été contrôlée dans
le texte persisté. La différence avec l'essai précédent reste documentée :
ces appréciations ponctuelles ne sont pas une mesure absolue de la personne.

T27 sépare les usages : appréciation `gpt-oss-120b`, OCR
`gemini-3.5-flash-lite`, embeddings `gemini-embedding-001` en 3072 dimensions.
Le [rapport de choix et de récupération](ai-adapters.md) décrit la comparaison
répétée, ses écarts, les budgets et l’invalidation du cache. Ces réglages sont
des choix de démonstration ; le responsable conserve la décision humaine.
