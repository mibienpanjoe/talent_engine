# Talent Engine — Contrat de campagne et formulaire

**Date :** 2026-10-03
**Statut :** contrat de référence pour T01 ; gel à première candidature réelle confirmé par le mainteneur ; implémentation non vérifiée.
**Sources :** [cadrage](../product/project-overview.md),
[exigences MVP](../product/mvp-requirements-and-acceptance.md),
[décisions](../product/decision-register.md),
[moteur](../evaluation/evaluation-engine-spec.md).

Ce contrat possède le besoin, les questions, leurs associations et la version
publiée. La réception, l'idempotence et les tâches seront détaillées par T04 ;
les politiques et barèmes par T02. Aucun endpoint ni comportement runtime
n'est annoncé comme déjà implémenté.

## 1. Contenu de configuration

| Objet | Contenu et invariant |
| --- | --- |
| Campagne | Identifiant, propriétaire, type `training` ou `recruitment`, titre, domaine, description, niveau visé, échéance facultative, état et révision de gestion. |
| Exigence | Identifiant stable dans la campagne, famille, attente, importance `required` ou `desired`, mode déterministe ou qualitatif, références aux questions attendues. |
| Question | Identifiant stable, type, libellé, aide facultative, obligation de réponse, contraintes, options éventuelles et ordre. |
| Configuration publiée | Identifiant/version immuables, configuration complète du besoin et des questions, politique/barèmes versionnés, date et auteur de publication. |

Les types de question MVP sont texte court, texte long, email, nombre, date,
choix simple, choix multiple, URL et fichier. Les options possèdent des
identifiants distincts de leurs libellés ; les réponses référencent ces
identifiants. L'ordre est explicite et identique dans chaque rendu. Les
contraintes applicables au type sont vérifiées côté serveur ; leurs limites
chiffrées seront fixées dans T04/T05, sans valeurs par défaut inventées ici.

Le responsable ne saisit ni poids ni formule. Les suggestions d'exigences et
de questions requièrent sa confirmation. Une exigence non prise en charge
ne reçoit jamais automatiquement un barème arbitraire : sa résolution suit
T02. La présence d'une source attendue ne garantit ni réponse suffisante ni
compétence ; les champs facultatifs restent possibles.

Les coordonnées et informations de réception nécessaires au candidat sont
identifiées dans la configuration du formulaire, séparément des exigences
scorées. Les politiques n'attribuent aucun point aux coordonnées.

## 2. Couverture des exigences et aperçu

Chaque exigence possède au moins une question source compatible avec son
mode : réponse structurée pour une condition, réponse textuelle, document
ou lien associé pour une appréciation. Plusieurs exigences peuvent utiliser
la même question. Une association référence une question de la même
configuration ; pas de référence pendante ou vers une autre campagne.

Un brouillon incomplet peut être enregistré. Supprimer une question retire
ses associations et produit une erreur de préparation explicite si une
exigence n'a plus de source. Les corrections proposées sont : ajouter une
question, associer une question compatible ou supprimer/reformuler
l'exigence. Une association vide n'est pas réparée silencieusement.

La publication exige : champs du besoin valides, exigences résolues selon le
contrat de politique, sources associées compatibles, questions valides et
identifiants/options uniques. Elle renvoie tous les problèmes localisables
pour que l'interface conserve le brouillon et guide la correction.

L'éditeur, l'aperçu et le formulaire public utilisent le même schéma et le
même renderer de questions. L'aperçu de brouillon est identifié ; l'aperçu
publié affiche le snapshot actif. Seule l'API fait autorité pour la validation.
Une validation refusée conserve les réponses dans le navigateur.

## 3. États et transitions

| État | Accès candidat | Actions responsable |
| --- | --- | --- |
| `draft` | Aucun formulaire public de soumission | Modifier, prévisualiser, tester, publier ou dupliquer. |
| `published` sans candidature réelle | Formulaire actif tant que l'échéance n'est pas dépassée | Préparer des changements puis republier atomiquement, fermer ou dupliquer. |
| `published` avec candidature réelle | Même formulaire et politique figés | Consulter, fermer ou dupliquer ; aucune modification d'évaluation. |
| `closed` | Aucune nouvelle réception | Consulter ou dupliquer ; pas de réouverture dans le MVP. |

Le gel à première candidature réelle est la proposition issue du cadrage.
Il devient permanent même si cette candidature est supprimée plus tard :
conserver `configuration_locked_at`, sans déduire le gel du nombre actuel de
candidatures. Les analyses échouées et partielles comptent comme réceptions
réelles. Les tests ne verrouillent jamais la campagne.

Une campagne fermée garde ses dossiers et snapshots accessibles au
responsable. L'échéance est un instant stocké en UTC, présenté dans le fuseau
choisi par l'interface ; à `now >= deadline`, une nouvelle réception est
refusée, même si aucun processus n'a encore changé l'état en `closed`.
Après le gel, la date limite ne peut être prolongée ; une fermeture anticipée
reste autorisée. Il n'y a aucune suppression cascade des dossiers à fermeture.

## 4. Publication, modifications et snapshots

Chaque publication crée un snapshot immuable avant son utilisation par une
candidature. Le lien public stable de la campagne pointe vers son snapshot
actif ; tous les précédents restent identifiables. Chaque candidature et
analyse référencent explicitement le snapshot et la politique utilisés.

Avant première réception réelle, des changements sont sauvegardés en
brouillon de travail ; ils ne changent pas le formulaire actif avant une
republication validée. Une seule transaction remplace le snapshot actif.
Le responsable voit les changements non publiés et leur effet attendu.

