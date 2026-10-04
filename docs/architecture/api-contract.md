# Talent Engine — Contrat HTTP

**Date :** 2026-10-03. **Statut :** contrat de conception T05 ; aucune route
implémentée. Schémas, paramètres, sécurité, requêtes et réponses sont décrits
dans [api-design.openapi.json](../../contracts/api-design.openapi.json).
Cet artefact manuel n'est pas le futur `contracts/openapi.json` exporté par
FastAPI. Au bootstrap, comparer l'export généré à ce contrat avant de générer
les types TypeScript ; ne pas maintenir deux autorités incompatibles.

## 1. Conventions

Préfixe `/api/v1`, JSON snake_case et enums minuscules comme les contrats métier.
Dates ISO avec fuseau, UUID, décimales en chaînes et scores rationnels exacts.
Validation stricte du corps (champs supplémentaires refusés). Les critères
conditionnels par snapshot/politique sont validés en service, pas seulement
par un schéma de transport. Nombres finis, pas de NaN/Infinity.

Les routes publiques ne révèlent ni questions de test, politiques internes,
score, dossier, clés externes ou IDs propriétaires. Le public lit le formulaire
actif et les conditions de dépôt, prépare ses pièces et reçoit confirmation.
Le lien de campagne est un token opaque ; il n'autorise aucune lecture privée.
Les uploads utilisent en plus une capacité de session par bearer token.

## 2. Accès et mutations

- `GET /access/csrf` : token anti-CSRF pour session responsable existante,
  Cache-Control no-store. Login vérifie Origin ; session/me fournit l'identité.
- Login crée/renouvelle session, cookie et CSRF ; logout révoque. Le cookie ne
  figure jamais dans le JSON. Private = session et propriétaire du dossier.
- Toute mutation privée sauf login exige `X-CSRF-Token`. Origine autorisée,
  cookie et politiques d'expiration suivent [SECURITY](../../SECURITY.md).
- Gestion campagne/décision/correction/activation : `If-Match: "revision"`
  obligatoire. GET renvoie ETag et révision ; absence → 428, obsolète → 409.
  Les corrections/activations précisent aussi `expected_evaluation_id`.
- Publication/duplication/tests/relances portent `Idempotency-Key` afin qu'un
  double clic ne crée pas deux actions ; portée route/ressource/propriétaire,
  empreinte corps + If-Match, rejeu reconnu avant précondition nouvelle action.
  Réponses d'action gardées 24 h ; les demandes de relance gardent leur unicité
  dans analysis_runs. Une même clé/payload renvoie sa réponse originale.
  Les mutations de revue répondent par event_id/révision/pointeur, sans copier
  contact/réponses dans le reçu d'action ; le client recharge ensuite la fiche.
- Réception publique suit la portée 90 jours du contrat de réception, pas
  la durée des actions privées. Ne pas réessayer automatiquement une mutation
  avec une nouvelle clé quand son résultat est inconnu.

## 3. Inventaire fonctionnel

L'OpenAPI constitue l'inventaire exact ; les groupes livrés successivement sont :

| Groupe | Routes / comportement |
| --- | --- |
| Health | live et ready, sans informations de connexion/secrets. |
| Access | session login/me/logout et CSRF. |
| Campaigns | créer/lister/lire/modifier brouillon, publications, fermeture, duplication et tests privés. |
| Public | formulaire actif ; session/upload ; réception idempotente. |
| Applications | liste campagne (vue/décision/état), fiche, téléchargement privé, suppression/purge. |
| Reviews | historique, corrections/restore_base, décision, activation explicite. |
| Analyses | versions/étapes, création relance/réanalyse ciblée et lecture d'exécution. |
| Evidence | extraits/provenance privés, politique lisible et base d'évaluation. |

Une liste utilise `limit` (1–100, défaut 25) et `cursor` opaque. Réponse
`items`, `next_cursor` nullable ; pas d'invention de total lorsque coûteux.
Le cursor lie propriétaire/campagne/vue/filtres/tri ; incompatible → 422.
Pour une liste de revue, les mutations peuvent changer score/rang : le serveur
renvoie `list_revision` et invalide un cursor dont la projection a changé
(`409 list_changed`). L'interface recharge ; pas de pagination incohérente
silencieuse. Les compteurs de chaque vue sont séparés de `all` (recouvrement).
`campaign.list_revision` est incrémentée pour réception, suppression,
changement d'état de traitement, résultat effectif, correction ou décision
qui change cette liste. Un heartbeat seul ne l'incrémente pas.

