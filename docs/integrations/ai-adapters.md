# Adaptateurs IA et récupération versionnée

Trois modèles demandés explicitement, configurés séparément côté worker :

| Usage | Variable | Défaut retenu |
| --- | --- | --- |
| Appréciation JSON | `TALENT_LLM_MODEL` | `gpt-oss-120b` |
| Transcription visuelle conditionnelle | `TALENT_LLM_OCR_MODEL` | `gemini-3.5-flash-lite` |
| Vecteurs | `TALENT_LLM_EMBEDDING_MODEL` | `gemini-embedding-001` |
| Dimension vectorielle | `TALENT_LLM_EMBEDDING_DIMENSIONS` | `3072` |

La provenance conserve les modèles demandés/effectifs du chat et de l’OCR,
ainsi que la famille, dimension et fournisseur annoncé par la réponse
vectorielle, lorsqu’il est disponible. La famille reçue doit correspondre
exactement à la famille demandée. Pas de routage vectoriel `auto`, mélange
entre familles ou substitution silencieuse après quota. Le code installé de
FreeLLMAPI route ses embeddings entre fournisseurs d’une même famille.
Un nom de modèle distant ne garantit pas l’immuabilité future de ses poids :
un changement connu de famille, dimension ou adaptateur invalide le cache.

## Comparaison réelle du 4 octobre 2026

Les attentes FR/EN de `fixtures/retrieval/model-cases.json` ont été écrites
avant les appels : paraphrases, contradiction, zéro explicite, rôle collectif
et injection. `scripts/compare_ai_models.py` répète trois appels par modèle,
avec le même prompt, température zéro et format JSON de production. Le rapport
[observé](../../fixtures/retrieval/observed-2026-10-04.json) conserve son empreinte
exacte et chaque résultat, y compris les écarts.

| Modèle | Résultat du script final | Durée par appel |
| --- | --- | --- |
| Gemini 3.5 Flash Lite, Google | 16/18 statuts et niveaux attendus ; citations valides | 3,39–4,18 s |
| GPT-OSS-120b, Groq `openai/gpt-oss-120b` | 18/18 ; citations valides, stable sur les trois répétitions | 4,17–5,44 s |
| Gemini Embedding 001, Google, 3072 | 6/6 premiers passages attendus ; scores stables | 1,03–2,08 s |
| Gemini Embedding 2, Google, 3072 | 6/6 premiers passages attendus ; scores stables | 1,05–1,44 s |

GPT-OSS est retenu pour la stabilité des statuts attendus sur ce jeu. Les deux
écarts de Flash Lite concernent `insufficient_information` au lieu de
`source_unavailable` après filtrage de l’injection ; aucun score n’est inventé.
Embedding 001 reste retenu : les deux familles retrouvent les mêmes passages,
et le jeu ne démontre pas d’avantage de pertinence justifiant une migration.
La valeur brute d’un cosinus ne compare pas la qualité de familles différentes.
L’OCR conserve le modèle visuel déjà exercé sur trois pages scannées.

Des sondes supplémentaires ont rencontré des indisponibilités Gemma et
Gemini Flash (deux délais dépassés sur trois pour Flash), et un identifiant
Llama absent du catalogue a été rejeté. Ces sondes ne mesurent pas leur qualité.
Un premier script sans demande de format JSON rejetait des blocs Markdown ;
le rapport final utilise le format effectif du worker. Les attentes n’ont
pas été modifiées pour s’adapter aux sorties.

