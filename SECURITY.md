# Protection des données et frontières de confiance

**Date :** 2026-10-03. **Statut :** règles d'implémentation du MVP ; aucune
revue de sécurité runtime ni conformité réglementaire démontrée à ce stade.

## Accès et secrets

Un responsable de démo, sans inscription publique ni multi-entreprises.
Mot de passe initial fourni hors Git, hash Argon2id, session opaque aléatoire
256 bits dont seul le digest est en base. Cookie HttpOnly, SameSite=Lax,
Secure sous HTTPS, chemin `/`, sans Domain ; session limitée à 8 h absolues
et 1 h d'inactivité, révoquée au logout. Local HTTP autorisé uniquement en
développement sur loopback, avec cookie de développement distinct.

Toutes les routes privées contrôlent session et propriétaire côté API.
Mutations privées exigent CSRF lié à session et Origin autorisé ; login
contrôle également Origin pour prévenir login CSRF. Le web et `/api/v1` sont
exposés sous une origine via proxy local ; pas de CORS wildcard avec cookies.
Compte/session/clé de test ne sont jamais dérivés d'un champ envoyé par le
candidat. Aucun endpoint public ne lit scores, évaluations ou pièces.

Clés de passerelle/tiers exclusivement côté serveur, environnement privé ;
`.env.example` sans valeur réelle. Aucun secret dans repo, bundle frontend,
URL, prompt ou logs. HTTPS requis avant toute exposition Internet ; le mode
local ne constitue pas un déploiement sécurisé démontré.

## Limites publiques et fichiers

Limites du [contrat de réception](docs/applications/submission-contract.md).
Rate limits initiaux : login 5 essais / 15 min / compte et IP ; réception
10 requêtes/min/IP et 100/min/campagne ; création upload-session 10/min/IP ;
upload 20/min/IP, 2 transferts simultanés/session. Rejeu compte dans limite
de requêtes mais ne crée pas de dépôt. Compteurs atomiques partagés API via
PostgreSQL avec TTL, IP issue seulement de proxy de confiance. Un 429 renvoie
Retry-After ; ils bornent l'abus et ne constituent pas une capacité mesurée.

Stockage hors `public/` et Git, noms aléatoires, traversées de chemin refusées,
contrôle taille/type réel et décodage PDF/image isolé/borné. Consultations
privées via API, Content-Disposition attachment et nosniff ; l'aperçu sûr
utilise renderer isolé, jamais du HTML arbitraire fourni. Les dépendances de
parsing sont verrouillées et leurs avis de sécurité revus au bootstrap.

## Collecte et contenu non fiable

URLs HTTP(S), sans identifiants utilisateur intégrés, ports 80/443 seulement.
Résoudre tous les enregistrements IPv4/IPv6, refuser toute adresse non publique
(loopback, privée, link-local, réservée, multicast, métadonnées). Épingler
l'IP validée pour la connexion en conservant Host/SNI ; même contrôle à chaque
redirection, maximum 3. Une simple validation DNS suivie d'une résolution
automatique HTTP ne suffit pas contre le rebinding.

Portfolio : page fournie puis maximum 2 pages du même hostname, profondeur 1,
3 pages au total ; 2 MiB/page décompressée et 30 s/appel, budget par exécution
du contrat de tâches. Refuser réponse protégée, non textuelle ou nécessitant
contournement ; statut explicite pour rendu JS non pris en charge.
GitHub : hôte officiel/API officielle, dépôt explicitement fourni, README et
maximum 5 fichiers de texte, 1 MiB/fichier et 3 MiB au total ; snapshot au
commit utilisé, aucun téléchargement/exécution générale de code. Respecter
quotas et restrictions ; un profil seul invite à fournir un projet précis.

Réponses, CV, README et pages sont des données non fiables. Les instructions
qu'ils contiennent n'ont aucune autorité sur prompts système, poids, barèmes,
outils ou destinations réseau. Le modèle ne reçoit que les extraits utiles,
avec coordonnées exclues quand inutiles ; validation stricte des sorties et
provenance. Pas d'outil de shell/code candidat ni d'accès à des secrets du
serveur par le modèle. Nettoyer le rendu de texte/Markdown, interdire HTML
actif et liens javascript. Les échecs d'accès ne prouvent rien sur une compétence.

## Rétention et suppression

Pour la démo : données de candidature conservées 90 jours depuis réception,
sessions de test et uploads non attachés 24 h, logs techniques 7 jours. Les
snapshots/politiques peuvent rester comme configuration sans données candidat.
La suppression manuelle est disponible avant échéance. Pas de backup privé
configuré dans le MVP ; tout futur backup exige un contrat de rétention séparé.

Suppression en deux temps durables :

1. Transaction : marquer dossier supprimé, révoquer accès, annuler tâches et
   leases, figer tombstone de réception, créer demande de purge. Le dossier
   disparaît immédiatement des lectures ; aucune tâche ne peut le finaliser.
2. Purge idempotente : retirer pièces et leurs caches, extraits, embeddings,
   réponses, évaluations/corrections/notes et références personnelles en base.
   Réessayer les suppressions de fichiers échouées ; suivre leur état sans
   déclarer purge terminée avant contrôles SQL et stockage. Ne pas partager
   les octets privés entre dossiers via déduplication globale.

Le tombstone garde seulement campaign ID, mode, HMAC de clé, empreinte du
payload et expiration initiale de 90 jours ; aucun contact/réponse/note.
À expiration, le retirer. Conserver les dossiers sous tombstone logique
uniquement jusqu'à purge ; les IDs de traitement ne permettent aucune lecture
publique. Interdire la réactivation d'une évaluation supprimée et ignorer les
résultats externes tardifs. Les [leases](docs/operations/analysis-lifecycle.md)
et nettoyages partagent ce contrôle ; pas de donnée ressuscitée.

## Incidents et preuve

Les profils de démo sont fictifs et les résultats préchargés identifiés.
L'information candidat annonce analyse automatisée et éventuels fournisseurs
distants ; une passerelle localhost ne signifie pas une inférence locale.
Un incident donne un code assaini, des IDs de corrélation et une action de
reprise, sans CV/secret dans traces. Avant usage réel, revoir contexte de
traitement, base légale, prestataires et conservation ; ce document fixe
des mesures techniques, pas un avis juridique.

Vérifications prévues : accès direct non autorisé, CSRF/login, upload étranger,
fichier hostile, SSRF et rebinding, injection de prompt, fuite bundle/logs,
suppression concurrente et purge interrompue. T11/T17/T22/T25/T31 les exercent.
