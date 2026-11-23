# Plan du basculement V3 (phase 13) — pour validation du PO

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle.
> **Statut : plan arbitré par le PO le 23/11/2026 et exécuté (option A ; PDF dans `refonte/pdf/` ; anciens PDF archivés sans suppression ; maquettes V1 dans `refonte/archives/apercus_V1/` ; attestation séparée).** Texte d'origine conservé ci-dessous ; compte rendu : `RAPPORT_BASCULEMENT_V3.md`.

Branche `claude/fervent-wright-kl6gtx` · PDF de référence du commit `63e9be2` · inventaire exact de 268 fichiers : `inventaire_anciens_documents.csv` (chemin, taille, SHA-256, catégorie, destination proposée dans chaque option, citation par les documents de la révision 2). Les chemins sont donnés depuis `docs/dossier-technique/`.

## 1. Documents de la révision 2 retenus

| Livrable | Retenu | Empreinte SHA-256 |
|---|---|---|
| Guide utilisateur (86 p.) | oui | `966983dc5aa7ee23e644747f303b98ae37526b4641143ca1f400ed254242f0a2` |
| Référentiel fonctionnel et de gouvernance (138 p.) | oui | `d1bd6be859883909ee2b7e42ce5ae6978faada1c1ea5c2d8f1dcd9757027e41c` |
| Dossier technique de reprise (96 p.) | oui | `52da02728443b6b43cac92bcb44a912338378cca5a5bcf7fc59a652c4158d22c` |
| Registre des écarts et décisions (52 p.) | oui | `45bc78edbb5629fd5a4fbe3ded8b1e37adc0047a2249927aff046a014a437caf` |
| Annexes consultables (index autonome et CSV), sources Markdown, registre `registre.json`, captures, schémas, outils, rapports, journaux | oui | — |
| Cinq PDF de maquette V1 (`refonte/apercus_V1/`) | **à arbitrer** : ils portent le pied « maquette pilote V1, non validé » | voir §6 |

## 2. Emplacement définitif proposé

| Élément | Aujourd'hui | Proposition |
|---|---|---|
| Quatre PDF, aperçus HTML, rapports de contrôles, journaux | `refonte/pdf_candidats/` | **`refonte/pdf/`** (renommage du dossier, `git mv`, contenu et noms de fichiers inchangés, empreintes identiques) |
| Sources, annexes consultables, registre, captures, schémas, outils, rapports | `refonte/…` | inchangés |
| Point d'entrée | `refonte/README_DOSSIER.md` | inchangé ; un court `LISEZ-MOI.md` à la racine du dossier technique renvoie vers lui et vers l'archive |
| Documents conservés en place | `audit_preuves/` (25 fichiers), `couverture/` (6), `outils/` (13, qui génère `couverture/`), `AUDIT_GLOBAL_G0.md`, `PLAN_EXECUTION_REFONTE_G0.md` | inchangés |

Variante : placer les PDF dans `pdf/` à la racine, comme le prévoit le plan initial, une fois les deux anciens PDF archivés. Je recommande `refonte/pdf/` : tout le nouveau dossier tient sous `refonte/`, sans mélange avec l'ancien.

## 3. Sort de chaque ancienne arborescence et de chaque ancien PDF

