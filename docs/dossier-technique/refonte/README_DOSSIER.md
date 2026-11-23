# Dossier de documentation Matrix — révision 2 (G0 rév. 2)

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire : cette mention n'est pas une classification officielle ; la classification et les destinataires restent à valider par l'autorité compétente. Ne pas diffuser.
> **État de ce dossier (23/11/2026) : jalon V2 validé par le PO sur le plan documentaire (22/11/2026) ; basculement documentaire V3 exécuté.** Les quatre PDF de la révision 2 (`pdf/`) sont les versions de référence ; la validation est attestée dans `pdf/ATTESTATION_VALIDATION_V2.md`. Cette validation ne vaut ni validation fonctionnelle du logiciel Matrix ni autorisation de diffusion. Les anciennes arborescences et les trois anciens PDF sont archivés dans `../archive_G0_initial/`, sans suppression (`baseline/RAPPORT_BASCULEMENT_V3.md`).

## Qui lit quoi

| Je suis… | Je lis | Où |
|---|---|---|
| Marin ou chef | Le **guide utilisateur** illustré | `1_guide_utilisateur/` ; PDF `pdf/Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf` |
| Responsable, commandement, décideur | Le **référentiel fonctionnel et de gouvernance** (commencer par le résumé pour le décideur) | `2_referentiel_fonctionnel/` ; PDF `…_2_Referentiel_fonctionnel_…` |
| Développeur, mainteneur, exploitant | Le **dossier technique de reprise** (accès restreint) | `3_dossier_technique/` ; PDF `…_3_Dossier_technique_reprise_…` |
| Quiconque cherche un inventaire (routes, modèles, variables, éléments non vérifiés) | Les **annexes consultables** : ouvrir `4_annexes_consultables/index.html` (hors ligne) ou les CSV | `4_annexes_consultables/` |
| PO, responsable, mainteneur | Le **registre des écarts et décisions** (source unique : `registre.json`) | `5_registre/` ; PDF `…_5_Registre_ecarts_decisions_…` |

Les quatre PDF et leurs empreintes SHA-256 sont dans `INVENTAIRE_LIVRABLES.md` ; ils sont dans `pdf/`. Les mentions « PDF candidat … non validé » qu'ils portent sont historiques : l'attestation `pdf/ATTESTATION_VALIDATION_V2.md` fait foi.

## Fichiers d'accompagnement

| Fichier | Rôle |
|---|---|
| `INVENTAIRE_LIVRABLES.md` | Les cinq livrables, les quatre PDF (pages, taille, SHA-256), les journaux et rapports |
| `RAPPORT_RECETTE_REFONTE.md` | Rapport final de recette : contrôles C1 à C14, couverture, inspection, réserves, compteurs de reconstruction |
| `REPRISE.md` | Point de reprise : phase en cours, dernière tâche |
| `MAPPING_ANCIEN_NOUVEAU.csv` | Chaque titre de l'ancienne édition → son emplacement dans la nouvelle structure ou « retiré » avec motif |
| `faits.yaml` | Registre des chiffres (généré depuis l'inventaire du code), injecté dans les documents |
| `config/` | Identité documentaire, séparation, termes, revue manuelle des contrôles |
| `captures/` | Captures d'écran (instance de démonstration isolée, données fictives) et manifeste |
| `schemas/` | Sources Mermaid et exports SVG |
| `outils/` | Constructeur, contrôles C1 à C14, générateurs, consolidation du journal d'inspection |
| `pdf/` | PDF de la révision 2, aperçus HTML, rapports de contrôles, journaux d'inspection (le journal final est `JOURNAL_INSPECTION_FINAL.csv`, une ligne par page) |
| `archives/` | Maquettes PDF de la V1 (`archives/apercus_V1/`), archivées pour qu'elles ne soient pas confondues avec les documents validés |
| `baseline/` | Rapports de barrière, de passe, de clôture et de basculement, plan V3 ; ce sont des **instantanés datés**, non remis à jour |
| `../archive_G0_initial/` | Première édition archivée (arborescences, rapports, trois anciens PDF) : à ne plus diffuser ; table de correspondance des chemins dans son `LISEZ-MOI.md` |

## Reconstruire et contrôler

Les PDF ne sont plus à reconstruire : toute modification de contenu exige une décision du PO.

```bash
python3 refonte/outils/lancer_controles_sources.py     # aperçus HTML et contrôles sur les sources (barrière G1)
python3 refonte/outils/generer_annexes_consultables.py  # annexes consultables
python3 refonte/outils/generer_registre.py <dossier-technique> <dossier-v12> refonte/5_registre
python3 refonte/outils/consolider_journal.py refonte/pdf refonte/pdf/JOURNAL_INSPECTION_FINAL.csv   # journal par page
python3 refonte/outils/verifier_suivi.py                 # cohérence des documents de suivi et des empreintes
```

Rien dans ce dossier ne valide le logiciel Matrix ni n'autorise sa diffusion.
