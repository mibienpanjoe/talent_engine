# Audit des dépendances — 2026-10-03

`pnpm audit --audit-level high` a détecté [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) : récursion sans borne dans `braces <= 3.0.3`, sans version corrigée publiée lors du contrôle.

Chemin vérifié : `eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces`. Il appartient exclusivement aux dépendances de développement. Le paquet `braces` est absent de l’export Next standalone inspecté. Les motifs de glob viennent de la configuration du dépôt et du plugin de lint ; aucune entrée HTTP ni donnée candidat n’est transmise à ce parseur.

Une exception précise à ce GHSA est enregistrée dans `pnpm-workspace.yaml`. L’audit reste bloquant pour tout autre avis high/critical. Les workflows de PR utilisent des runners isolés, sans secrets de production, avec délai de 15 minutes. Réexaminer au prochain changement d’ESLint ou avant le 2026-10-17 ; retirer l’exception dès qu’un correctif compatible existe. Cette exception ne signifie pas que le paquet est corrigé.

Les scripts de dépendances ne sont pas autorisés globalement. Le script `unrs-resolver` est explicitement ignoré ; son binaire optionnel précompilé suffit au lint vérifié. Les installs restent verrouillées.
