# Talent Engine — Réception durable et fichiers

**Date :** 2026-10-03. **Statut :** référence T04 ; transactions à implémenter
et éprouver sur PostgreSQL en T16–T18. Dépend du
[contrat campagne](../campaigns/campaign-and-form-contract.md).

## 1. Entrée et réception

Le candidat soumet `snapshot_id`, coordonnées, réponses typées par question,
références d'uploads et `Idempotency-Key`. Pas de champ public permettant de
choisir propriétaire, score, politique, état, marqueur de test ou décision.
Les champs supplémentaires sont refusés. Une réponse cite seulement les
identifiants de question/options du snapshot fourni.

La clé est aléatoire (au moins 128 bits), générée avant le premier envoi et
conservée pour les reprises du même dépôt. Sa portée est la campagne publique
et le mode (`real`/`test`) ; le test est une route privée distincte. Le stockage
conserve le HMAC de la clé et l'empreinte du payload canonique, pas la clé brute.
La contrainte unique porte sur `(campaign_id, mode, key_digest)`.

Payload canonique : snapshot, coordonnées/valeurs validées, ordre des réponses
par ID de question, ensembles de choix multiples triés, pièces par question
et ordre avec empreinte du contenu/taille/type détecté. Les libellés de fichier
conservés font partie du payload. Les IDs temporaires d'upload, horodatages,
ordre des clés JSON et état réseau en sont exclus. Ne pas casefold les textes
ou modifier une réponse pour lui attribuer une autre signification. Versionner
la canonicalisation (`submission-v1`) et son empreinte SHA-256.

Chercher d'abord une réception existante avant de valider une **nouvelle**
réception sous la configuration actuelle. Pour un rejeu, utiliser le snapshot
et manifeste d'uploads de la réception originale : leurs IDs soumis, hashes,
tailles/types et libellés permettent de reconstruire le payload sans rouvrir
les fichiers ni exiger une session d'upload encore vivante. Une nouvelle
référence d'upload équivalente doit être prête et appartenir à la session
présentée ; elle n'est pas attachée lors du rejeu. Après suppression, le
tombstone reconnu renvoie 410 sans tenter de reconstruire les données purgées.

- Nouvelle clé valide : `201`, référence de réception et date, sans score.
- Clé existante et même payload : `200`, même référence/date ; aucun nouvel
  upload attaché ni tâche, même après fermeture ou expiration de la campagne.
- Clé existante et payload différent : `409 idempotency_conflict`, sans écriture.

La clé est une capacité de rejeu confidentielle ; ne pas la journaliser. Le
rejeu ne révèle ni réponses, identité ni état d'analyse. Pas de route publique
de lecture de dossier. Une suppression conserve un tombstone minimal jusqu'à
expiration de la clé : le même rejeu renvoie `410 submission_deleted` au lieu
de recréer une candidature. Une autre clé peut déposer une nouvelle candidature
si la campagne l'autorise ; aucun dédoublonnage implicite par adresse email.

## 2. Préparation et propriété des fichiers

Créer une session d'upload liée à campagne/snapshot et à un secret aléatoire
256 bits renvoyé une fois. Sa capacité autorise seulement ses fichiers, pas un
dossier existant. Elle expire après 24 h. Les routes de préparation exigent
campagne ouverte/version active et contrôlent les limites avant stockage.
Le test exige session responsable et espace de stockage isolé.

Chaque upload écrit en flux dans un chemin privé aléatoire, calcule taille,
empreinte et type réel, puis ferme le fichier et marque la référence `ready`.
L'extension ou le Content-Type fourni ne fait pas autorité. Refuser fichiers
chiffrés non lisibles, archives, exécutables, SVG/HTML ; accepter seulement
PDF, PNG et JPEG détectés. Ne jamais exécuter ni servir comme contenu actif.
Pour PDF/scans, la vérification complète des pages peut se faire au worker ;
dépasser cette limite produit une erreur de source explicite, pas une note.

L'API attache seulement les références `ready` appartenant à cette session,
ce snapshot et cette question, encore non attachées et non expirées. Les IDs
d'une autre session sont refusés même s'ils sont devinés. Le nom original est
une métadonnée nettoyée, jamais un chemin ni un en-tête brut.

Le stockage temporaire et attaché utilise le même volume privé : **pas de
déplacement de fichier après commit SQL**. L'attachement modifie les références
en base. Le ramasse-miettes et la réception verrouillent la même ligne upload ;
un upload réservé/attaché n'est pas collecté. Une transaction échouée laisse
des uploads non attachés que leur session peut réutiliser, puis collecter.
Un crash après écriture avant ligne SQL produit un fichier orphelin : le
nettoyage ne retire que des fichiers âgés de plus de 24 h et non référencés.

## 3. Transaction de réception

Après validation syntaxique et empreinte canonique, ouvrir une transaction :

1. Chercher la clé existante ; traiter rejeu/conflit/tombstone avant les
   restrictions actuelles de nouvelle réception. Si concurrence, la contrainte
   unique tranche ; l'appel perdant relit la ligne après rollback.