Chaque appel vectoriel du rapport annonce 227 tokens d’entrée. Aucun coût
monétaire effectif du compte n’est fourni : `monetary_cost_observed` reste
null. Ne pas déduire la gratuité d’un HTTP 200 ; voir la
[tarification Google](https://ai.google.dev/gemini-api/docs/pricing) et celle du
[fournisseur Groq](https://console.groq.com/docs/model/openai/gpt-oss-120b).
Ces quelques cas fictifs ne calibrent ni les barèmes ni l’équité en recrutement.
Les niveaux peuvent encore varier ; la décision reste humaine.

Pour répéter, fournir les variables `TALENT_LLM_*` via l’environnement serveur,
sans inscrire la clé dans une commande ou un fichier versionné, puis :

```sh
uv run --project apps/api python scripts/compare_ai_models.py
```

Le script affiche des lignes JSON avec observations et erreurs, jamais clés,
textes de candidatures ou vecteurs. Il utilise uniquement les fixtures fictives.

## Récupération et cache

`evidence-retrieval-v1` filtre les injections reconnues avant tout embedding.
Les coordonnées email sont masquées. Les extraits admissibles doivent être liés
aux questions du critère. Au plus 64 candidats sont parcourus en alternant les
sources, avec priorité aux déclarations négatives explicites reconnues ; les
candidats au-delà de ce plafond sont signalés comme omis. Les 20 requêtes
maximum combinent attente et barème. Lots de 16 textes, requête 200 000 octets,
réponse 4 MiB, vecteurs finis et non nuls de dimension exacte, normalisation L2.
Les choix suivent la [documentation des embeddings Google](https://ai.google.dev/gemini-api/docs/embeddings).

La similarité cosinus sélectionne trois passages par critère et conserve aussi
les déclarations négatives reconnues. Elle ne produit ni niveau ni bonus de
source. La limite finale de prompt reste 40 000 caractères ; injections et
passages omis restent visibles. Une contradiction non explicite dans un passage
omis peut échapper à cette lecture ciblée : ce n’est pas une revue exhaustive.
Les preuves historiques et originaux restent consultables.

Budget de récupération observé : 20 s, puis génération bornée à 30 s, avant
le plafond worker de 60 s. Une erreur vectorielle/quota utilise les reprises
existantes ; aucune appréciation n’est construite avec des vecteurs incohérents.
Les délais des sockets sont par opération bloquante ; le worker contrôle aussi
la durée totale avant toute publication, avec son bail et sa génération.

La migration `0014_embedding_cache` crée un cache privé par candidature.
Sa clé comprend version de récupération/adaptateur, famille et dimension ;
chaque entrée identifie version de source et texte masqué, ou requête de
critère et barème. Changer source, texte, barème, famille ou dimension provoque
une nouvelle entrée. Aucun vecteur n’est réutilisé entre candidatures.

Les appels se font hors verrou SQL. Les vecteurs calculés restent en mémoire
jusqu’à finalisation : bail/génération, sources, classement des passages,
appréciations et hash du prompt doivent tous être validés avant leur insertion.
Une perte de bail ou un résultat invalide n’enregistre ni cache ni évaluation.
La provenance conserve requêtes hachées, passages/rangs, omissions, dimension,
durée, tokens annoncés et nombres de hits/misses. Le cache ne change pas les
sources et checkpoints historiques déjà réussis.

La recette combinée réelle a collecté un scan fictif, le portfolio et le dépôt
publics autorisés, puis persisté/rendu leurs résultats. Dix-huit vecteurs ont
été calculés ; une seconde récupération a retrouvé exactement les mêmes
passages avec 18 hits et aucun nouvel appel. Les citations ont été vérifiées
contre textes conservés, localisateurs et empreintes. Cette preuve établit le
parcours technique ; elle ne valide pas les compétences d’une personne réelle.

Sur la recette combinée Amina, GPT-OSS a ensuite donné 4/3/4 (91,25), alors
que Flash Lite avait donné 3/3/4 (81,25) sur une autre collecte du scan.
La transcription OCR et le choix des passages peuvent aussi varier : cette
comparaison de parcours ne permet pas d’attribuer la différence au seul chat.
Le résultat attendu déterministe des tests de calcul reste un oracle contrôlé,
sans obligation qu’un modèle réel lui corresponde sur chaque appréciation.

Une seconde recette sur les artefacts finaux a donné 3/3/4 (81,25) avec
GPT-OSS. Même après une comparaison synthétique stable, cette variation
confirme qu’une appréciation réelle reste à vérifier humainement.
