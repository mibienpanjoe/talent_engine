# Talent Engine — Assets de marque générés

**Date :** 2026-10-03  
**Méthode :** outil intégré `image_gen`, puis inspection et sélection des sorties.  
**Statut :** sept PNG générés et inspectés ; masters vectoriels à produire.

## 1. Sources et documentation

La [référence fournie](references/talent-engine-signal-identity.png) guide le
symbole à trois cercles et étoile à quatre branches, le wordmark minuscule
et les variantes monochromes et bleues de la
[direction visuelle](visual-identity.md).

- [Manifest](../../assets/brand/manifest.json) : dimensions, alpha, empreintes et provenance.

## 2. Fichiers et usages

Les noms « dark » et « light » désignent la surface de destination.

| Asset | Dimensions | Fond | Usage |
| --- | --- | --- | --- |
| [Logo dark accent](../../assets/brand/logo-dark-accent.png) | 2172 × 724 | Anthracite opaque | Signature principale et en-tête sombre. |
| [Logo light mono](../../assets/brand/logo-light-mono.png) | 2172 × 724 | Transparent | Documents et surfaces claires, monochrome. |
| [Logo light accent](../../assets/brand/logo-light-accent.png) | 2172 × 724 | Transparent | Signature avec étoile bleue sur fond clair. |
| [Symbol light mono](../../assets/brand/symbol-light-mono.png) | 1254 × 1254 | Transparent | Symbole compact monochrome sur fond clair. |
| [Symbol light accent](../../assets/brand/symbol-light-accent.png) | 1254 × 1254 | Transparent | Symbole compact avec étoile bleue sur fond clair. |
| [Symbol dark mono](../../assets/brand/symbol-dark-mono.png) | 1254 × 1254 | Anthracite opaque | Symbole monochrome sur fond sombre. |
| [App icon dark accent](../../assets/brand/app-icon-dark-accent.png) | 1254 × 1254 | Anthracite opaque | Icône d'application et symbole avec accent sur fond sombre. |

Les assets sombres ont un fond intégré : les placer sur la surface de marque
ou dans une zone prévue pour cette signature. Ils ne sont pas des overlays
transparents interchangeables entre toutes les surfaces du dashboard.

Les PNG gardent les marges des sorties sélectionnées. Les afficher avec leur
ratio d'origine et une taille de boîte cohérente ; ne pas les déformer.
La revue a utilisé une signature à 240 px de largeur et des symboles à plusieurs
tailles. Pour la navigation, privilégier une boîte d'au moins 24 px ; à 16 px,
la finesse de l'étoile devient moins distincte.

## 3. Génération et raffinement

Le premier passage a produit des franges et résidus dans les variantes
blanches transparentes. Ces sorties ont été écartées du jeu livré. Les versions
sombres ont été régénérées sur un fond anthracite opaque ; les variantes noires
et noires/bleues conservent une véritable transparence.

Les sept sorties sélectionnées sont copiées sans transformation de pixels
dans `assets/brand/`. Les prompts demandent des aplats précis, mais les PNG
générés ne constituent pas des masters garantissant des couleurs ou contours
mathématiquement identiques. Le jeu est une base raster pour la démonstration
et l'implémentation ; un master vectoriel commun permettra de figer la géométrie.

## 4. Vérifications effectuées

- Les sept PNG se décodent ; dimensions et modes RGB/RGBA sont enregistrés.
- Les quatre variantes transparentes possèdent un alpha allant de 0 à 255.
- Les trois variantes opaques n'ont pas de transparence.
- Les copies correspondent aux empreintes des fichiers générés sélectionnés.
- Les wordmarks ont été inspectés : texte « talent engine », minuscules et
  disposition symbole/texte conservés.
- Les symboles ont été inspectés : trois cercles et étoile dans le quadrant
  supérieur droit, avec espaces entre formes.
- Lors de la revue initiale, les assets ont été exercés dans un navigateur
  Playwright à 1280 px puis 390 px : 18 placements chargés, sans débordement
  horizontal et sans erreur ni avertissement console.

Les éléments temporaires de revue ont été supprimés par le mainteneur après
inspection. Les assets sous `assets/brand/` et leur documentation servent
de base pour la suite.

## 5. Formats restant à produire

Les assets livrés sont des PNG haute résolution. Les SVG, un favicon ICO et les
exports dimensionnés pour une éventuelle PWA ne sont pas encore produits.
La revue a testé la réduction effectuée par le navigateur, pas des fichiers
favicon 16/32 px séparés. Les choix définitifs de tokens et de contraste UI
restent à vérifier sur les écrans de l'application.