2. Verrouiller la campagne, **relire la clé après acquisition du verrou**
   (un concurrent peut l'avoir créée), puis recontrôler état, échéance à
   l'instant de décision, snapshot actif et éventuel gel seulement pour une
   nouvelle réception. Pas d'analyse ou appel externe sous verrou.
3. Verrouiller/valider la session et ses uploads ; revalider les réponses et
   leur correspondance au snapshot. Toute erreur annule cette transaction.
4. Créer candidature et réponses, rattacher les fichiers, créer l'exécution
   initiale et sa tâche persistante, enregistrer réception et clé, poser le gel
   permanent si candidature réelle ; incrémenter révision de campagne.
5. Commit, puis confirmer. Le worker découvre les tâches en base ; aucun
   envoi à une file volatile n'est nécessaire après commit.

Une candidature reçue implique une tâche initiale dans **le même commit**.
Une exception avant commit ne laisse ni candidature, ni tâche, ni gel, ni clé
de succès. Après commit, une perte de réponse réseau se résout par rejeu.
Les octets déjà préparés restent privés indépendamment du résultat SQL.

## 4. Limites v1 et réponses

Limites de développement/démo choisies pour borner le travail, pas mesures de
capacité : configuration serveur validée, publiée avec le formulaire et jamais
abaissée au milieu d'une session sans erreur explicite.

| Ressource | Limite v1 |
| --- | --- |
| Questions/exigences par campagne | 50 questions, 20 exigences, 20 options par question |
| Texte court/long | 500 / 10 000 caractères Unicode ; libellé 200, aide 1 000 |
| Titre/description campagne | 200 / 10 000 caractères |
| Fichier / candidature | 10 MiB par fichier, 5 fichiers, 30 MiB au total |
| PDF / image | 30 pages, 25 mégapixels ; décodage borné en processus isolé |
| Réponses JSON | 256 KiB maximum, sans octets fichiers ; nombres finis, 15 chiffres significatifs maximum |
| Liens fournis | 5 liens HTTP(S) au total, 2 048 caractères par URL |
| Upload/session | 5 uploads prêts et 30 MiB ; session 24 h, préparation 120 s maximum par fichier |
| Rejeu | Clé/reçu ou tombstone conservés 90 jours à partir de la réception |

Contraintes d'une question (min/max, longueur, nombre de choix, fichiers) ne
peuvent dépasser ces bornes ; minimum ≤ maximum. Contact initial : nom et email
obligatoires, aucun diplôme/GitHub ajouté sans besoin confirmé. Dates de réponse
au format ISO date, instants de campagne ISO avec fuseau ; pas de date locale
ambiguë. Tous les échecs de validation sont localisés par question.

Erreurs : `413 payload_too_large`, `415 unsupported_file_type`,
`422 validation_error`, `409 snapshot_conflict`/`campaign_closed`/
`idempotency_conflict`, `410 upload_expired`/`submission_deleted`,
`429 rate_limited` avec `Retry-After`. L'interface conserve réponses et clé sur
erreur réseau ; changement réel du payload après réception nécessite une
nouvelle intention de dépôt, jamais un remplacement silencieux de la clé.

## 5. Scénarios transactionnels

| Incident | État attendu |
| --- | --- |
| Double clic / deux requêtes identiques simultanées | Une candidature, une exécution, une tâche ; même réception. |
| Même clé, snapshot ou réponse modifié | Conflit, aucun nouveau dossier. |
| Crash avant commit | Rien reçu ; uploads privés réutilisables jusqu'à expiration. |
| Crash après commit avant réponse | Dossier/tâche durables ; rejeu restitue la réception. |
| Service LLM hors ligne | Réception confirmée ; incident de traitement visible côté responsable. |
| Upload étranger, expiré, fichier trop grand | Nouvelle réception refusée sans création partielle. |
| Collecteur de fichiers concurrent | Fichier attaché conservé, ou référence expirée refusée avant réception. |
| Fermeture/republication concurrente | Ordre de transaction du contrat campagne, aucune version mélangée. |
| Rejeu après suppression | Tombstone 410 ; aucun dossier ressuscité. |

La [suppression](../../SECURITY.md) coordonne base, worker et volume.
Les détails d'API et contraintes de données sont définis en T05.


## Implémentation T16

La réception JSON réelle et les essais privés enregistrent candidature,
exécution, tâche, reçu et gel dans une transaction PostgreSQL. Le rejeu
précède les contrôles de version, fermeture et échéance. La liste privée
exclut les essais ; le dossier retourne le snapshot reçu avec ses réponses.
Les documents et le traitement des tâches relèvent de T17 et T18.


## Implémentation T17

Les sessions réelles et privées durent 24 h et utilisent une capacité
256 bits. Le multipart est borné pendant sa lecture, les fichiers sont
écrits par blocs et synchronisés sur le volume privé. PDF/PNG/JPEG sont
vérifiés dans un processus isolé (mémoire, CPU, délai, pages et pixels
bornés). L’attachement SQL ne déplace aucun octet. Sur résultat SQL incertain,
le fichier reste privé pour éviter de supprimer un document reçu ; les
orphelins non référencés âgés de plus de 24 h sont collectés.

Le téléchargement impose la session responsable et la propriété du dossier,
avec disposition attachment, nosniff, no-store et CSP sandbox. Le rejeu
reconstruit les fichiers originaux sans exiger leur session encore vivante ;
une nouvelle référence équivalente exige sa propre capacité et reste non attachée.
`python -m talent_engine.documents.cleanup` collecte les temporaires expirés,
sous le même verrou de ligne que la réception, puis les orphelins anciens.
