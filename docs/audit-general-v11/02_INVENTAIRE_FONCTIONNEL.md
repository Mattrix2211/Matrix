# Inventaire fonctionnel — version 0

Établi sur le commit `1c37f22` par comptage mécanique du dépôt (aucune interprétation de comportement). **Un module présent ici n'est pas déclaré fonctionnel** : l'état de conformité se lit dans `03_MATRICE_CONFORMITE.md`.

## 1. Paquets applicatifs

« Modèles » = classes définies dans `models*.py`, hors énumérations et classes abstraites. « Tests » = fonctions `def test_` dans des fichiers `test*.py` du paquet ; les tests de `matrix/tests/` couvrent surtout des sujets transverses (permissions, navigation, UX).

| Paquet | Modèles | Migrations | Fichiers de test | Tests | Lignes de code (hors tests et migrations) |
|---|---|---|---|---|---|
| `absences/` | 1 | 1 | 3 | 21 | 385 |
| `accounts/` | 9 | 20 | 14 | 159 | 1403 |
| `annonces/` | 4 | 2 | 4 | 46 | 675 |
| `assets/` | 29 | 45 | 45 | 493 | 8658 |
| `calendar_app/` | 1 | 2 | 17 | 124 | 1488 |
| `dashboard/` | 2 | 1 | 20 | 261 | 2551 |
| `demandes/` | 1 | 1 | 3 | 41 | 635 |
| `documentation/` | 3 | 1 | 1 | 9 | 541 |
| `logistics/` | 8 | 14 | 23 | 228 | 2165 |
| `maintenance/` | 6 | 9 | 25 | 178 | 2996 |
| `matrix/` | 3 | 0 | 61 | 881 | 8284 |
| `notifications/` | 2 | 5 | 21 | 165 | 1504 |
| `org/` | 18 | 17 | 9 | 95 | 1301 |
| `postes/` | 2 | 1 | 1 | 7 | 280 |
| `programme/` | 3 | 1 | 1 | 10 | 443 |
| `quarts/` | 16 | 25 | 40 | 609 | 7434 |
| `reports/` | 0 | 0 | 7 | 49 | 882 |
| `retex/` | 2 | 2 | 1 | 5 | 433 |
| `rondes/` | 4 | 1 | 0 | 0 | 195 |
| `taches/` | 5 | 8 | 5 | 94 | 990 |
| `threads/` | 3 | 3 | 6 | 30 | 315 |
| `training/` | 11 | 15 | 24 | 310 | 4020 |

Total mesuré : 22 paquets. Le comptage de tests par recherche textuelle (≈ 3 700) diffère légèrement du nombre exécuté par Django (3 829, qui compte aussi les tests générés ou hérités).

## 2. Sujets à ne pas oublier (fonctions présentes ou résiduelles hors menu principal)

| Élément | Constat | Preuve |
|---|---|---|
| `rondes/` | Module **retiré** par décision PO du 02/11 ; reste des modèles et migrations ; plus de tests propres au paquet, test de retrait dans `matrix/tests/` | `rondes/` (ls), `matrix/tests/test_module_rondes_retire.py` |
| `assets/scan_views.py`, `assets/web_urls.py` | Références « QR » dans le code alors que les QR codes sont « hors V1 » | grep `QR|qrcode` : à qualifier (audit 08) |
| `postes/`, `programme/`, `demandes/`, `retex/`, `documentation/` | Paquets petits (279 à 635 lignes), peu testés (7 à 41 tests) | tableau §1 |
| `reports/` | Aucun modèle, 7 fichiers de test, exports | tableau §1 |
| Commandes de gestion (16) | `seed_demo*` (4), `importer_referentiel_batiments`, `initialiser_mode_batiment`, `purger_brouillons`, `analyser_*` (2), `signaler_divergences_feuilles`, `fusionner_formations`, `catalogue_reprise`, `generate_*` (3), `generate_vapid_keys` | `*/management/commands/` |
| Scripts de lancement | `scripts/preparer_instance_test.py`, `setup.bat`, `start.bat`, `create_admin.bat`, `reset_admin.bat`, `docker-compose.yml` | racine |
| Prototypes | `docs/prototypes/quarts/` (vues A et B, captures) | — |
| Gabarits | 193 fichiers HTML sous `matrix/templates` (et gabarits d'apps) | `find` |
| Tests JavaScript | 4 fichiers `*.test.js` dans `matrix/tests/` | `ls matrix/tests` |

## 3. Documentation du dépôt (sources internes)

| Document | Rôle | Statut |
|---|---|---|
| `CLAUDE.md`, `docs/REFERENCE.md` | Règles techniques et référence | Vivants ; `REFERENCE.md` §4 dit « 14 apps » (écart) |
| `docs/UX.md` (589 lignes) | Cahier UX/UI | Vivant |
| `docs/RECETTE.md`, `docs/DEMO.md`, `docs/TESTS_MARINS.md`, `docs/COMPATIBILITE_CHECKLIST.md` | Recette visuelle, démonstration, tests avec marins, PostgreSQL | Recette visuelle déclarative ; la version lue sur 1c37f22 ne cite plus Rondes |
| `docs/recette/` (6 fichiers + registre ANO-001 à 014) | Dossier de recette V1.1 | Source de preuves à rejouer, jamais à croire sur parole |
| `docs/propositions/` (15 fichiers) | Analyses pour arbitrage (droits COMAEQ, mer/quai, notifications par régime…) | Propositions : ne sont pas des décisions sauf mention « validé par le PO » |
| `docs/archive/` | Historique | Jamais une consigne (`CLAUDE.md`) |
| `docs/demo/guide_recette_metier.md` | Guide de recette par profil | — |
