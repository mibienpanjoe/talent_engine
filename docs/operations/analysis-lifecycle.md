# Talent Engine — Exécution persistante des analyses

**Date :** 2026-10-04. **Statut :** contrat T04 ; orchestration de réception
implémentée en T18, adaptateurs de collecte et d’évaluation encore à raccorder. Voir [réception](../applications/submission-contract.md) et
[revue](../review/review-and-corrections.md).

## 1. Exécution, étapes et états

Une exécution appartient à une candidature et un snapshot immuables. Elle
possède un motif (`initial`, `retry_sources`, `reanalyze`), un identifiant,
une empreinte de demande et un manifeste de sources versionnées. La tâche
PostgreSQL référence cette exécution. Un rejeu de la même demande ne crée
pas une deuxième exécution ; une réanalyse intentionnelle reçoit une nouvelle
clé de demande. Une seule tâche active par candidature (queued/running/waiting)
est autorisée ; une autre demande reçoit un conflit explicite.

| État d'analyse | Sens |
| --- | --- |
| `queued` | Tâche durable en attente ; éventuellement `next_attempt_at`. |
| `collecting` | Sources en collecte/extraction ; état détaillé par étape. |
| `evaluating` | Extraits et manifeste fixés, appréciation puis calcul. |
| `completed` | Sortie valide ; tous les critères évalués. |
| `completed_partial` | Sortie valide avec au moins un critère inconnu ; pas un échec technique global. |
| `failed` | Échec global empêchant un résultat valide, tentatives épuisées ou erreur non récupérable. |

État de tâche interne : `queued`, `running`, `waiting`, `succeeded`, `failed`,
`cancelled`. `cancelled` signifie suppression du dossier ; ne pas présenter
le dossier supprimé comme une candidature encore consultable.
Une erreur isolée de source peut aboutir à `completed_partial` si le traitement
produit une appréciation valide de chaque critère, y compris inconnues.
Une réponse modèle invalide ne devient pas une inconnue synthétique pour
masquer l'échec ; elle rend l'étape de validation en échec.

## 2. Acquisition et fencing

Un worker acquiert une tâche éligible dans une transaction courte avec
`FOR UPDATE SKIP LOCKED`. Vérifier candidature non supprimée,
`next_attempt_at <= now`, absence de lease vivant, et budget d'étape disponible.
Choisir la prochaine étape non terminée et consommer sa tentative **dans cette
acquisition**, avant commit ; même un crash avant le premier appel consomme
donc le budget. Si le budget est épuisé, marquer l'échec de cette étape sans nouvel appel.
Attribuer `lease_token` unique, incrémenter `lease_generation`, fixer
`lease_until = now + 90 s`, puis commit. Les appels externes sont hors transaction.
Heartbeat toutes les 30 s avec horloge PostgreSQL, uniquement si token et
génération correspondent et candidature non supprimée.

Toute écriture de résultat/progression/finalisation vérifie à nouveau token,
génération et lease non expiré, dans la transaction avec le contrôle de
suppression. Un worker qui a perdu le lease abandonne ses sorties ; même si
l'appel externe finit, il ne peut plus écrire. Les tokens sont du fencing,
pas un contrôle fondé seulement sur heartbeat ou identité de processus.

Après expiration, une acquisition incrémente génération et reprend au dernier
checkpoint durable. Deux workers ne finalisent pas la même génération ; une
contrainte unique empêche deux sorties finales pour une exécution. L'appel
externe peut avoir été réalisé deux fois après crash ; la garantie porte sur
l'effet persistant, pas une promesse d'exactly-once chez le fournisseur.

À chaque passage à une nouvelle étape dans le même lease, consommer sa
tentative et enregistrer le checkpoint d'entrée avant travail, sous fencing.
L'acquisition après crash ne recommence jamais une étape déjà réussie.

## 3. Checkpoints et reprise bornée

Étapes : extraire les réponses, collecter chaque source externe/document,
constituer les extraits, figer le manifeste, proposer les appréciations,
valider, calculer et publier l'évaluation immuable. Chaque étape conserve
status, tentative, heures, empreinte d'entrée et sortie validée ou erreur.
Une sortie validée est réutilisée, pas réécrite en place.

Trois tentatives **au total par étape** (initiale + deux reprises), acquisitions
après crash comprises ; budget consommé au début de tentative, pas seulement
sur erreur. Temporisation après erreur technique : 30 s puis 120 s, avec
jitter 0–10 s. Délai d'appel externe 30 s, extraction locale 60 s et budget
total de travail actif par exécution 10 min (hors attente différée).
Ces bornes sont configurées et validées, pas cachées dans le prompt.

