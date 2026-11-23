# Compte rendu du basculement documentaire V3 (phase 13)

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle.
> Exécuté le 23/11/2026 sur la branche `claude/fervent-wright-kl6gtx`, en un seul commit, selon le plan `PLAN_BASCULEMENT_V3.md` arbitré par le PO (option A ; PDF dans `refonte/pdf/` ; anciens PDF archivés sans suppression ; maquettes V1 archivées ; attestation séparée). Aucun code applicatif touché, aucune reconstruction, aucune fusion dans `main`, aucune diffusion. Le hash du commit figure dans `git log` (message « basculement V3 »).

## Déplacements (`git mv`, 287 renommages, tous à 100 % de similarité : aucun contenu modifié)

| Origine (depuis `docs/dossier-technique/`) | Destination | Fichiers |
|---|---|---|
| `diffusable/` | `archive_G0_initial/diffusable/` | 21 |
| `restreint/` (22 chapitres numérotés) | `archive_G0_initial/restreint/` | 22 |
| `schemas/` (première édition) | `archive_G0_initial/schemas/` | 84 |
| `guide-visuel/` (dont `pdf/Matrix_Guide_visuel_G0.pdf`) | `archive_G0_initial/guide-visuel/` | 72 |
| `pdf/Matrix_Dossier_technique_G0_DIFFUSABLE.pdf`, `…_RESTREINT.pdf` | `archive_G0_initial/pdf/` | 2 |
| Rapports et propositions de la première édition | `archive_G0_initial/rapports/` | 11 |
| `00_LISEZ-MOI.md`, `GUIDE_DE_LECTURE.md` | `archive_G0_initial/` | 2 |
| `refonte/apercus_V1/` (maquettes V1, dont cinq PDF) | `refonte/archives/apercus_V1/` | 40 |
| `refonte/pdf_candidats/` | `refonte/pdf/` | 33 |

Restés en place (option A) : `restreint/ECARTS_DECISIONS_CODE.md`, `restreint/annexes/` (7 fichiers), `audit_preuves/`, `couverture/`, `outils/`, `AUDIT_GLOBAL_G0.md`, `PLAN_EXECUTION_REFONTE_G0.md`.

Fichiers créés : `LISEZ-MOI.md` (racine), `archive_G0_initial/LISEZ-MOI.md` (statut et table de correspondance des chemins), `refonte/archives/LISEZ-MOI.md`, `refonte/pdf/ATTESTATION_VALIDATION_V2.md`, `refonte/outils/chemins.py`, `refonte/outils/verifier_basculement.py`. Rien n'est supprimé.

## Mises à jour documentaires et outils (aucun contenu métier, schéma, décision ni statut modifié)

- Documents de suivi : `README_DOSSIER.md`, `REPRISE.md`, `INVENTAIRE_LIVRABLES.md`, `RAPPORT_RECETTE_REFONTE.md`, `PLAN_BASCULEMENT_V3.md` (ligne de statut), `.gitignore` (nouveau chemin des aperçus HTML).
- Outils : les lectures de l'ancienne édition passent par `chemins.py` (chemin d'origine, sinon archive) dans `controles.py`, `controle_perte_contenu.py`, `convertir_chapitres.py`, `generer_mapping.py`, `resoudre_renvois_anciens.py` ; `verifier_references_refonte.py` accepte une preuve archivée ; `lancer_controles_pilote.py` et `dossier_presentation.py` pointent vers `archives/apercus_V1` ; `verifier_suivi.py` lit `pdf/`.
- Inchangés : les quatre PDF, les sources, `MAPPING_ANCIEN_NOUVEAU.csv`, le registre, les annexes, les rapports datés de `baseline/`.

## Résultats des vérifications (§6 du plan)

| Vérification | Résultat |
|---|---|
| Renommages | 287, tous R100 ; aucune modification de contenu |
| Inventaire des 268 anciens fichiers (`verifier_basculement.py`) | tous retrouvés à leur destination, SHA-256 identiques ; aucun présent aux deux endroits ; aucun ancien dossier subsistant |
| SHA-256 des quatre PDF | identiques à l'attestation et à l'inventaire des livrables (`verifier_suivi.py` : 6 documents de suivi, 372 pages, 0 écart) |
| Journal d'inspection | recalculé par `consolider_journal.py` : identique octet pour octet, 372 lignes |
| Attestation | quatre empreintes, 16 réserves, date du 22/11/2026, renvoi au rapport de recette : vérifiés par `verifier_suivi.py` |
| Citations de chemins anciens par les documents de la révision 2 (21) | toutes existent à l'endroit cité (option A) ou à la destination décrite par la table de correspondance |
| Liens relatifs des fichiers Markdown | 0 cassé avant, 0 cassé après |
| Barrière G1 (`lancer_controles_sources.py`) | 0 bloquant ; rapports de contrôles et aperçus HTML des quatre documents identiques à ceux d'avant le basculement |
| C1 à C14 sur les quatre PDF (`controles.py doc`, `global`) | 0 bloquant ; rapports identiques aux rapports validés (C1 507/507, C8 renforcé : 0 coupure) |
| C4 références de code (709 clés) | 0 erreur (voir anomalie 1) |
| C7/C11 | 125 décisions sur 125 avec leur état ; 0 écart de relation des schémas |
| C12 | régénérations du registre, des annexes consultables, de l'index des schémas et de la correspondance : sans différence ; `test_coupures.py` : 0 coupure sur 60 chapitres, 8 détectées sans les règles |
| Contrôle de perte de contenu | 178 lignes « non retrouvées telles quelles » avant et après (résultat inchangé) ; renvois non résolus : 1 avant, 1 après |
| C13 | 0 fichier hors documentation modifié depuis `637de94` ; `main` non touchée |

## Anomalies

1. **Contrôle C4 en échec au premier passage (3 erreurs)** : trois preuves de l'entrée AUD du registre (`guide-visuel/RAPPORT_GUIDE_VISUEL_G0.md`, `restreint/13_logistique_technique.md`, `restreint/23_configuration_deploiement_exploitation.md`) n'existaient plus à l'ancien chemin. Correction dans l'outil seulement : la vérification d'existence accepte désormais le chemin dans l'archive (la preuve doit toujours exister) ; texte du registre inchangé. Résultat après correction : 0 erreur, rapport identique à celui d'avant.
2. **Effet attendu, non corrigé** : les PDF figés citent d'anciens chemins qui ont changé d'adresse (rapports de la première édition, `00_LISEZ-MOI.md`, `restreint/13_…`, `restreint/23_…`, `guide-visuel/RAPPORT_GUIDE_VISUEL_G0.md`) ; ils se lisent avec la table de correspondance de `archive_G0_initial/LISEZ-MOI.md`. Les références vivantes citées (`restreint/ECARTS_DECISIONS_CODE.md`, `restreint/annexes/B_matrice_role_action.md`, `couverture/`, `audit_preuves/`) sont intactes.
3. Les mentions « PDF candidat … non validé » des quatre PDF sont conservées : l'attestation `refonte/pdf/ATTESTATION_VALIDATION_V2.md` fait foi.

Aucune autre anomalie. La validation du basculement relève du PO.
