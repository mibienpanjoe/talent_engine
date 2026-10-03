# Talent Engine — Cadrage MVP et acceptation

**Date :** 2026-10-03  
**Statut :** objectif de livraison retenu ; exigences dérivées des sources,
contrats détaillés proposés et implémentation non vérifiée.  
**Sources :** [overview](project-overview.md), [moteur](../evaluation/evaluation-engine-spec.md)
et [décisions](decision-register.md).

## 1. Objectif de livraison

Livrer le MVP du challenge avec un parcours complet et démontrable. Le
mainteneur travaille seul avec l'assistant ; cette organisation ne réduit pas
le périmètre décrit dans les sources. L'échéance et les volumes restent ouverts.

Le responsable crée une campagne, reçoit une candidature, examine une
évaluation sourcée et prend une décision. Une formation en développement et
un recrutement marketing montrent l'adaptation du même moteur à deux besoins.

## 2. Exigences et acceptation proposées

| ID | Exigence | Acceptation observable | Source |
| --- | --- | --- | --- |
| REQ-ACC-01 | Protéger l'espace responsable. | Une session autorise le responsable ; une requête privée sans accès est refusée côté serveur. | Overview §§11, 14. |
| REQ-CAM-01 | Créer une campagne guidée sans code. | Type, description, exigences et questions sont éditables ; la sauvegarde est visible. | Overview §5. |
| REQ-CAM-02 | Garantir des sources attendues par exigence. | Une suppression de question laissant une exigence sans source signale le problème et propose une correction. | Overview §5. |
| REQ-CAM-03 | Publier, fermer et dupliquer une campagne. | Le lien ouvre le formulaire attendu ; la fermeture bloque les nouvelles soumissions ; une duplication permet un nouveau besoin. | Overview §§5, 9. |
| REQ-FRM-01 | Partager le rendu entre aperçu et formulaire public. | Les mêmes questions, contraintes et ordre apparaissent dans les deux vues. | Overview §§5, 10. |
| REQ-SUB-01 | Enregistrer durablement avant l'analyse. | La candidature reçue reste consultable si un appel externe échoue ; la confirmation n'attend pas sa fin. | Overview §§6, 15. |
| REQ-SUB-02 | Recevoir une soumission une seule fois. | Double clic et reprise réseau de la même soumission ne créent pas deux candidatures. | Overview §16. |
| REQ-SRC-01 | Extraire documents et scans. | PDF textuel extrait localement ; OCR conditionnel ; document illisible signalé sans conclusion négative. | Overview §§6–7. |
| REQ-SRC-02 | Lire les liens fournis de manière ciblée. | Portfolio et GitHub publics apportent des extraits avec provenance ; panne ou restriction produit un état explicite. | Overview §7. |
| REQ-EVA-01 | Fixer une politique commune avant l'évaluation. | Les évaluations d'une campagne retrouvent la configuration et la politique utilisées ; le modèle ne choisit pas les poids. | Moteur §3. |
| REQ-EVA-02 | Sourcer chaque appréciation qualitative. | Niveau justifié par des extraits existants ou statut d'inconnue ; niveau hors bornes et référence inexistante refusés. | Moteur §§4–5. |
| REQ-EVA-03 | Traiter les inconnues séparément du zéro. | Chloé : score final absent, couverture 65 %, bornes 58,75–93,75 ; aucun faux rang de dossier complet. | Moteur §§6–7, 11. |
| REQ-EVA-04 | Calculer le score dans le backend. | Amina : 81,25 ; mêmes entrées et politique donnent le même calcul ; pas de bonus pour trois mentions du même projet. | Moteur §§6–7, 11. |
| REQ-EVA-05 | Séparer admissibilité et adéquation. | David : score 93,75 et disponibilité incompatible visibles simultanément ; aucun rejet automatique. | Moteur §§6–7. |
| REQ-REV-01 | Organiser une revue sans perdre de dossier. | Tous les dossiers restent accessibles ; les vues montrent résultats complets, inconnues et conditions non satisfaites selon un contrat explicite. | Moteur §9. |
| REQ-REV-02 | Corriger une appréciation avec historique. | Auteur, motif, anciennes et nouvelles valeurs sont conservés ; score et couverture recalculés ; réanalyse traçable. | Overview §8 ; moteur §10. |
| REQ-REV-03 | Conserver la décision humaine distincte. | Présélectionner ou ne pas retenir change la décision sans effacer l'évaluation ni confondre état de traitement et sélection. | Overview §§8–9. |
| REQ-JOB-01 | Reprendre un traitement interrompu ou en échec. | Tâche persistante, étapes visibles, tentatives bornées et reprise ciblée ; aucune panne convertie en note zéro. | Overview §§11, 15 ; moteur §10. |
| REQ-UX-01 | Livrer les écrans essentiels utilisables. | Création, formulaire, tableau et fiche utilisables au clavier et sur mobile, avec erreurs, focus et états vides ; thème sombre proposé. | Overview §10 et choix du mainteneur. |
| REQ-DEMO-01 | Démontrer les deux domaines sans masquer le mode utilisé. | Parcours développement complet, cas marketing comparable ; fixtures préchargées identifiées ; appels directs distingués. | Overview §16. |
| REQ-REL-01 | Fournir un démarrage local reproductible. | Installation depuis les instructions sur un environnement propre, migrations et données fictives disponibles ; mode sans clé expliqué. | Overview §16. |

Les valeurs de calcul sont des exemples fictifs proposés. Leur exactitude
arithmétique peut être vérifiée indépendamment ; leur politique de sélection
n'est pas calibrée sur des personnes réelles.

## 3. Limites conservées

Les exclusions du cadrage restent applicables : comptes candidats,
multi-entreprises, emails automatiques, intégrations ATS/formulaires externes,
exécution du code des candidats, exploration générale des réseaux sociaux,
entraînement d'un classement et automatisation de la décision finale.

Documents, OCR conditionnel, portfolios et GitHub ciblés restent dans le MVP.
L'ordre de réalisation ne doit pas les faire passer implicitement en extension.

## 4. Définition de la démonstration complète

Le scénario montre une nouvelle candidature persistée, une extraction réelle,
une appréciation qualitative validée et sourcée, son calcul, le rendu de la
fiche, puis une correction et une décision humaine consultables dans l'historique.
Le deuxième domaine et un dossier partiel montrent la flexibilité et les
inconnues. Les fixtures seules ne prouvent pas le chemin d'analyse en direct.

La version de politique, la contribution du candidat, les échecs techniques
et les limites des modèles restent consultables. Un incident technique ne
supprime pas la candidature ou une correction humaine.

## 5. Arbitrages nécessaires pour rendre ces exigences exécutables

Définir le cycle de configuration, les familles et leurs poids, les barèmes
marketing, l'effet des compétences indispensables, les files, le résultat
effectif corrigé, l'idempotence et les transitions de tâches. Les exigences
fixent le comportement visé ; elles ne remplacent pas ces contrats ouverts.
