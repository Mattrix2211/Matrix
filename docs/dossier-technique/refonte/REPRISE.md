# Point de reprise — refonte documentaire G0 révision 2

> Document de travail. Plan : `../PLAN_EXECUTION_REFONTE_G0.md`. Rapport de barrière : `baseline/BARRIERE_G1.md`.

**État : phases 0 à 9 terminées ; barrière G1 « sources documentaires contrôlées » atteinte le 16/11/2026. ARRÊT : les phases 10 à 13 n'ont pas été engagées et exigent l'accord explicite du PO.** V1 (maquette) validée par le PO le 16/11/2026 sur le plan de l'architecture documentaire, des maquettes et des choix éditoriaux : cette validation ne vaut ni validation du logiciel ni autorisation de diffusion.

| Phase | État |
|---|---|
| 0 Gel et cadrage | fait |
| 1 Socle d'outillage | fait |
| 2 Registre et faits | fait |
| 3 Schémas et chapitre pilote | fait ; maquette V1 validée |
| 4 Instance et captures | fait (70 captures, `captures/`) |
| 5 Rédaction du guide utilisateur | fait (sources) |
| 6 Rédaction du référentiel | fait (sources) |
| 7 Rédaction du dossier technique | fait (sources) ; prise en main exécutée |
| 8 Annexes consultables | fait (`4_annexes_consultables/`) |
| 9 Contrôles sur sources | fait ; **G1 vert** |
| 10 à 13 | **non commencées** |

Rejouer les contrôles de la barrière G1 : `python3 outils/lancer_controles_sources.py` (rapports dans `apercus_G1/`).
Régénérer les annexes : `python3 outils/generer_annexes_consultables.py` ; les vérifier : `node outils/verifier_annexes.js 4_annexes_consultables/index.html apercus_G1`.
Instance de démonstration et captures : `outils/captures/` (copie isolée de l'état B hors dépôt, `git archive 6d6d0be`, puis `scripts/preparer_instance_test.py --reinitialiser` de cette copie et `guide-visuel/outils/enrichir_demo_guide.py`).
Contraintes permanentes : sources initiales et anciens PDF conservés ; aucun code applicatif touché ; tests A14/A20/A25 restent dans `../audit_preuves/` ; pas de PR, pas de fusion, pas de modification de `main`.
