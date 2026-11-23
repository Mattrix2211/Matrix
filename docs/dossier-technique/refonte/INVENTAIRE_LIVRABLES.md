# Inventaire des livrables — Matrix G0 révision 2

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle. Jalon V2 validé sur le plan documentaire (22/11/2026), basculement V3 exécuté (23/11/2026) ; aucune validation du logiciel, aucune autorisation de diffusion.

Branche `claude/fervent-wright-kl6gtx` · état applicatif B `6d6d0be` · base d'audit `637de94` · PDF produits au commit `63e9be2`.

## Les quatre PDF de référence (dossier `pdf/`)

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
| Journal d'inspection final, une ligne par page (372) | `pdf/JOURNAL_INSPECTION_FINAL.csv` ; pages relues par passe : `pdf/inspections_directes_par_passe.json` |
| Journaux intermédiaires V2 à V5 (historiques) | `pdf/JOURNAL_INSPECTION_V2.csv` à `V5.csv` |
| Contrôles des PDF (C8 renforcé compris) | `pdf/controles_GU.md`, `_RF.md`, `_DT.md`, `_RE.md`, `controles_transversaux.md`, `controle_C4.md` |
| Lisibilité des schémas | `pdf/schemas_lisibilite.csv` |
| Rapport final de recette | `RAPPORT_RECETTE_REFONTE.md` |
| Attestation de validation de V2 (empreintes, réserves, mentions historiques) | `pdf/ATTESTATION_VALIDATION_V2.md` |
| Rapports de barrière et de passe (instantanés datés) | `baseline/` |
| Plan du basculement V3, inventaire des anciens documents, compte rendu | `baseline/PLAN_BASCULEMENT_V3.md`, `baseline/inventaire_anciens_documents.csv`, `baseline/RAPPORT_BASCULEMENT_V3.md` |

## Anciens documents (archivés, non modifiés)

Première édition archivée par `git mv` dans `../archive_G0_initial/` (`diffusable/`, `restreint/` sauf `ECARTS_DECISIONS_CODE.md` et `annexes/` restés en place car cités par les PDF figés, `schemas/`, `guide-visuel/`, `pdf/` avec les deux anciens PDF, `rapports/`). Le troisième ancien PDF (guide visuel) suit `guide-visuel/`. Maquettes PDF de la V1 : `archives/apercus_V1/`. Inventaire exact (268 fichiers, SHA-256) : `baseline/inventaire_anciens_documents.csv`.
