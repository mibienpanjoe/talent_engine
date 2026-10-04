# Deux démonstrations identifiées

Tous les candidats, réponses, observations et décisions de ces recettes sont
fictifs. Le jeu versionné est dans
[fixtures/demonstrations/cases.json](../../fixtures/demonstrations/cases.json).
Les références publiques optionnelles en mode réel restent des sources
distinctes ; leur présence ne prouve pas une contribution personnelle.

## Sans clé : résultats préchargés

Après démarrage, migration et initialisation du responsable :

```sh
make seed-demo
```

La commande crée deux campagnes publiées et sept dossiers : Amina, Boris,
Chloé, David, Fatou, Karim et Lina. Elle répond avec les identifiants des
campagnes et dossiers. Ouvrir l’espace responsable, puis une campagne.
Chaque résultat indique « Exemple préchargé », sa version et l’absence
d’appel modèle. Les passages cités proviennent des réponses fictives conservées.

| Domaine | Cas | Score /100 | Couverture | Disponibilité |
| --- | --- | --- | --- | --- |
| Développement | Amina | 81,25 | 100 % | Compatible |
| Développement | Boris | 65 | 100 % | Compatible |
| Développement | Chloé | Absence de score global | 65 % | Compatible |
| Développement | David | 93,75 | 100 % | Condition non satisfaite |
| Marketing | Fatou | 77,50 | 100 % | Compatible |
| Marketing | Karim | 76,25 | 100 % | Compatible |
| Marketing | Lina | Absence de score global | 65 % | Compatible |

Chloé et Lina restent à vérifier, sans rang de dossier complet. David conserve
son score mais n’entre pas dans le classement des dossiers prêts à examiner.
Ces appréciations constituent des exemples pédagogiques, pas une calibration
sur des personnes réelles.

Répéter le même mode et lot réutilise les campagnes et dossiers, même après
rotation du secret CSRF. Les corrections et décisions existantes sont conservées.
Les dossiers supprimés ne sont pas recréés tant que leur reçu de suppression
est conservé. Après expiration de la rétention de 90 jours, choisir un nouveau
lot pour une nouvelle recette. Le seed ne crée ni compte ni secret.

## Analyse réelle : nouveaux dossiers

Configurer d’abord le worker et la passerelle selon
[FreeLLMAPI côté serveur](../integrations/local-freellmapi.md).
Créer un lot distinct :

```sh
docker compose run --rm seed-demo python -m talent_engine.demo \
  --mode live --batch ma-recette-01
```

Cela crée une candidature fictive neuve par domaine. Développement reçoit
les PDF textuel et scanné d’Amina ; marketing reçoit le PDF textuel de Fatou.
La réception utilise les validations et la transaction habituelles. Les tâches
restent en attente du worker ; aucune appréciation préchargée n’est attribuée.

Pour tester aussi des références publiques expressément fournies :

```sh
docker compose run --rm seed-demo python -m talent_engine.demo \
  --mode live --batch ma-recette-sources-01 \
  --portfolio https://mibienpan.me/ \
  --github https://github.com/mibienpanjoe/swe-portfolio
```

Les liens sont ajoutés au dossier fictif développement. Le worker applique
les mêmes limites réseau et budgets que pour un dépôt public. Le dossier
affiche l’état des sources, les pages OCR, le commit GitHub, la version
effective du modèle et les passages retenus. Sans passerelle configurée, un
incident apparaît ; le dossier reste enregistré et aucun faux score n’est créé.
Une relance est possible après configuration du service.

Les résultats réels peuvent différer des exemples préchargés. Vérifier le
texte cité et le barème avant de corriger. Une citation existante prouve la
traçabilité ; elle ne certifie pas l’interprétation du modèle.

## Recette de revue

1. Ouvrir le résultat et au moins une preuve ; comparer avec la réponse ou
   le document original.
2. Corriger une appréciation avec observation et motif : le backend recalcule
   le résultat effectif ; la base automatique reste dans les versions.
3. Enregistrer une décision indépendante et consulter l’historique.
4. Relancer l’analyse : l’ancienne version reste effective jusqu’à activation.
5. Lors d’un report partiel, confirmer explicitement les corrections écartées.
6. Pour un dossier fictif jetable, demander sa suppression et vérifier le
   suivi de purge, puis l’absence du dossier et des documents privés.

## Preuves du 4 octobre 2026

Les deux seeds préchargés ont été exécutés deux fois dans Compose sans clé,
avec sorties identiques. Les tests PostgreSQL couvrent aussi deux seeds
concurrents, la rotation de secret, la conservation d’une décision et le refus
de ressusciter un dossier supprimé.

Deux nouvelles analyses ont terminé avec Groq / openai/gpt-oss-120b.
Développement : PDF textuel, trois pages OCR réussies, portfolio disponible,
GitHub au commit recueilli ; score automatique 91,25. Marketing : PDF et
réponses disponibles ; score automatique 58,75. Les deux résultats sont
explicitement en mode live, sans version de fixture.

La recette navigateur a ensuite corrigé la réalisation d’Amina au niveau 2
(score effectif 82,50) et enregistré Présélectionné. Pour Fatou, la production
de contenu a été remise à vérifier (couverture 75 %, score global absent),
puis une décision Non retenu a été enregistrée. Ces choix de recette sont
fictifs ; ils montrent la séparation entre calcul, inconnues et décision.
