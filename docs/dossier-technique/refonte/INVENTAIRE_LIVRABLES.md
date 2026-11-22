# Inventaire des livrables — Matrix G0 révision 2

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle. Jalon V2 validé sur le plan documentaire (22/11/2026) ; aucune validation du logiciel, aucune autorisation de diffusion.

Branche `claude/fervent-wright-kl6gtx` · état applicatif B `6d6d0be` · base d'audit `637de94` · PDF produits au commit `63e9be2`.

## Les quatre PDF de référence (dossier `pdf_candidats/`)

| Livrable | Fichier | Pages | Taille (octets) | SHA-256 |
|---|---|---|---|---|
| D1 Guide utilisateur | `Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf` | 86 | 19 807 858 | `966983dc5aa7ee23e644747f303b98ae37526b4641143ca1f400ed254242f0a2` |
| D2 Référentiel fonctionnel et de gouvernance | `Matrix_G0R2_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf` | 138 | 6 563 632 | `d1bd6be859883909ee2b7e42ce5ae6978faada1c1ea5c2d8f1dcd9757027e41c` |
| D3 Dossier technique de reprise | `Matrix_G0R2_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf` | 96 | 5 269 593 | `52da02728443b6b43cac92bcb44a912338378cca5a5bcf7fc59a652c4158d22c` |
| D5 Registre des écarts et décisions | `Matrix_G0R2_5_Registre_ecarts_decisions_PROVISOIRE_RESTREINT.pdf` | 52 | 1 813 119 | `45bc78edbb5629fd5a4fbe3ded8b1e37adc0047a2249927aff046a014a437caf` |

Total : 372 pages. Le D4 (annexes consultables) n'est pas un PDF : `4_annexes_consultables/index.html` et ses tables CSV.

## Autres livrables et sources

| Élément | Emplacement |
|---|---|
| Sources Markdown du guide, du référentiel, du dossier technique | `1_guide_utilisateur/`, `2_referentiel_fonctionnel/`, `3_dossier_technique/` |
| Annexes consultables hors ligne (index autonome et tables CSV) | `4_annexes_consultables/` |
| Registre vivant (source unique `registre.json`, vues générées) | `5_registre/` |
| Correspondance ancien → nouveau | `MAPPING_ANCIEN_NOUVEAU.csv` |
| Registre des chiffres | `faits.yaml` |
| Captures et manifeste | `captures/` |
| Schémas (sources et exports) et index des 46 schémas | `schemas/`, `2_referentiel_fonctionnel/31_index_des_schemas.md` |

## Preuves et rapports

| Élément | Emplacement |
|---|---|
| Journal d'inspection final, une ligne par page (372) | `pdf_candidats/JOURNAL_INSPECTION_FINAL.csv` ; pages relues par passe : `pdf_candidats/inspections_directes_par_passe.json` |
| Journaux intermédiaires V2 à V5 (historiques) | `pdf_candidats/JOURNAL_INSPECTION_V2.csv` à `V5.csv` |
| Contrôles des PDF (C8 renforcé compris) | `pdf_candidats/controles_GU.md`, `_RF.md`, `_DT.md`, `_RE.md`, `controles_transversaux.md`, `controle_C4.md` |
| Lisibilité des schémas | `pdf_candidats/schemas_lisibilite.csv` |
| Rapport final de recette | `RAPPORT_RECETTE_REFONTE.md` |
| Rapports de barrière et de passe (instantanés datés) | `baseline/` |
| Plan du basculement V3 et inventaire des anciens documents | `baseline/PLAN_BASCULEMENT_V3.md`, `baseline/inventaire_anciens_documents.csv` |

## Anciens documents (conservés, non modifiés)

`diffusable/`, `restreint/`, `schemas/`, `guide-visuel/`, `pdf/` (deux PDF « diffusable » et « restreint » de la première édition) et les rapports de la première édition restent en place jusqu'à l'arbitrage du PO. Inventaire exact : `baseline/inventaire_anciens_documents.csv`.
