# Preuves PDF — contrôles automatiques et inspections

Date : 12/11/2026. PDF : `pdf/Matrix_Dossier_technique_G0_DIFFUSABLE.pdf` (108 p.), `..._RESTREINT.pdf` (143 p., 55 en paysage), `guide-visuel/pdf/Matrix_Guide_visuel_G0.pdf` (39 p.). Outils : pypdfium2, Pillow, rendu Chromium.

## 1. Légendes séparées de leur figure (détection : légende dans les 20 % supérieurs de la page)
| PDF | Page | Schéma | Constat |
|---|---|---|---|
| Restreint | 5 | S10 | L'image est en bas de la page 4, sa légende « Schéma S10 — Organisation et comptes (extrait) » en haut de la page 5 |
| Diffusable | 100 | S40 | Même défaut (non regardé à l'œil : détection automatique seule) |

## 2. Pages peu remplies (encre < 6 % de la zone utile)
- Diffusable : 14, 82, 93, 106 (une ligne de tableau ou 4 à 6 lignes de « Limites » / « Sources »).
- Restreint : 18, 24, 61, 85 et **39, 41, 45 (≤ 5 lignes)**.
- Constat visuel à 62–70 dpi sur 11 de ces pages. La page 14 du diffusable ne porte qu'**une ligne de tableau** et les sources.

## 3. Références techniques dans le PDF « diffusable »
Extraction du texte : 39 chemins de fichiers `.py` sur 12 pages (20, 24, 30, 34, 46, 50, 55, 68, 72, 87, 93, 107), 8 noms de branches `claude/…` sur 7 pages (1, 3, 11, 12, 14, 99, 102), 9 chemins `docs/…`, 6 mentions Redis/Celery/PostgreSQL. Absence constatée : variables d'environnement, adresses, `manage.py`, `.claude`. La page de couverture annonce pourtant « Aucune référence de code ». Le contrôle de séparation de l'ensemble 4 ne vise que « fichier:ligne ».

## 4. Lisibilité des schémas (largeur utile calculée, voir `schemas_lisibilite.csv`)
Corps de police minimal rendu à la largeur de page portrait (510 pt) : S10 **5,0 pt** ; S04, S13, S28 5,8 pt ; S09 6,0 pt ; S15 6,0 pt ; S01 et S21 6,2 pt ; S11 7,2 pt. Inspection visuelle à 90–110 dpi : S10 (p. 4 restreint), S09 (p. 50), S11 (p. 67), S13 (diffusable p. 31) — S10 est illisible, S09 et S13 lisibles mais denses, S11 correct.

## 5. Symbole ⚪
Rendu comme un petit cercle « ◦ » dans les deux PDF du dossier (🟢🔵🟣 sont des pastilles colorées). Corrigé seulement dans le guide visuel.

## 6. Pages réellement inspectées pendant cet audit
Diffusable : 1, 2, 14, 21, 22, 31, 82, 93, 106. Restreint : 4, 5, 18, 24, 39, 41, 45, 50, 61, 67, 85, 88, 89. Guide visuel : les 39 pages à ~90 dpi (pages 3, 8, 18, 19, 36, 37, 39 revues après la dernière régénération, les autres dans la pagination précédente). **Les ~190 autres pages des deux PDF du dossier n'ont pas été revues individuellement dans cet audit** (mesures automatiques et inspections des sessions précédentes seulement).
