# Extraction et provenance des pièces

Le worker extrait les réponses et PDF textuels après la réception durable,
sans appel externe et sans verrou SQL pendant l'extraction. La migration
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
ne deviennent pas des extraits destinés au modèle. Une URL est signalée comme
indisponible jusqu'à l'implémentation de sa récupération.

L'extraction suit [la documentation pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
Elle tourne dans un sous-processus sans identifiants de service : mémoire
256 MiB, CPU 8 secondes et délai 9 secondes par pièce ; maximum 30 pages,
10 MiB par flux décompressé et 200 000 caractères par document. Les extraits
font au plus 2 000 caractères. L'empreinte est revérifiée avant lecture.
Un document corrompu ou modifié devient `unreadable`. Une page sans texte
est signalée dans `ocr_pages`, avec `ocr_required` ; aucune transcription
n'est inventée. L'OCR proprement dit appartient à T24.

L'enregistrement des sources et du manifeste se fait dans le commit du
checkpoint, après vérification du bail et de la génération du dossier.
Un worker expiré ou un dossier supprimé ne peut pas publier de preuves.
Les checkpoints précédemment réussis ne sont pas réécrits à la mise à jour
du pipeline. Le format de manifeste courant est `received-sources-v2`.

`fixtures/documents/textual-demo.pdf` est un document intégralement fictif,
avec deux pages de texte. Les tests exercent sa réception HTTP, son extraction
par le worker et la persistance des pages/extraits sur PostgreSQL. Ces essais
ne prouvent pas encore une appréciation LLM, qui est l'étape suivante.
