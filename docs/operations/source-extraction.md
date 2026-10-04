# Extraction et provenance des pièces

Le worker extrait les réponses et PDF textuels après la réception durable,
sans verrou SQL pendant l’extraction. L’OCR conditionnel appelle la passerelle
serveur seulement pour les pages sans texte et les images. La migration
`0010_sources` ajoute les versions de sources, extraits et associations
à l'exécution. Les références composites empêchent de rattacher une preuve
à une autre candidature.

Une source conserve l'empreinte du fichier reçu, l'empreinte du texte extrait,
la version de l'extracteur, les questions associées et son état. Chaque extrait
conserve son texte, son empreinte et un localisateur : page et offsets pour
un PDF, question et offsets pour une réponse. Les offsets portent sur le
texte extrait conservé. CRLF/CR sont normalisés en LF ; NUL et Unicode invalide
sont remplacés. Le fichier original reste téléchargeable en accès privé.

Un CV reste une déclaration, même s'il est transmis sous forme de fichier.
Le même PDF reçu plusieurs fois dans un dossier donne une seule source et
n'ajoute aucun poids. Les coordonnées de contact et réponses de type email
ne deviennent pas des extraits destinés au modèle. Les portfolios publics
fournis sont collectés selon les limites ci-dessous.

L'extraction suit [la documentation pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
Elle tourne dans un sous-processus sans identifiants de service : mémoire
256 MiB, CPU 8 secondes et délai 9 secondes par pièce ; maximum 30 pages,
10 MiB par flux décompressé et 200 000 caractères par document. Les extraits
font au plus 2 000 caractères. L'empreinte est revérifiée avant lecture.
Un document corrompu ou modifié devient `unreadable`. Une page sans texte
est signalée dans `ocr_pages`, avec `ocr_required` ; aucune transcription
n'est inventée. Le worker transcrit uniquement ces pages par l’adaptateur OCR décrit ci-dessous.

L'enregistrement des sources et du manifeste se fait dans le commit du
checkpoint, après vérification du bail et de la génération du dossier.
Un worker expiré ou un dossier supprimé ne peut pas publier de preuves.
Les checkpoints précédemment réussis ne sont pas réécrits à la mise à jour
du pipeline. Le format de manifeste courant est `received-sources-v3`.

`fixtures/documents/textual-demo.pdf` est un document intégralement fictif,
avec deux pages de texte. Les tests exercent sa réception HTTP, son extraction
par le worker et la persistance des pages/extraits sur PostgreSQL. Ces essais
vérifient la provenance indépendamment du modèle. `amina-demo.pdf` est un autre
document fictif de trois pages, utilisé pour exercer le parcours complet :
dépôt HTTP, extraction, appréciation réelle via FreeLLMAPI, persistance du
score et affichage des citations dans la fiche privée. Cette recette ne
constitue pas une calibration des barèmes ni des modèles.

## OCR conditionnel

