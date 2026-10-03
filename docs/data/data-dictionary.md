# Talent Engine — Dictionnaire de données

**Date :** 2026-10-03. **Statut :** référence T05, modèle non migré.
Les champs publics typés sont dans [l'OpenAPI de conception](../../contracts/api-design.openapi.json).
Les contraintes relationnelles appartiennent au [modèle](canonical-model.md).

## 1. Types communs

| Type | Stockage / HTTP | Nullabilité et invariant |
| --- | --- | --- |
| ID | UUID / string uuid | Non nul, généré serveur sauf IDs stables validés d'éditeur. |
| Révision | bigint / entier JSON | ≥ 1, ≤ 9 007 199 254 740 991 ; If-Match cité pour mutations ; ne pas dépasser le domaine JS sûr. |
| Instant | timestamptz / string date-time | ISO 8601 avec fuseau en entrée, UTC `Z` en sortie. NULL uniquement si indiqué. |
| Date | date / string date | YYYY-MM-DD, sans fuseau et sans conversion d'instant implicite. |
| Secret/token | digest en base / string opaque | Aléatoire ≥ 256 bits, renvoyé une fois ; jamais logs. Idempotency-Key ≥ 128 bits. |
| Empreinte | char(64) / string hex lowercase | SHA-256 du contenu/payload avec version de canonicalisation. |
| Poids/score exact | numérateur/dénominateur / objet de chaînes d'entiers | Rapport rationnel réduit ; dénominateur positif, aucun float autoritaire. |
| Score projeté | calcul depuis rapport / string decimal ou null | 0–100, 6 décimales au plus ; null pour partiel, jamais chaîne vide. |
| Corps texte | text / string | Unicode ; limites du contrat réception ; rendu échappé. |
| JSON structuré | jsonb / schéma strict | Questions, contraintes, politique, réponse discriminée ; jamais sortie fournisseur brute faisant autorité. |

## 2. Champs critiques par entité

| Entité | Champs obligatoires | Champs optionnels / NULL |
| --- | --- | --- |
| Reviewer | id, login unique, password_hash, created_at | disabled_at |
| Session | id, reviewer_id, token_digest, csrf_digest, created_at, expires_at, last_seen_at | revoked_at |
| Campaign | id, owner_id, state, revision, list_revision, draft_configuration, created_at | active_snapshot_id, configuration_locked_at, closed_at ; deadline dans snapshot nullable |
| Snapshot | id, campaign_id, mode, version, configuration, policy_version, policy_snapshot, created_at, created_by | published_at seulement si test |
| Question | snapshot_id, question_id, type, label, required, position, constraints | help ; options seulement choix, limites fichiers seulement fichier |
| Criterion | snapshot_id, criterion_id, family, expectation, importance, evaluation_mode (qualitative/deterministic) | assessment_mode automatic/manual pour qualitatif seulement ; weight/rubric/threshold NULL pour condition, condition_rule NULL pour qualitatif |
| Application | id, campaign_id, snapshot_id, mode, received_at, contact, decision, review_revision, processing_generation | effective_evaluation_id, deleted_at |
| Answer | application_id, snapshot_id, question_id, value discriminée | Valeur absente si question facultative ; ne pas enregistrer une réponse required avec NULL |
| Upload session | id, campaign_id, snapshot_id, mode, capability_digest, created_at, expires_at | owner_reviewer_id obligatoire seulement en mode test |
| Upload | id, session_id, snapshot_id, question_id, storage_key, filename, media_type, bytes, sha256, state, created_at | application_id et attached_at avant réception |
| Receipt | id, campaign_id, mode, key_digest, canonical_version, payload_hash, received_at, expires_at, receipt_ref | application_id/manifeste purgés au tombstone ; deleted_at avant purge |
| Mutation receipt | id, owner_id, route, resource_id, key_digest, payload_hash, result, created_at, expires_at | application_id selon action ; résultat minimal sans contenu candidat, purgé si dossier supprimé |
| Analysis run | id, application_id, snapshot_id, reason, request_key_digest, state, created_at | finished_at, manifest avant fixation, error_code si échec |
| Job | id, run_id, application_id, state, lease_generation, created_at | lease_token/until/worker_id hors running ; next_attempt_at hors waiting ; error_code |
| Step | id, run_id, stage, source_key, attempts, state, input_hash | output_reference et finished_at avant succès, error_code hors échec |
| Source version | id, application_id, kind, state, created_at, extractor_version | upload_id pour document, URL/commit pour externe, content_hash/text si indisponible |
| Excerpt | id, application_id, source_version_id, text, locator, nature, excerpt_hash | auteur uniquement human_verification ; target_evaluation_id pour note humaine |
| Evaluation | id, application_id, run_id, snapshot_id, policy_version, provenance, created_at, is_complete, calculation | score_exact/score NULL si partiel ; provider/model NULL en mode préchargé, mode explicite |
| Assessment | evaluation_id, snapshot_id, criterion_id, status, rationale, uncertainties, rubric_version | level NULL sauf evaluated ; preuves selon état |
| Condition result | evaluation_id, snapshot_id, criterion_id, status, rationale | aucune note numérique ; preuves possibles même unknown |
| Review event | id, application_id, kind, author_id, created_at, revision, previous, next | motif obligatoire correction/activation, evaluation_id/cible selon kind, supersedes/reapplied_from selon événement |
| Cleanup | id, target_application_id, campaign_id, owner_id, state, created_at, attempts | application_id NULL après purge SQL ; next_attempt_at et error_code si reprise, finished_at avant succès |

Les champs révision sont bornés selon types communs même si bigint en base.
`source.kind` : `answer`, `document`, `portfolio`, `github`, `human_note`.
`source.state` : `available`, `unavailable`, `unreadable`, `blocked`.
`job.state` : queued/running/waiting/succeeded/failed/cancelled ; statut affiché
de l'analyse défini par le contrat de tâches. `review_event.kind` : correction,
restore_base, activation, decision ou title_change (ce dernier appartient à
l'historique campagne, sans candidature).

## 3. Version et localisation des preuves

Un `locator` est discriminé : question ID pour réponse, page et offsets pour
PDF/OCR, URL et offsets pour portfolio, repository/commit/path/lignes pour
GitHub, ID de note pour vérification humaine. Les offsets pointent le texte
normalisé **versionné** ; conserver extrait et empreinte pour comparaison.
URL originale et URL finale validée restent différentes. L'empreinte du PDF
n'est pas celle du texte extrait ; les deux sont conservées.

`provenance.mode` = `live` ou `preloaded`. Live conserve provider/model demandés
et effectifs, prompt_version, adapter/extractor_versions, manifeste et dates.
Préchargé conserve fixture_version et signale absence d'appel ; les champs
modèle ne prétendent pas qu'un fournisseur a exécuté l'analyse.

Les notes humaines sont de nouvelles sources, pas modifications de PDF. Une
appréciation automatique ne cite que run_evidence ; une correction peut citer
un extrait compatible ou une note dédiée à cette base, même candidature.

## 4. NULL, omission et suppressions

PATCH : champ absent = inchangé ; NULL efface seulement champ nullable et
modifiable selon état. Liste vide remplace explicitement une liste, sans
supprimer une exigence obligatoire en secret. Les champs immuables/protégés
sont refusés, pas ignorés. Réponse facultative omise n'est pas un niveau zéro.

Le tombstone ne conserve ni manifeste personnel, ni contact, ni réponse.
Les références de cleanup existent jusqu'à purge effective puis sont
minimisées ; garder key_digest/payload_hash sans accès public aux données.
Les snapshots sont de configuration sans données candidat et ne sont pas
supprimés à la fermeture. La suppression est définie par [SECURITY](../../SECURITY.md).
