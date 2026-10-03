# Talent Engine — Revue, corrections et résultat effectif

**Date :** 2026-10-03. **Statut :** référence d'implémentation T03 ; aucun
comportement runtime vérifié. Dépend de [l'évaluation](../evaluation/evaluation-contract.md)
et des [politiques](../evaluation/policies-and-rubrics.md).

## 1. Dimensions indépendantes

Le dossier expose état de la dernière analyse, version effective, résultats
par critère, admissibilité, alertes et décision humaine séparément. Une analyse
échouée n'efface pas une version effective antérieure. Aucune version effective
signifie `evaluation: null`, pas un score 0 ni un état « complet ».

Décisions : `to_review`, `shortlisted`, `not_selected`, initialement `to_review`.
Un responsable autorisé peut les changer sans condition de score ; une alerte
reste visible. Chaque changement conserve ancien/nouveau état, auteur/date et
motif facultatif. Les corrections d'appréciation exigent, elles, un motif.
Une décision ne modifie pas automatiquement une file d'évaluation.

## 2. Files : recouvrement explicite

Toutes les candidatures réelles non supprimées apparaissent dans `all`, y
compris queued/failed et sans évaluation. Les tests ont une liste privée
séparée. Les trois vues portent sur le **résultat effectif** :

| Vue | Prédicat |
| --- | --- |
| `ready` (« Prêts à examiner ») | Évaluation effective complète, admissibilité `eligible`/`not_applicable`, aucune alerte de compétence indispensable. |
| `needs_review` (« À vérifier ») | Pas d'évaluation effective, ou critère inconnu/contradictoire/indisponible, ou admissibilité `needs_review`, ou alerte de compétence indispensable. |
| `condition_unmet` (« Conditions non satisfaites ») | Au moins une condition indispensable explicitement `unmet`. |

Un dossier partiel avec condition incompatible apparaît dans `needs_review`
**et** `condition_unmet`. La somme des compteurs des vues n'est donc pas le
total de candidats ; `all` est l'autorité. Un nouvel échec technique avec
évaluation complète antérieure ne change pas ces prédicats : afficher son
incident séparément et permettre un filtre d'état technique.

`ready` trie par score rationnel exact décroissant ; rang de compétition
`1 + nombre de dossiers ready ayant un score strictement supérieur`. Deux
scores égaux partagent le rang, les suivants peuvent sauter un numéro. Date
de réception puis ID servent uniquement à stabiliser l'ordre entre ex æquo.
Un filtre par décision ne recalcule pas le rang au sein de `ready` ; ce rang
est calculé dans la campagne entière, au résultat effectif courant.
Les autres vues et `all` trient par date de réception décroissante puis ID,
avec rang `null`. Un dossier David complet mais incompatible garde son score
dans sa fiche, sans rang de `ready`. La pagination respecte ce tri stable.
Un rang est une organisation de revue, jamais une décision de sélection.

En liste, afficher une décimale pour score, au plus une pour couverture,
et « Évaluation partielle » pour `score: null`. Les bornes apparaissent dans
le détail avec leur sens arithmétique. Quand deux nombres affichés identiques
ont des rangs différents, indiquer la précision du calcul sur consultation ;
ne pas fabriquer une égalité à partir de l'affichage arrondi.

## 3. Couche de correction

Une évaluation automatique terminée est immuable. Le résultat effectif est
une projection de `effective_evaluation_id` et de ses corrections humaines,
recalculée côté backend avec le snapshot de cette évaluation. Une correction
ne change jamais poids, famille, politique, barème ni réponse originale.

Chaque événement de correction conserve : ID, candidature, évaluation cible,
critère/condition cible, révision de revue attendue, auteur, date, motif non
vide, valeur effective antérieure, nouvelle valeur et preuves. Les niveaux
et états respectent le contrat d'évaluation ; un `evaluated` humain possède
un extrait existant ou une note `human_verification` réellement enregistrée.
Une correction de condition cite la réponse ou note justifiant `met`, `unmet`
ou `unknown`. Les coordonnées ne constituent pas une justification de niveau.

La dernière correction d'une cible dans une même évaluation supplante la
précédente **dans la projection**, sans effacer l'historique. Revenir au
résultat automatique crée un événement `restore_base`, pas une suppression.
Le motif explique ce retour ; l'événement n'invente pas de preuve supplémentaire.
Appreciations, conditions, alertes, score, couverture et files sont recalculés
dans la même transaction que l'événement et l'incrément de `review_revision`.

Le client envoie la révision et l'évaluation effective attendues. Une autre
correction ou activation concurrente provoque `409 review_revision_conflict`,
sans écriture partielle. Les valeurs `previous`/auteur/date sont calculées par
le serveur. Le marqueur de révision renvoyé sert également à une modification
de décision ; une mise à jour silencieuse n'est jamais la résolution de conflit.

## 4. Première analyse et réanalyse

La première évaluation valide `completed` ou `completed_partial` peut devenir
effective atomiquement s'il n'existe encore aucune version effective. Une
analyse failed ou sortie LLM invalide n'en devient jamais une. Les résultats
intermédiaires ne changent pas le score affiché.

Chaque réanalyse conserve candidature, snapshot, sources/empreintes, politique,
barèmes, modèle/prompt et ID d'exécution. Elle produit une nouvelle évaluation
immuable. **Toute réanalyse attend une activation explicite du responsable**,
même sans corrections ; jusque-là, la version effective et ses corrections
restent affichées, avec la nouvelle version disponible à comparer.

L'activation porte les IDs ancien/nouveau et la révision attendue. Le responsable
choisit :

- `use_new_base` : activer la nouvelle base sans corrections ; historique
  précédent conservé, confirmation explicite que les corrections précédentes
  n'appartiennent plus à la projection active.
- `reapply_selected` : si snapshot, politique et barèmes identiques, choisir
  chaque correction à reporter ; revérifier preuve et pertinence, motif et
  nouvel état. Créer de **nouveaux** événements liés aux anciens, avec nouvelles
  valeurs antérieures ; ne jamais copier des identifiants d'extraits obsolètes.

Une vérification humaine qui reste pertinente peut être explicitement recitée
dans la nouvelle version. Une preuve externe remplacée doit être réétablie ou
la correction refusée. La transaction valide toutes les corrections sélectionnées
avant de changer le pointeur ; sinon rien n'est activé. Un changement de
snapshot/politique/barème interdit `reapply_selected` ; une nouvelle campagne
et de nouvelles corrections sont nécessaires. Une campagne gelée ne change
pas de politique par une relance.

L'activation produit un événement auteur/date/motif/options et ancien/nouveau
pointeur. La décision humaine du dossier reste indépendante. Les anciennes
évaluations sont consultables sans les substituer discrètement au résultat actif.

## 5. Scénarios à reproduire en T23/T28–T30

| Entrée/action | Résultat attendu |
| --- | --- |
| Amina et Boris complets, compatibles | ready ; rangs respectifs 1 et 2 dans cet ensemble. |
| Chloé partielle, compatible | needs_review ; score et rang null ; couverture 65. |
| David complet, incompatible | condition_unmet ; score 93,75 ; rang null. |
| Chloé partielle et incompatible | Deux vues needs_review/condition_unmet, une entrée dans all. |
| Compétence indispensable à niveau 1, conditions satisfaites | needs_review ; alerte dédiée ; pas condition_unmet. |
| Deux scores égaux au premier rang, troisième inférieur | Rangs 1/1/3 ; ordre de tie stable, score non arrondi comme autorité. |
| Chloé : pratique corrigée à 3 avec note justifiée | Score 85, couverture 100, ready si aucune autre alerte ; historique préservé. |
| Deux corrections partent de la même révision | Une réussit, autre conflit ; aucun ancien état écrasé. |
| Réanalyse après correction | Nouvelle base disponible, ancien score corrigé effectif jusqu'à activation. |
| Activation avec source de correction disparue | Reapplication refusée ; ancienne projection intacte. |
| Activation use_new_base confirmée | Nouvelle base effective, anciennes corrections consultables et décision conservée. |
| Nouvelle analyse failed, ancienne complète | Ancien résultat visible, incident distinct ; pas de zéro généré. |

Ces scénarios définissent les oracles de revue. Leur validation documentaire
ne remplace pas les tests transactionnels et parcours navigateur futurs.
