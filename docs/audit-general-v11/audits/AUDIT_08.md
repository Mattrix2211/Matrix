# Audit 08 — Maintenance et installations

**Statut : partiel.** Preuves exécutées par l'API de maintenance (client de test, base `seed_demo`) ; le parcours web d'exécution d'une fiche, la grille de saisie, les gammes, la périodicité, les fiches flotte et le catalogue n'ont pas été rejoués.

## Constats vérifiés

| Contrôle | Résultat |
|---|---|
| Clôture d'une maintenance sur installation critique sans confirmation | **refusée (400)**, refus tracé dans l'`AuditLog` |
| … avec `confirmation: true` | acceptée ; occurrence terminée ; `valide_par` renseigné ; trace d'audit |
| … avec la chaîne `"true"` au lieu du booléen | refusée (400) : strict, conforme à la règle documentée |
| Clôture d'une occurrence par un équipier non assigné hors périmètre | refusée (403) |
| Une occurrence terminée peut-elle être réécrite par l'API ? | non : 409 « corrigez-le depuis son écran, avec un motif » (lecture de code) |
| Non-conformité sur **matériel mobile** | 1 ticket correctif créé + 1 notification (signal `create_corrective_on_non_conform`) |
| Non-conformité sur **installation** | **ni ticket ni notification** par l'API (le signal ignore les installations : commentaire du code) |
| QR / scan | la route `/scan/<uuid>/` redirige bien vers l'installation, alors que les décisions disent « QR codes hors V1 » (DP-06) |

## Anomalies

- **AUD-023 (MÉTIER, P2)** : le flux documenté « inspection non conforme → ticket correctif » (`README.md`, `docs/REFERENCE.md` §5) n'est vrai que pour le matériel mobile ; pour les installations, une non-conformité saisie par l'API ne déclenche ni ticket ni alerte. Le chemin web n'a pas été rejoué : l'écran de compte rendu peut notifier le chef de secteur (décision UX-3.10) — à vérifier avant de conclure.
- Documentation du dépôt trop optimiste sur ce flux (écart de documentation).

## Non vérifié

Génération des occurrences (Celery), dérive des mesures, hiérarchie parent/enfant, fiches et circuits de validation, catalogue flotte, tournées et PDF, historique des relevés, périodicité, outillage et EPI, ressources, anomalies et rondes (module retiré).