PDF textuel : aucun appel visuel. Scan : rendu de chaque page sans texte dans
un sous-processus sans credentials, via [PDFium](https://pypdfium2.readthedocs.io/en/stable/python_api.html).
PNG/JPEG : décodage isolé et orientation corrigée. Mémoire 512 MiB, CPU 8 s,
délai de rendu 9 s ; image normalisée à 1600 pixels sur le plus grand côté
et 2 MiB maximum. Le contrôle de l’empreinte originale précède le rendu.
L’ensemble de la collecte dispose de 50 s avant le plafond worker de 60 s ;
les pages hors budget restent explicitement indisponibles.

La passerelle FreeLLMAPI configurée reçoit uniquement cette image et une
consigne de transcription, sans métadonnées de contact ajoutées ni politique. Le modèle
demandé est celui configuré côté worker, actuellement `gemini-3.5-flash-lite`.
La transcription reste une sortie non fiable : aucune interprétation de ses
instructions, extraction d’extraits puis validation des appréciations séparées.
Les textes OCR et le fichier original restent distincts et consultables.
Le résultat ne garantit pas l’exactitude de tous les caractères ; le responsable
peut comparer la transcription à l’original depuis la fiche.

La migration `0013_ocr_provenance` conserve, par page, modèle demandé/effectif,
fournisseur, version de consigne, empreintes de l’image et du texte, dates et
durée, ou code d’erreur. Un 429/5xx/délai réseau utilise les reprises existantes
(jusqu’à trois tentatives) ; à la dernière tentative les pages indisponibles
restent dans la source sans texte inventé. Les autres pages extraites restent
exploitables. L’origine OCR est affichée dans le dialogue de preuve.

L’accès actuel à la passerelle et les appels Google ont été exercés ; aucun
coût effectif ni palier de facturation du compte n’est déduit d’un HTTP 200.
La [tarification officielle](https://ai.google.dev/gemini-api/docs/pricing)
dépend du modèle et du palier. Ne pas promettre une gratuité permanente.
`amina-scan-demo.pdf` est la version intégralement fictive, rasterisée sur trois
pages, de l’autre document de recette Amina.

## Portfolios publics

Le collecteur lit la page fournie et au plus deux pages pertinentes du même
hôte, à profondeur un. Il extrait uniquement le texte statique ; une page
qui exige JavaScript reste explicitement indisponible. Chaque réponse est
limitée à 2 MiB, l’ensemble du texte à 200 000 caractères, sans troncature
silencieuse, dans le budget commun de 50 secondes. Pas de cookies,
authentification, proxy ambiant ni contournement d’accès.

HTTP(S) sur ports par défaut uniquement : toutes les adresses DNS doivent
être publiques, puis la connexion utilise une IP validée avec le nom original
pour Host et TLS. Les trois redirections maximum subissent les mêmes contrôles.
Les IP locales, privées et mécanismes de transition IPv6 sont bloqués. Les
tests couvrent aussi le rebinding et une vraie réponse HTTP Connection: close.

Chaque page conserve URL finale, date, empreinte du corps reçu et texte
extrait ; chaque citation conserve URL et offsets dans ce texte. La fiche
montre le texte historique et un lien vers l’origine. Une page restreinte,
trop volumineuse ou hors budget n’empêche pas la réception du dossier.
Les 429 et erreurs transitoires utilisent les reprises du worker.

Le parcours dépôt → collecte → appréciation → fiche a été exercé sur le
portfolio public fourni par son propriétaire, avec vérification des offsets
et empreintes. La collecte valide la provenance, pas la calibration du modèle.

## Dépôts GitHub publics

Le lien doit désigner la racine d’un dépôt GitHub HTTPS public, sans paramètres.
Les variantes de casse, slash final et suffixe `.git` sont dédupliquées. Un
profil ou lien vers un fichier demande explicitement une URL de dépôt. Le
collecteur utilise uniquement l’[API officielle de contenus](https://docs.github.com/en/rest/repos/contents)
et l’[arbre Git](https://docs.github.com/en/rest/git/trees), sans token : accès
public seulement. Les redirections ne peuvent pas quitter `api.github.com`.

La branche par défaut est résolue une fois en commit SHA. Les fichiers sont
ensuite lus avec ce SHA et leur empreinte Git est vérifiée contre l’arbre.
L’arbre est borné à 1 000 entrées et 2 MiB ; un arbre tronqué n’est pas utilisé.
Lecture d’un README racine et de cinq fichiers texte au plus, en donnant
priorité aux chemins sources/tests puis à l’ordre lexical. Pas de symlinks,
submodules, code exécuté, assets binaires, clone ou consultation de commits
supplémentaires. Maximum 1 MiB par fichier, 3 MiB au total et 200 000 caractères
extraits, dans le budget de collecte commun. Ces limites sont explicites dans
la provenance. Un projet volumineux peut donc fournir une couverture partielle.

Les preuves conservent dépôt, commit, chemin, offsets, empreintes et date. Le
texte historique reste dans la fiche ; le lien original vise le même commit.
Un dépôt collectif ou possédé par le candidat ne prouve pas sa contribution
personnelle : celle-ci reste à établir séparément. La répétition du lien ne
crée pas de source supplémentaire ni de bonus. Les accès privés/404, quotas
et fichiers trop volumineux conservent la candidature avec une erreur visible.
