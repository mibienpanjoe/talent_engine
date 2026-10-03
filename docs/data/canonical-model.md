# Talent Engine — Modèle canonique

**Date :** 2026-10-03. **Statut :** modèle de référence T05 ; aucune migration
ou base applicative créée. Le [dictionnaire](data-dictionary.md) précise types
et nullabilité. Ce modèle traduit les contrats
[campagne](../campaigns/campaign-and-form-contract.md),
[réception](../applications/submission-contract.md),
[évaluation](../evaluation/evaluation-contract.md),
[revue](../review/review-and-corrections.md) et
[tâches](../operations/analysis-lifecycle.md).

## 1. Identifiants, versions et propriété

IDs internes UUID v4 générés serveur (exception : identifiants stables de
questions/exigences alloués par l'éditeur et validés serveur). Tokens publics
et capacités sont aléatoires 256 bits, distincts des IDs de lignes ; garder
leurs digests lorsque le secret n'a pas à être restitué. Tous les instants
sont timestamptz UTC. Les numéros de révision sont bigint croissants.

Un propriétaire responsable possède ses campagnes et, par elles, dossiers
et pièces ; les requêtes privées appliquent systématiquement ce périmètre.
Pas de tenant implicite ni de compte candidat. Toutes les références de
preuve sont vérifiées dans le périmètre de la candidature, même si UUID valide.

## 2. Entités et relations

| Entité | Relations et responsabilité |
| --- | --- |
| `reviewers`, `sessions` | Compte/hash de mot de passe ; sessions privées, expiration absolue/inactivité, digest de token, CSRF et révocation. |
| `campaigns` | Propriétaire, state, révision de gestion et list_revision de revue, brouillon JSON validé, snapshot actif, gel permanent et historique éditorial. |
| `campaign_snapshots` | Campagne, mode real/test, version, contenu immuable, politique/barèmes complets et publication auteur/date. |
| `snapshot_questions` | `(snapshot_id, question_id)` ; type, ordre, options et contraintes du snapshot. |
| `snapshot_criteria` | `(snapshot_id, criterion_id)` ; famille, mode, importance, barème, poids exact ou condition structurée. |
| `criterion_question_links` | `(snapshot_id, criterion_id, question_id)` ; sources attendues dans la même version. |
| `upload_sessions`, `uploads` | Capacité/snapshot/expiration ; fichiers privés temporaires puis rattachement unique à candidature/question. |
| `applications`, `answers` | Campagne/snapshot/mode, réception, coordonnées, décision/review_revision, pointeur effectif et suppression ; réponses typées immuables. |
| `submission_receipts` | Campagne/mode/key_digest unique, payload_hash/canonicalisation/manifeste, référence/date de réception, expiration et tombstone. |
| `mutation_receipts` | Actions privées : propriétaire/route/ressource/key_digest, empreinte corps et révision, résultat minimal, expiration 24 h ; références purgées avec données concernées. |
| `analysis_runs`, `analysis_jobs`, `analysis_steps` | Candidature/snapshot, intention/idempotence, manifeste, état ; tâche/lease/fencing ; checkpoint et budget par étape. |
| `source_versions`, `evidence_excerpts` | Candidature, type d'origine, URL ou fichier, contenu/empreinte/état ; localisation, texte, nature et extraction versionnés. |
| `run_sources`, `run_evidence` | Manifeste exact de sources/extraits autorisés à cette exécution. Pas d'ajout après fixation pour évaluation. |
| `evaluations`, `criterion_assessments`, `condition_results` | Base immuable d'une exécution ; résultat par critère et condition du snapshot, provenance modèle/prompt et calcul exact. |
| `assessment_evidence`, `condition_evidence` | Références aux extraits validés de la candidature et du manifeste applicable. |
| `review_events`, `review_event_evidence` | Corrections/restore_base, activation et décision ; auteur/date/motif, précédents/nouveaux états, lien de report éventuel. |
| `cleanup_requests` | Purge durable/idempotente ; target_application_id copié, campaign/owner pour accès après suppression, FK application nullable après purge ; état/reprise sans coordonnées. |
| `rate_limit_buckets` | Compteurs atomiques temporaires partagés, clé HMAC de compte/IP/campagne ; TTL, pas de contenu candidat. |

Le brouillon est un document JSON validé avec révision optimiste ; seuls les
snapshots publiés/test sont projetés en questions/critères immuables pour les
réponses et évaluations. Les JSON de politique sont validés, pas des conteneurs
libres que le modèle peut modifier. Aucun contenu privé sous assets/fixtures.

## 3. Contraintes et index à implémenter

| Invariant | Autorité de contrainte |
| --- | --- |
| Snapshot actif appartenant à campagne | FK composite `(campaign_id, active_snapshot_id)` vers snapshot ; mode real et état contrôlés au service. |
| Version de snapshot unique | UNIQUE `(campaign_id, mode, version)` ; snapshots sans UPDATE métier après création. |
| Question/critère de la bonne version | PK composites snapshot/ID ; associations avec deux FKs composites du même snapshot. |
| Candidature dans snapshot de sa campagne | FK composite campaign/snapshot et contrôle du mode real/test ; UNIQUE `(id, snapshot_id)` pour autres références. |
| Une réponse par question/dossier | UNIQUE `(application_id, question_id)` ; FKs `(application_id,snapshot_id)` et `(snapshot_id,question_id)`. |
| Upload attaché une fois au bon dossier | FK candidature/snapshot et question/snapshot, UNIQUE de référence attachée ; session/mode propriétaire vérifiés sous verrou. |
| Une réception par clé et mode | UNIQUE `(campaign_id,mode,key_digest)` ; FK candidature nullable pour tombstone. |
| Une exécution par demande | UNIQUE `(application_id,request_key_digest)` ; initiale liée au commit de réception. |
| Une seule tâche active par candidature | Index unique partiel sur application pour queued/running/waiting ; acquisition index sur state/next_attempt_at/lease_until. |
| Un checkpoint par étape/source/exécution | UNIQUE `(run_id,stage,source_key)` ; source_key explicite y compris étape sans source, pas NULL ambigu. |
| Une base d'évaluation par exécution | UNIQUE `evaluations.run_id` ; candidature/snapshot identiques à exécution. |
| Un résultat par critère/condition | UNIQUE évaluation/cible ; FK snapshot/cible ; niveau 0–4 si evaluated, NULL sinon via CHECK. |
| Références sources/extraits dans dossier | FKs composites incluant application ; manifeste validé transactionnellement avant sortie automatique. |
| Projection effective dans même dossier | FK composite `(application_id,effective_evaluation_id)` ; corrections ciblées sur cette base sous révision. |
| Poids exact valides | Numérateur ≥ 0, dénominateur > 0 ; 100 au total, répartition/politique et gcd vérifiés à compilation. |
| Dates et ordres cohérents | Révisions positives, dates/expiration valides, question order unique par snapshot, bornes de contraintes compatibles. |

Une contrainte locale CHECK ne peut garantir toutes les règles inter-lignes :
nombre de critères, somme des poids, mode et manifeste appartiennent à une
transaction de service, puis sont couverts par tests d'intégration. Les FKs
ne remplacent pas l'autorisation. Les index de revue portent campagne/mode/date
et pointeur effectif ; ne pas trier par float ou string décimale.

## 4. Transactions propriétaires

Ordre de verrou partagé quand plusieurs entités sont nécessaires : campagne,
candidature, tâche, session d'upload, uploads triés par ID. Un lecteur préalable
de clé n'est pas un verrou d'écriture ; relire après acquisition de campagne.
Les accès worker commencent à tâche pour SKIP LOCKED, la libèrent avant tout
verrou de finalisation candidature→tâche ; aucun inverse sous deux verrous.

- Publication : verrou/révision de campagne, compilation, snapshot/questions/
  critères/associations puis pointeur actif atomiques.
- Réception : campagne, clés/réponses/uploads, candidature/exécution/tâche,
  gel et réception dans le même commit, aucun appel externe.
- Worker : acquisition courte ; finalisation candidature→tâche avec token,
  génération/lease, checkpoints et base immuable ; activation initiale CAS.
- Revue : candidature sous review_revision, preuves/correction ou activation,
  projection et événements atomiques. La décision ne change pas l'évaluation.
- Suppression : candidature→tâche, marquage, invalidation/annulation et demande
  de purge ; ensuite nettoyage idempotent sans écritures tardives autorisées.

Ne jamais garder un verrou SQL pendant HTTP, extraction, OCR ou génération.

## 5. Chaîne d'intégrité à démontrer

Campagne → snapshot/politique → question → réponse/candidature → fichier ou
URL → version de source → extrait → manifeste d'exécution → appréciation →
score exact → correction/activation → projection de revue et décision.

Le test d'intégration crée cette chaîne, tente de relier un extrait d'un autre
dossier et un critère d'une autre version (refus), corrige un critère puis
vérifie score/historique, relance sans activation et supprime pendant tâche.
Les migrations initiales ne créent que les entités nécessaires à l'étape
courante ; cette cible n'exige pas un squelette complet dès T07.
