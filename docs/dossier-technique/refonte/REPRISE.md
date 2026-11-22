# Point de reprise — refonte documentaire G0 révision 2

> Document de travail. Plan : `../PLAN_EXECUTION_REFONTE_G0.md`. Rapport de recette : `RAPPORT_RECETTE_REFONTE.md`. Inventaire : `INVENTAIRE_LIVRABLES.md`.

**État au 22/11/2026 : phases 0 à 12 terminées ; jalon V2 validé par le PO sur le plan documentaire** (quatre PDF acceptés comme versions de référence, avec réserves connues et documentées ; ni validation fonctionnelle du logiciel, ni autorisation de diffusion). **Phase 13 : préparation engagée, basculement non exécuté.** Le plan V3 (`baseline/PLAN_BASCULEMENT_V3.md`) attend l'arbitrage du PO : aucun fichier n'est déplacé, aucun ancien PDF n'est retiré, aucune reconstruction n'est autorisée.

| Phase | État |
|---|---|
| 0 Gel et cadrage | fait |
| 1 Socle d'outillage | fait |
| 2 Registre et faits | fait |
| 3 Schémas et chapitre pilote | fait ; maquette V1 validée le 16/11/2026 |
| 4 Instance et captures | fait (72 captures au manifeste, `captures/`) |
| 5 Rédaction du guide utilisateur | fait |
| 6 Rédaction du référentiel | fait |
| 7 Rédaction du dossier technique | fait ; prise en main exécutée |
| 8 Annexes consultables | fait (`4_annexes_consultables/`) |
| 9 Contrôles sur sources | fait ; barrière G1 atteinte le 16/11/2026 |
| 10 Construction des PDF candidats | fait |
| 11 Inspection à taille réelle | fait ; journal par page `pdf_candidats/JOURNAL_INSPECTION_FINAL.csv` (372 pages) |
| 12 Corrections et cohérence | fait ; rapport `RAPPORT_RECETTE_REFONTE.md` ; jalon V2 validé |
| 13 Basculement | **préparation seulement** : plan V3 en attente de validation du PO |

Reconstructions réelles après la première construction candidate (jamais remises à zéro) : guide 5, référentiel 9, dossier technique 5, registre 3. Le PO ne demande plus de reconstruction.

Rejouer les contrôles : `python3 outils/lancer_controles_sources.py` (rapports dans `apercus_G1/`), puis `python3 outils/verifier_suivi.py` (cohérence des documents de suivi et des empreintes des PDF).
Régénérer les annexes : `python3 outils/generer_annexes_consultables.py` ; les vérifier : `node outils/verifier_annexes.js 4_annexes_consultables/index.html apercus_G1`.
Instance de démonstration et captures : `outils/captures/` (copie isolée de l'état B hors dépôt, `git archive 6d6d0be`).
Contraintes permanentes : sources initiales et anciens PDF conservés jusqu'à l'arbitrage du PO ; aucun code applicatif touché ; tests A14/A20/A25 dans `../audit_preuves/` ; pas de PR, pas de fusion, pas de modification de `main` ; aucune diffusion externe.
