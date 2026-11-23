# Attestation de validation du jalon V2

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle.

## Attestation

Le PO a validé le **22/11/2026**, sur le plan documentaire seulement, le jalon V2 de la refonte documentaire Matrix G0 révision 2 : les quatre PDF ci-dessous sont acceptés comme **versions de référence**, avec les réserves connues et documentées listées plus bas. Le basculement V3 a été exécuté le 23/11/2026 sans modifier aucun de ces PDF.

Cette attestation ne vaut **ni validation fonctionnelle du logiciel Matrix, ni autorisation de diffusion**. Elle ne rend aucun écart ou point à confirmer du registre « décidé » : A1 à A26 et NE-01 à NE-07 restent des écarts documentés, et les propositions 🟣 restent des propositions.

## Documents validés et empreintes SHA-256

| Document | Fichier | Pages | SHA-256 |
|---|---|---|---|
| Guide utilisateur | `Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf` | 86 | `966983dc5aa7ee23e644747f303b98ae37526b4641143ca1f400ed254242f0a2` |
| Référentiel fonctionnel et de gouvernance | `Matrix_G0R2_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf` | 138 | `d1bd6be859883909ee2b7e42ce5ae6978faada1c1ea5c2d8f1dcd9757027e41c` |
| Dossier technique de reprise | `Matrix_G0R2_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf` | 96 | `52da02728443b6b43cac92bcb44a912338378cca5a5bcf7fc59a652c4158d22c` |
| Registre des écarts et décisions | `Matrix_G0R2_5_Registre_ecarts_decisions_PROVISOIRE_RESTREINT.pdf` | 52 | `45bc78edbb5629fd5a4fbe3ded8b1e37adc0047a2249927aff046a014a437caf` |

Total : 372 pages. Les PDF n'ont pas été reconstruits depuis le commit `63e9be2` ; leur empreinte se vérifie avec `sha256sum` ou `python3 refonte/outils/verifier_suivi.py`.

## Mentions « non validé » : caractère historique

Chaque PDF porte, en couverture (« État documentaire : PDF candidat de la révision 2 — non validé ») et en pied de page (« PDF candidat de la révision 2 — non validé »), la mention de son état au moment de sa construction. Ces mentions sont **historiques** : elles ne sont pas modifiées, car modifier un PDF validé exigerait de le reconstruire et en changerait l'empreinte. **Cette attestation fait foi pour l'état de validation documentaire de ces empreintes.** La mention « DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE » reste en vigueur : c'est une précaution documentaire, non une classification.

## Réserves connues et documentées (16 pages)

Pages remplies à moins de 40 % ou réserve de présentation de la V2, justifiées (fin de chapitre court, début de chapitre avant une page de capture), sans défaut ouvert :

| Document | Page | Observation |
|---|---|---|
| Guide utilisateur | 6 | fin de chapitre court (justifié) ; page remplie à 26 % (avertissement C8, réserve connue) |
| Guide utilisateur | 47 | début de chapitre : texte court puis page de capture paysage (disposition justifiée) |
| Guide utilisateur | 59 | début de chapitre (justifié) ; page remplie à 26 % (avertissement C8, réserve connue) |
| Guide utilisateur | 71 | début de chapitre (justifié) ; page remplie à 31 % (avertissement C8, réserve connue) |
| Guide utilisateur | 80 | début de chapitre (justifié) ; page remplie à 18 % (avertissement C8, réserve connue) |
| Guide utilisateur | 86 | dernière page (index) ; page remplie à 36 % (avertissement C8, réserve connue) |
| Référentiel fonctionnel et de gouvernance | 8 | page remplie à 14 % (avertissement C8, réserve connue) |
| Référentiel fonctionnel et de gouvernance | 16 | page remplie à 38 % (avertissement C8, réserve connue) |
| Référentiel fonctionnel et de gouvernance | 131 | page remplie à 9 % (avertissement C8, réserve connue) |
| Référentiel fonctionnel et de gouvernance | 138 | page remplie à 39 % (avertissement C8, réserve connue) |
| Dossier technique de reprise | 7 | page remplie à 5 % (avertissement C8, réserve connue) |
| Dossier technique de reprise | 9 | page remplie à 24 % (avertissement C8, réserve connue) |
| Dossier technique de reprise | 12 | fin de chapitre courte (justifié) ; page remplie à 9 % (avertissement C8, réserve connue) |
| Dossier technique de reprise | 56 | page remplie à 12 % (avertissement C8, réserve connue) |
| Dossier technique de reprise | 75 | page remplie à 30 % (avertissement C8, réserve connue) |
| Registre des écarts et décisions | 43 | fin de fiche (28 %) justifiée ; page remplie à 28 % (avertissement C8, réserve connue) |

Autres réserves : cinq schémas conservés comme fichiers mais non repris dans les documents (S09, S10b, S24, S28b, S40) ; résultats de tests des lots, preuves historiques non rejouées ; aucune recette navigateur réelle (mobile, lecteur d'écran), PostgreSQL ni Windows revendiquée en dehors de ce que les documents indiquent comme rejoué.

## Références

- Rapport final de recette : `../RAPPORT_RECETTE_REFONTE.md` (contrôles C1 à C14, inspection, réserves, compteurs de reconstruction : guide 5, référentiel 9, dossier technique 5, registre 3).
- Journal d'inspection final, une ligne par page : `JOURNAL_INSPECTION_FINAL.csv`.
- Inventaire des livrables : `../INVENTAIRE_LIVRABLES.md`. Compte rendu du basculement : `../baseline/RAPPORT_BASCULEMENT_V3.md`.
