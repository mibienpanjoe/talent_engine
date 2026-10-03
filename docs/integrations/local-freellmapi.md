# Talent Engine — Intégration au FreeLLMAPI local

**Date :** 2026-10-03  
**Statut :** installation identifiée ; container arrêté ; appels non vérifiés.

## 1. Intention du mainteneur

Le mainteneur indique que FreeLLMAPI est déjà installé et configuré avec
plusieurs fournisseurs. Cette passerelle est la piste prioritaire pour les
appels LLM de Talent Engine. Les modèles et fournisseurs réellement utilisables
restent à vérifier sur le service en fonctionnement.

Un accès sur localhost désigne la passerelle. Les inférences peuvent être
effectuées par des fournisseurs distants ; la minimisation des données reste
pertinente.

## 2. Constats locaux

Contrôles effectués : inventaire Docker et inspection du container, puis lecture
du Compose et de la documentation installée sous `/home/mj/projects/freellmapi`.

| Élément | Constat |
| --- | --- |
| Container | `freellmapi-freellmapi-1`. |
| Image enregistrée | `ghcr.io/tashfeenahmed/freellmapi:latest` ; version exacte non déterminée. |
| État Docker | Arrêté, `Running=false`, code de sortie 137. |
| Arrêt enregistré | 2026-08-23 à 11:54:14 UTC. |
| OOM signalé | `OOMKilled=false` ; la cause du code 137 n'est pas établie. |
| Port configuré | `127.0.0.1:3001` vers `3001/tcp`. |
| Volume configuré | `freellmapi_freellmapi-data` vers `/app/server/data`. |

L'inspection du volume monté en lecture seule n'a trouvé aucun fichier.
Ce résultat ne confirme pas où la configuration antérieure a été conservée
et ne contredit pas le témoignage du mainteneur. Le container n'a pas été
redémarré. Conformément au choix du mainteneur, il sera démarré seulement
lorsque les travaux nécessiteront des appels à FreeLLMAPI. L'inventaire des fournisseurs actifs n'a pas été établi.

## 3. Contrat d'intégration proposé

La documentation locale décrit un point d'accès compatible OpenAI à
`http://localhost:3001/v1`, un endpoint de chat, des embeddings et un en-tête
`X-Routed-Via` pour identifier le fournisseur et modèle effectifs. Il s'agit
des capacités décrites dans le checkout local, pas de tests du container arrêté.

L'adaptateur Python de Talent Engine devrait conserver :

- une URL de base configurable côté serveur ;
- une clé de passerelle hors dépôt et hors journaux ;
- modèle demandé, fournisseur et modèle effectifs, prompt et politique versionnés ;
- validation stricte des appréciations et des références justificatives ;
- délais, erreurs et reprises bornés, sans convertir une panne en niveau zéro.

Dans Docker, `localhost` désigne le container appelant. Le routage de l'API
Talent Engine vers la passerelle existante devra donc être établi et testé
avant de fixer la configuration Compose. Ne pas exposer la passerelle
publiquement pour résoudre ce point.

## 4. Vérifications avant sélection des modèles

1. Localiser la configuration existante et vérifier l'image effectivement utilisée.
2. Lorsque l’intégration en a besoin, démarrer le container, vérifier son état et inventorier les modèles exposés et fournisseurs actifs.
3. Tester les réponses françaises, le schéma et les citations sur les mêmes fixtures.
4. Vérifier le fournisseur effectif et le comportement des changements de modèle.
5. Vérifier séparément embeddings et OCR ; un endpoint de chat ne prouve pas ces capacités.
6. Mesurer temps, quotas et limites constatées, puis retenir une configuration de démo.

La récupération sémantique ne doit jamais mélanger des espaces de vecteurs
issus de modèles différents. Les réglages de routage et de fallback doivent
préserver la traçabilité de chaque évaluation.