Après première réception réelle, exigences, questions, contraintes, ordre,
associations, politique, type, domaine, niveau visé, échéance et description
du besoin sont figés. Une refonte utilise une duplication. Si un brouillon de
travail existait au moment du gel, il reste consultable pour duplication et
ne peut plus être publié sur cette campagne.

Une correction éditoriale après gel est limitée au titre d'affichage : elle
ne modifie pas le snapshot, conserve ancien/nouveau titre et auteur/date, et
ne change pas l'attente évaluée. Le produit affiche la version effectivement
soumise dans le dossier. Une correction du besoin ou des instructions de
question nécessite une nouvelle campagne ; aucun champ libre « descriptif »
modifiable après gel ne peut devenir une règle d'évaluation implicite.

## 5. Concurrence et formulaire ouvert

Toutes les mutations de gestion portent la révision attendue. Une révision
obsolète entraîne un conflit explicite et aucune écriture partielle. Le
client recharge et présente les changements ; il ne les écrase pas.

La publication, la fermeture et la première réception réelle sérialisent
leur contrôle de l'état actif de la même campagne dans la transaction.
La réception transmet l'identifiant du snapshot affiché ; elle n'est jamais
revalidée silencieusement sous une nouvelle version.

- Si la réception gagne face à une republication, elle verrouille le snapshot
  courant ; la republication échoue explicitement sans modifier la politique.
- Si la republication gagne, la soumission depuis l'ancien formulaire est
  refusée pour version périmée, sans candidature ni tâche. Le candidat conserve
  ses réponses, recharge le formulaire et confirme les réponses adaptées.
- Si la fermeture gagne, la nouvelle réception est refusée. Si la réception
  gagne, son dossier reste enregistré et la fermeture bloque les suivants.
- Deux premières réceptions simultanées valides utilisent le même snapshot ;
  la première pose le gel, la seconde reste autorisée sans nouvelle version.

L'échéance est contrôlée avec l'horloge serveur à la décision de réception
sérialisée. Un fichier envoyé avant fermeture n'autorise pas une réception
après fermeture. Le nettoyage des uploads inutilisés appartient à T04.
Une répétition idempotente d'une réception déjà enregistrée retourne sa
réception d'origine même après fermeture ; elle ne constitue pas un nouveau
dépôt. La portée et la collision de clé seront définies dans T04.

## 6. Candidatures de test et duplication

Le test est réservé au responsable authentifié et signale constamment son
mode. Il utilise un snapshot de test du brouillon choisi ou la configuration
publiée identifiée. Son éventuel traitement reste isolé des candidatures
réelles : aucun classement, compteur réel, décision de sélection ni gel.
Une requête publique ne peut choisir un marqueur de test pour contourner ces
règles. Une candidature de test ne devient pas réelle par modification d'un
champ ; il faut une nouvelle soumission publique.

Dupliquer crée une nouvelle campagne privée `draft`, un nouveau lien/token
public et de nouveaux identifiants d'exigences/questions. Les associations
sont réécrites vers ces identifiants. Copier le snapshot actif par défaut,
ou explicitement le brouillon de travail sélectionné ; annoncer lequel.
La copie n'hérite d'aucun dossier, tâche, correction, décision, date de gel
ou historique privé. La politique référencée reste vérifiée à sa publication.
L'échéance est remise à `null` et doit être revue avant publication.

## 7. Scénarios d'acceptation pour T13–T18

| Cas | Résultat observable attendu |
| --- | --- |
| Enregistrer brouillon incomplet | Sauvegarde visible ; erreurs de préparation accessibles ; aucune URL de réception active. |
| Retirer l'unique question d'une exigence | Association retirée, problème localisé, publication bloquée jusqu'à réparation. |
| Prévisualiser puis publier | Même types, contraintes, options et ordre ; snapshot et politique identifiés. |
| Modifier une campagne publiée sans réception | Formulaire actuel inchangé jusqu'à republication ; nouvelle version atomique. |
| Soumettre depuis ancien formulaire après republication | Conflit de version, réponses conservées, aucune candidature/tâche créée. |
| Première réception réelle | Candidature rattachée au snapshot, gel permanent et politique inchangée. |
| Supprimer le premier dossier | La campagne conserve son gel. |
| Republier pendant première réception | Un seul ordre de transaction ; conflit décrit en section 5, aucun mélange de versions. |
| Fermer pendant réception | Réception enregistrée avant fermeture, ou nouvelle réception refusée ; aucun dossier perdu. |
| Dépasser l'échéance | Nouvelle réception refusée par l'API, même avec page ouverte avant l'échéance. |
| Rejouer une réception après fermeture | Même réception retournée selon T04, sans nouveau dossier. |
| Tester avant/après publication | Résultat test identifié et privé ; pas de gel ni apparition dans la revue réelle. |
| Dupliquer une campagne gelée | Nouveau brouillon, identifiants et associations cohérents, échéance à revoir, aucun dossier copié. |
| Modifier avec révision périmée | Conflit explicite, aucune écriture et aucun écrasement du travail concurrent. |
| Accéder au brouillon ou au test sans session | Refus côté serveur, aucune exposition des données privées. |

## 8. Limites de cette livraison documentaire

T01 définit le contrat et les scénarios, sans prouver leur exécution.
T02 fixe compilation et barèmes ; T04 fixe transaction complète,
idempotence, fichiers et limites ; T05 traduit ces invariants en modèle et
API ; T13–T18 implémentent et exercent les comportements avec PostgreSQL et
navigateur. La pertinence d'une appréciation reste indépendante de la validité
du formulaire et de la provenance de son snapshot.