Deux options (le choix du PO porte sur la deuxième colonne ; la destination `archive_G0_initial/` est créée par `git mv`, rien n'est supprimé).

| Ancien élément | Fichiers | Option A (recommandée) | Option B |
|---|---|---|---|
| `diffusable/` | 21 | `archive_G0_initial/diffusable/` | idem |
| `restreint/` (chapitres et annexes sauf ci-dessous) | 22 | `archive_G0_initial/restreint/` | idem |
| `restreint/ECARTS_DECISIONS_CODE.md` et `restreint/annexes/` (8 fichiers) | 8 | **laissés en place** : les PDF définitifs les citent comme références en ligne et les outils de génération des annexes et du registre les lisent | `archive_G0_initial/restreint/` + table de correspondance |
| `schemas/` (42 schémas) | 84 | `archive_G0_initial/schemas/` | idem |
| `guide-visuel/` (captures, outils, rapport) | 71 | `archive_G0_initial/guide-visuel/` | idem |
| Rapports et propositions de la première édition (bilan, qualification, clôture, E1 à E4, revue, synthèse, proposition, sommaire) | 11 | `archive_G0_initial/rapports/` | idem |
| `00_LISEZ-MOI.md`, `GUIDE_DE_LECTURE.md` | 2 | `archive_G0_initial/` (remplacés par `README_DOSSIER.md`) | idem |
| `pdf/Matrix_Dossier_technique_G0_DIFFUSABLE.pdf`, `…_RESTREINT.pdf` | 2 | **`archive_G0_initial/pdf/`, sans suppression** ; retrait irréversible seulement sur ordre explicite du PO | idem |
| `guide-visuel/pdf/Matrix_Guide_visuel_G0.pdf` | 1 | `archive_G0_initial/guide-visuel/pdf/` (suit son arborescence) | idem |

Les trois anciens PDF portent l'en-tête « DIFFUSION GÉNÉRALE » : ils ne doivent plus circuler. L'archivage les déplace sans les supprimer ; l'historique git les conserve de toute façon. Un fichier `archive_G0_initial/LISEZ-MOI.md` indiquera ce statut et la table de correspondance des chemins.

## 4. Chemins et liens à mettre à jour

| Où | Occurrences | Mise à jour proposée |
|---|---|---|
| Outils de la révision 2 qui lisent l'ancienne arborescence : `controles.py` (C1, C2, mode « ancien »), `convertir_chapitres.py`, `controle_perte_contenu.py`, `resoudre_renvois_anciens.py`, `generer_mapping.py`, `generer_index_schemas.py`, `lancer_controles_pilote.py`, `verifier_references_refonte.py` | 8 fichiers, une cinquantaine de lignes | une constante unique pour la racine de l'archive ; aucun comportement modifié |
| `generer_registre.py`, `generer_annexes_consultables.py` | `restreint/ECARTS_DECISIONS_CODE.md`, `restreint/annexes/` | aucune en option A ; constante d'archive en option B |
| `MAPPING_ANCIEN_NOUVEAU.csv` (549 chemins d'anciens titres) et commentaires `<!-- couvre: … -->` des sources | 549 lignes | **inchangés** : les chemins anciens se lisent désormais relatifs à `archive_G0_initial/` (note dans le fichier d'entrée) |
| Les PDF définitifs | 21 chemins anciens cités (voir §5) | **non modifiables** (aucune reconstruction) : résolus par la table de correspondance de `archive_G0_initial/LISEZ-MOI.md` et de `README_DOSSIER.md` |
| `registre.json` et vues du registre (constats citant d'anciens chemins) | 4 fichiers | inchangés (contenu métier) ; table de correspondance |
| `AUDIT_GLOBAL_G0.md`, `audit_preuves/pdf_controles.md`, `PLAN_EXECUTION_REFONTE_G0.md` | 4 occurrences | inchangés ; table de correspondance |
| Rapports de `baseline/` et rapports de première édition | nombreux | inchangés : ce sont des instantanés datés |
| Fichiers hors `docs/dossier-technique/` (code applicatif, `CLAUDE.md`, `docs/`) | **0 référence trouvée** | rien à faire |
| Dossier `pdf_candidats/` renommé `pdf/` | rapports de `baseline/` (historiques), `consolider_journal.py` (lit l'historique git à l'ancien chemin) | `consolider_journal.py` et `verifier_suivi.py` : nouveau chemin ; rapports historiques inchangés |

## 5. Citations d'anciens chemins dans les PDF définitifs (non modifiables)

Vingt et un éléments de l'ancienne arborescence sont cités par les documents de la révision 2 :

- **Références en ligne du dossier technique** : `restreint/ECARTS_DECISIONS_CODE.md` (citée à de nombreuses reprises), `restreint/annexes/B_matrice_role_action.md`, `couverture/etat_B/` (INVENTAIRE, MODELES, ROUTES), `audit_preuves/` (6 pièces), `outils/inventaire.py`. En option A, **tous restent valides au même chemin**. En option B, `restreint/` change d'adresse : une dizaine de citations deviennent fausses sans correspondance.
- **Sources historiques du registre et du dossier technique** : `00_LISEZ-MOI.md`, `GUIDE_DE_LECTURE.md`, `RAPPORT_CLOTURE_G0.md`, `RAPPORT_QUALIFICATION_FINALE_G0.md`, `SYNTHESE_ECARTS_PAR_CRITICITE.md`, `G0_SOMMAIRE_DETAILLE.md`, `guide-visuel/RAPPORT_GUIDE_VISUEL_G0.md`, `restreint/13_logistique_technique.md`, `restreint/23_configuration_deploiement_exploitation.md`. Ces citations désignent l'ancienne édition comme preuve d'une anomalie : elles gardent leur sens, à condition que le fichier existe dans l'archive.

## 6. Vérifications prévues après archivage

1. `git status` : uniquement des renommages (similarité 100 %) ; `git diff -M --stat` sans modification de contenu ; 268 fichiers avant, 268 après (inventaire comparé par SHA-256).
2. SHA-256 des quatre PDF de référence inchangés ; `python3 outils/verifier_suivi.py` sans écart.
3. Contrôles : C1 (507/507) et C2 rejoués sur l'archive, C4, C13 (aucun fichier applicatif), `lancer_controles_sources.py` (barrière G1), régénération du registre et des annexes identique octet pour octet.
4. Liens relatifs de tous les `.md` de `refonte/`, de l'index des annexes (ouverture hors ligne) et des rapports de contrôles : aucun lien cassé.
5. Les 21 chemins cités par les PDF (§5) : chacun existe au chemin cité (option A) ou dans la table de correspondance (option B).
6. `JOURNAL_INSPECTION_FINAL.csv` : recalculé (`consolider_journal.py`) identique.
7. Recherche de toute occurrence des anciens chemins hors table de correspondance, hors rapports datés.

## 7. Risques

| Risque | Gravité | Parade |
|---|---|---|
| Citations de chemins devenues fausses dans des PDF qu'on ne peut plus reconstruire | moyenne (option B) ; nulle (option A) | option A ; sinon table de correspondance |
| Outils de la révision 2 qui lisent l'ancienne édition (C1, C2, génération) | moyenne | constante d'archive + rejeu des contrôles (§6) |
| **Les PDF de référence affichent encore « PDF candidat de la révision 2 — non validé »** en couverture et en pied de page ; ils ne peuvent plus être reconstruits | moyenne (confusion d'état) | `README_DOSSIER.md`, `INVENTAIRE_LIVRABLES.md` et un fichier d'accompagnement dans le dossier des PDF attestent la validation documentaire du jalon V2 pour ces empreintes ; décision du PO : accepter la mention, ou autoriser plus tard une dernière reconstruction dédiée |
| Cinq PDF de maquette V1 (`refonte/apercus_V1/`) confondus avec les PDF de référence | faible | les archiver ou les laisser, au choix du PO ; ils portent « maquette pilote V1, non validé » |
| Ancien PDF « DIFFUSION GÉNÉRALE » qui continue de circuler | moyenne | archivage dans `archive_G0_initial/pdf/` avec avis ; retrait irréversible sur ordre explicite uniquement |
| Perte de fichiers lors du déplacement | faible | `git mv`, comparaison d'inventaire par SHA-256, rien n'est supprimé |
| Taille du dépôt (≈ 40 Mo d'anciens PDF et captures) | faible | inchangée : l'archivage ne copie rien |

## 8. Décisions demandées au PO

1. Option A (recommandée) ou option B pour `restreint/ECARTS_DECISIONS_CODE.md` et `restreint/annexes/`.
2. Emplacement des PDF : `refonte/pdf/` (recommandé) ou `pdf/` à la racine.
3. Archivage des trois anciens PDF dans `archive_G0_initial/pdf/` : oui ou non ; le retrait irréversible n'est pas proposé.
4. Sort des cinq PDF de maquette V1 : archiver ou laisser.
5. Mention « non validé » des PDF figés : acceptée avec attestation séparée, ou dernière reconstruction ultérieure.

Après votre arbitrage, l'exécution tient en un seul commit de renommages et de mises à jour de chemins, suivi des vérifications du §6. Aucune modification de contenu métier, de schéma, de décision ou de statut.
