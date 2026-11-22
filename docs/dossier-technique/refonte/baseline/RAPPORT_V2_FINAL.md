# Rapport de clôture du jalon V2 — Matrix G0, révision 2

Branche `claude/fervent-wright-kl6gtx` · état applicatif B `6d6d0be` · base d'audit `637de94`.
Aucun code applicatif modifié (C13 : différence vide), `main` intact, aucune PR, aucune fusion, aucune diffusion, phase 13 non engagée.

## 1. Défauts traités

| Défaut (construction du commit 636bf6b) | Résultat |
|---|---|
| DT p.36-37 : titre du chapitre 9 coupé | chapitre 9 entier en p.37 |
| DT p.33-34 : encadré « Public » du chapitre 8 coupé | chapitre 8 entier en p.34 |
| DT p.70-71 : encadré « Public » du chapitre 20 coupé | chapitre 20 entier en p.71 |
| RF p.115-116 : encadré « Public » du chapitre 20 coupé | chapitre 20 entier en p.116 |

Gabarit (`gabarits/refonte.css`) : trois règles ajoutées — un titre de chapitre ne se coupe pas (`h1 { break-inside: avoid }`), l'encadré « Public » reste entier et collé à son titre (`break-inside: avoid; break-after: avoid`), un surtitre de partie reste avec son titre. Aucun texte, schéma ni décision modifié.

## 2. Contrôle C8 renforcé

`controles.py` : fonction `coupures_chapitres` (appelée par C8, bloquante, aucun seuil ni contrôle existant modifié). Elle lit les titres de chapitre et les encadrés « Public » dans l'aperçu HTML et vérifie dans le PDF que le titre est entier sur sa page, que l'encadré commence et finit sur la même page que le titre, et que le titre n'est pas séparé de son encadré.

Preuves : (1) sur les PDF du commit 636bf6b le contrôle signale exactement les quatre défauts (RF p.115 ; DT p.33, 36, 70) et rien d'autre ; (2) banc d'essai `outils/test_coupures.py` : 60 chapitres placés à toutes les hauteurs de page, 0 coupure avec le gabarit actuel, 8 détectées sans les règles ; (3) constructions temporaires avant la reconstruction définitive (RF, DT) : 0 coupure.

## 3. Livrables

| Document | Pages | Octets | SHA-256 |
|---|---|---|---|
| Guide utilisateur | 86 | 19 807 858 | `966983dc5aa7ee23e644747f303b98ae37526b4641143ca1f400ed254242f0a2` (inchangé) |
| Référentiel fonctionnel | 138 | 6 563 632 | `d1bd6be859883909ee2b7e42ce5ae6978faada1c1ea5c2d8f1dcd9757027e41c` |
| Dossier technique | 96 | 5 269 593 | `52da02728443b6b43cac92bcb44a912338378cca5a5bcf7fc59a652c4158d22c` |
| Registre | 52 | 1 813 119 | `45bc78edbb5629fd5a4fbe3ded8b1e37adc0047a2249927aff046a014a437caf` (inchangé) |

Le RF passe de 137 à 138 pages : le chapitre 20 commence en p.116 au lieu d'être coupé. Les pages 116 à 138 sont décalées d'une page (sommaire p.7-8 et index des schémas mis à jour par la construction).

Reconstructions réelles (jamais remises à zéro) : GU 5, **RF 9**, **DT 5**, RE 3. Le budget de deux reconstructions reste dépassé. Les constructions temporaires de pré-vérification et de reproductibilité (C12, pixel pour pixel identiques aux livrables) ne sont pas comptées.

## 4. Résultats des contrôles (après reconstruction)

- **C8 renforcé** : 0 bloquant sur les quatre PDF ; 0 titre orphelin, 0 légende en haut de page, 0 page à texte petit, 0 syntaxe visible, **0 titre ou encadré « Public » coupé**. Pages remplies à moins de 40 % (avertissements connus) : GU p.6, 59, 71, 80, 86 ; RF p.8, 16, 131, 138 ; DT p.7, 9, 12, 56, 75 ; RE p.43.
- C1 507/507 ; C2, C3, C5, C6 (sommaires 37, 39, 38 entrées, 0 écart), C7, C9 (72 captures), C11 (35 actions ; 125 décisions sur 125), C13, C14 : 0 bloquant. C4 : 0 erreur de référence de code. C12 : reconstruction identique page par page.
- Signets : RF 321, DT 206, tous pointent sur la page de leur titre. Relations des schémas S02, S14, S22, S27, S38 : 0 écart.
- Non-régression GU et RE : fichiers identiques bit à bit (SHA-256 ci-dessus).

## 5. Inspection

Voir `pdf_candidats/JOURNAL_INSPECTION_V5.csv`. RF : 116 pages en identité pixel avec une page déjà inspectée, 22 relues visuellement, 5 schémas relus à 140 ppp. DT : 87 pages en identité pixel, 9 relues, 2 schémas denses relus à 140 ppp. Aucune nouvelle anomalie de pagination.

## 6. Réserves connues (inchangées)

Pages peu remplies listées ci-dessus ; schémas S09, S10b, S24, S28b, S40 non repris dans les documents.

Je m'arrête ici, en attente de votre décision sur la validation définitive de V2 et le basculement documentaire.