Tri des campagnes et analyses : created_at desc puis ID. Revue : règles T03,
score rationnel exact côté serveur, rang conservé sous filtre de décision.
Autres listes : ordre chronologique stable et ID ; pas de tri libre de colonne
SQL depuis une chaîne utilisateur. Le détail ouvre les preuves autorisées de
la version effective ou d'une base explicitement demandée, jamais mélange.

## 4. Erreurs homogènes

```json
{
  "error": {
    "code": "snapshot_conflict",
    "message": "Le formulaire a changé. Rechargez-le avant de confirmer.",
    "request_id": "identifiant-de-correlation",
    "details": [{"path": "snapshot_id", "code": "stale_version"}]
  }
}
```

`message` est lisible, `code` et `details[].code` sont stables. Pas de stack,
mot de passe ou réponse fournisseur brute. Les erreurs métier ne retournent
pas 200 ni un champ nullable à la place d'une erreur. Les 4xx ne consomment
pas une nouvelle tâche sauf réponse d'incident de traitement explicitement
consultable ; un appel fournisseur est postérieur à réception.

| HTTP | Codes principaux |
| --- | --- |
| 400 | malformed_request |
| 401 | authentication_required, invalid_credentials |
| 403 | csrf_invalid, forbidden ; dossier hors propriétaire reste 404 |
| 404 | not_found (ressource publique inconnue ou privée hors périmètre) |
| 409 | revision_conflict, snapshot_conflict, campaign_locked, campaign_closed, idempotency_conflict, analysis_active, review_revision_conflict, incompatible_reapplication, list_changed |
| 410 | upload_expired, submission_deleted |
| 413 / 415 | payload_too_large / unsupported_file_type |
| 422 | validation_error, invalid_cursor, invalid_evidence |
| 428 | revision_required |
| 429 | rate_limited, Retry-After obligatoire |
| 500 / 503 | internal_error / service_unavailable, sans données sensibles |

Réception 201/200 ; relance 202 avec tâche durable consultable ; suppression
202 tant que purge requise, 200 pour purge déjà achevée, 404 hors périmètre.
Une suppression répétée reconnaît la demande de purge du même propriétaire
avant les préconditions d'une nouvelle suppression ; le record minimal de
cleanup reste consultable après purge, sans reconstituer le dossier supprimé.
Fermer une campagne déjà closed avec bonne révision est sans effet et répond
200 ; une répétition avec clé retourne la réponse initiale. Expiration d'une
campagne reste consultable publiquement comme formulaire fermé sans permettre
de nouvelle réception. Tous les GET privés répondent Cache-Control no-store.

## 5. Vérification de l'implémentation future

Exporter les schémas FastAPI, comparer routes/méthodes/required/enums/sécurité,
générer le client, vérifier absence de dérive et compiler le consommateur.
Tests : ID d'extrait étranger, body inconnu, révision absente/obsolète,
session/CSRF, plusieurs pages après changement de classement, double dépôt,
upload étranger et réanalyse sans changement implicite du résultat effectif.
Un OpenAPI validé structurellement ne démontre pas les transactions SQL.


## Surface implémentée en phase campagne et réception

`contracts/openapi.json` exporte les routes effectivement exécutées ; le client
web en dérive. Le contrat de conception conserve la cible des phases suivantes.
La réception annonce 201 et son rejeu 200, les quotas 429 avec Retry-After.
Le multipart explicite question_id/file, sous borne ASGI et capacité privée.

Le dossier privé inclut son snapshot reçu, ses uploads téléchargeables et les
étapes de ses exécutions, sans exposer sorties brutes de checkpoints ni tokens
de lease. PATCH campagne accepte configuration ou titre d’affichage, jamais
les deux. `GET /campaigns/{id}/title-history` ajoute l’historique éditorial
privé sans modifier les snapshots.

Les façades `*/data.py` exposent le schéma transactionnel partagé nécessaire
à la réception multi-domaines. Chaque service possède ses validations ; le
caller contrôle le commit commun. Les consommateurs n’importent pas le
repository privé d’un autre domaine, et le worker enregistre les modèles sans
construire l’application HTTP.


La pagination des candidatures utilise un curseur opaque signé, lié au
responsable, à la campagne et à list_revision. Une nouvelle réception l’invalide
avec `409 cursor_invalidated`. La liste et le détail utilisent une transaction
REPEATABLE READ pour rendre une vue cohérente des données et étapes.