Erreur réseau/5xx/timeout → reprise si budget ; 429 → `waiting` avec raison
quota et `next_attempt_at` suivant `Retry-After` valide (maximum 1 h ; au-delà,
arrêt explicite `quota_wait_exceeded`). Consommer le même budget borné.
401/403 fournisseur → échec de configuration sans boucle automatique ;
404 ou source illisible → source indisponible, pas tentative sans fin.
Le retour `waiting` n'abandonne pas la progression publiée côté responsable.

Une reprise technique dans la même exécution utilise les checkpoints et mêmes
entrées ; une nouvelle collecte après sortie terminale crée une nouvelle
exécution. Le manifeste final contient IDs/empreintes des sources effectivement
utilisées ; la validation refuse une citation absente de ce manifeste.
Réutiliser extraction par `(content_hash, extractor_version)` et embeddings
par `(excerpt_hash, provider, model, dimensions, adapter_version)`. Pas de
vecteurs mélangés entre modèles. Les restrictions de confidentialité restent
valables pour les caches ; ne pas les partager entre candidatures.

## 4. Relance et publication

Le responsable désigne explicitement les sources échouées pour `retry_sources`.
La nouvelle exécution réutilise les sources/extraits réussis encore applicables,
recollecte les seules cibles et produit une nouvelle base d'évaluation si
nécessaire. Une source réussie dont on veut rafraîchir le contenu relève d'une
réanalyse explicite, pas d'un remplacement d'historique par reprise.

Avant finalisation, vérifier manifeste, schémas, score et versions, lease et
candidature active. Enregistrer évaluation et état terminal dans une transaction.
Si aucune version effective n'existe, l'activer avec contrôle atomique ; sinon
la laisser disponible à activer selon T03. Aucune reprise ne réapplique ni
n'efface automatiquement une correction. Source indisponible, panne de modèle
et niveau zéro restent trois informations différentes.

## 5. Suppression et observabilité

La suppression marque la candidature comme supprimée, incrémente sa génération
de traitement et annule/invalide tâche et leases dans la transaction. Chaque
finalisation verrouille/recontrôle cette même candidature. Les nettoyages sont
durables et réessayables ; un appel fournisseur déjà parti ne peut pas être
rappelé, mais son résultat tardif n'est ni enregistré ni affiché.

Événements minimisés : request/run/job IDs, étape, tentative, durée, code
d'erreur technique, modèle/fournisseur effectifs et date ; aucune réponse de
candidat, URL sensible, clé, cookie, prompt contenant des données ni CV.
Les erreurs rendues au responsable sont assainies, pas des traces brutes.
La fiche distingue état actuel, prochaine reprise et version effective.

## 6. Acceptation future

- Tuer un worker après acquisition, checkpoint puis appel externe : reprise
  bornée, ancienne génération incapable de finaliser et un résultat persistant.
- Lancer deux workers : une acquisition courante, pas de double activation.
- Simuler 429/5xx/réponse invalide : attente visible, trois tentatives maximum,
  candidature conservée, aucune note zéro générée.
- Relancer un portfolio seul : extraction PDF/GitHub inchangée réutilisée,
  nouvelle évaluation proposée, corrections précédentes intactes.
- Supprimer pendant appel : tâche annulée, résultat tardif rejeté, stockage
  nettoyé/repris sans ressusciter le dossier.


## Implémentation T18

Le service Compose `worker` acquiert via SKIP LOCKED, verrouille candidature
puis tâche, consomme la tentative avant le travail et conserve token et
génération. Une étape réussie est immutable ; la prochaine étape reçoit un
nouveau lease. Heartbeat et sorties recontrôlent lease, génération et suppression.
Le budget est de trois tentatives par étape, y compris après crash. Les
bornes par défaut sont 90 s / 30 s pour lease/heartbeat, 60 s par étape et
600 s actives par exécution, reprises différées 30/120 s avec jitter 0–10 s.
Les réglages `TALENT_WORKER_*` sont validés au démarrage.

Les étapes livrées sont la validation/extraction des réponses structurées et
le manifeste des documents et liens effectivement reçus. Elles ne téléchargent
aucune URL et n’extraient pas encore le texte des PDF : T19–T22 apportent ces
adaptateurs. L’étape d’évaluation termine avec `evaluation_unavailable`, sans
score ni version effective artificielle. Le dossier affiche les étapes,
tentatives, attente et incident réels ; la réception reste confirmée.

Les événements JSON corrèlent job/run/étape/tentative/génération et codes
assainis. Ils excluent réponses, URLs, contact, tokens et contenu de documents.
Le worker collecte les temporaires au démarrage puis chaque heure. Une panne
base/stockage est signalée et retentée sans trace contenant des paramètres SQL.

Preuves : tests PostgreSQL de concurrence, fencing, budget de trois crashes,
attentes différées, suppression en vol ; un vrai processus est tué après un
checkpoint et l’acquisition suivante. Deux processus reprennent après expiration
avec tentatives 1/2/1 : le checkpoint déjà réussi n’est pas recalculé.
