# Point de reprise — refonte documentaire G0 révision 2

> Document de travail. Plan : `../PLAN_EXECUTION_REFONTE_G0.md`. Rapport : `RAPPORT_JALON_V1.md`.

**État : phases 0 à 3 terminées ; ARRÊT au jalon V1 (validation PO requise).** Ne pas lancer la phase 4 ni la rédaction sans accord explicite.

| Phase | État |
|---|---|
| 0 Gel et cadrage | fait (mapping, faits, arborescence) |
| 1 Socle d'outillage | fait (`baseline/BARRIERE_G1a.md`) |
| 2 Registre et faits | fait (`baseline/BARRIERE_G2.md`) |
| 3 Schémas et pilote | fait ; aperçus dans `apercus_V1/` |
| 4 et suivantes | **non commencées** |

Reconstruire les aperçus : `python3 outils/lancer_controles_pilote.py` (nécessite Node/Playwright, pypdfium2, markdown, pyyaml).
Instance de démonstration et captures : voir `../guide-visuel/outils/` ; copie isolée de l'état B hors dépôt (`git archive 6d6d0be`).
Contraintes permanentes : sources initiales et anciens PDF conservés ; aucun code applicatif touché ; tests A14/A20/A25 restent dans `../audit_preuves/`.
