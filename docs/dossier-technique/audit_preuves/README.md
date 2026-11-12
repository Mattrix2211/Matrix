# Annexes de preuves de l'audit global G0 (phase 1)

> Diffusion restreinte. Date : 12/11/2026. Référence : état B (`6d6d0be`). Rapport : `../AUDIT_GLOBAL_G0.md`.

| Fichier | Contenu | Niveau de preuve |
|---|---|---|
| `captures_audit.csv` | Les 64 captures : profil, adresse, page du guide, verdict (OK, mineur, manque, redondante, doublon) et constat | [V][A] |
| `schemas_lisibilite.csv` | Corps de police minimal et courant de chacun des 42 schémas, rendu à la largeur d'une page portrait et paysage | [A] |
| `pdf_controles.md` | Légendes séparées, pages peu remplies, références techniques du PDF diffusable, pages réellement inspectées | [A][V] |
| `navigateur_droits.md` | Codes HTTP par profil et par adresse, A20 et A14 dans le navigateur, tests relancés | [N][T] |
| `tests_verification/` | Les trois fichiers de test A14, A20, A25 (29 tests, OK le 12/11/2026) : à copier dans `dashboard/tests/` et `maintenance/tests/` d'une copie isolée de l'état B | [T] |
| `scripts_navigateur/` | Scripts Playwright des essais de droits (comptes fictifs, instance isolée) | [N] |

## Rejouer les tests
Dans une copie isolée de `6d6d0be` (jamais sur des données réelles) :
```bash
cp audit_preuves/tests_verification/verif_g0_a14.py <copie>/dashboard/tests/
cp audit_preuves/tests_verification/verif_g0_a20.py audit_preuves/tests_verification/verif_g0_a25.py <copie>/maintenance/tests/
python manage.py test dashboard.tests.verif_g0_a14 maintenance.tests.verif_g0_a20 maintenance.tests.verif_g0_a25
```
(l'environnement de la démonstration isolée est celui de `scripts/preparer_instance_test.py` : base SQLite séparée, DEBUG actif, aucune connexion à Redis).

Les scripts du dossier `scripts_navigateur/` supposent une instance de démonstration lancée sur `127.0.0.1:8800` et le mot de passe de démonstration dans la variable `PW` ; ce mot de passe n'est jamais versionné.

## Ajouts de la phase 2
| Fichier | Contenu |
|---|---|
| `decisions_dec_verification.csv` | Les 125 décisions du dossier V1.2 (branche `claude/eager-hopper-2cbcqh`) : statut à la source et chapitres qui les citent |
| `pages_remplissage.csv` | Taux de remplissage vertical et nombre de mots de **chaque** page des deux PDF du dossier |
| `schemas_verdicts.csv` | Verdict visuel et utilité des 42 schémas |
| `a14_navigateur_chef_section.png` | A14 : page de passation vue par un chef de section de l'équipage sortant |
| `appareillage_session_ouverte.png` | Session d'appareillage ouverte (10 points, 0/10) |
| `scripts_navigateur/rel2.js`, `rel3.js`, `priv2.js`, `app.js`, `syn.js`, `assign.js` | Relève A→B et passation, tâche personnelle, appareillage, synthèse du chef, assignation |
