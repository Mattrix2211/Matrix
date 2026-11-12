# Preuves navigateur — droits d'accès par profil (instance de démonstration isolée, état B)

Date : 12/11/2026. Méthode : connexion Playwright/Chromium aux comptes fictifs, ouverture directe de chaque adresse, relevé du code HTTP. Script : `scripts_navigateur/dyn.js`. Instance : copie isolée de `6d6d0be` + données fictives du guide visuel.

| Adresse | equipier_a | chef_section_a | chef_secteur_a | chef_service_a | cdt_a | Attendu par le dossier |
|---|---|---|---|---|---|---|
| `/dashboard/flotte/` (Vue flotte) | 403 | 200 | 200 | 200 | 200 | À partir de chef de section (ch. 6 §6.5) ✔ |
| `/dashboard/comanav/` | 403 | 403 | 403 | 403 | 200 | COMANAV désigné, commandement (ch. 6 §6.5) ✔ (COMANAV désigné non essayé) |
| `/assets/plan/` (configurer le plan) | 403 | 403 | 403 | 200 | 200 | Seuil `plan_navire_configuration` = chef de service ✔ |
| `/parametre/?tab=modules` | 403 | 403 | 403 | 403 | 200 | Seuil `module_gestion` = commandant en second ✔ |
| `/parametre/?tab=seuils` | 403 | 403 | 403 | 403 | 403 | Administrateur d'unité ✔ (non essayé avec ce profil) |
| `/users/` | 403 | 403 | 403 | 403 | 200 | Commandant en second et au-dessus (ch. 2 §2.2) ✔ |
| `/documentation/nouveau/` | 404 | 200 | 200 | 200 | 200 | Rédaction : chef de section (`documentation_redaction`) ✔ (l’équipier reçoit 404 et non 403 : page masquée) |
| `/maintenance/occurrences/4/execute/` (non assignée) | **403** | 200 | 200 | 200 | 200 | Exécuter une maintenance qui n'est pas la sienne : chef de section (`maintenance_occurrence_gestion_tiers`) ✔ côté serveur |
| `/maintenance/gestion/occurrences/` (liste) | boutons « Exécuter » affichés sur **toutes** les lignes | — | — | — | — | Le chapitre 5 dit : « L'écran peut masquer un bouton » : ici il ne le masque pas (AUD-007) |

## A20 dans le navigateur (occurrence 6, « En validation »)

| Profil | Boutons d'action de la fiche |
|---|---|
| equipier_a (assigné) | aucun bouton d'enregistrement (seul « Tout conforme ») |
| chef_section_a | idem |
| chef_secteur_a | « **Enregistrer la correction** » |

Conforme au chapitre 12 §12.4 (correction réservée au chef de secteur ou plus). Script : `scripts_navigateur/a20.js`.

## A14 dans le navigateur

La génération manuelle d'une synthèse de passation par le commandant (`cdt_a`) est **refusée** tant qu'aucune relève validée n'existe : « Aucune relève validée n'a mis l'équipage actuel à bord : rien à passer. » La lecture de la synthèse par un chef de section **n'a donc pas pu être rejouée dans le navigateur** (il faut proposer puis valider une relève A/B). Elle reste établie **par test** (`tests_verification/verif_g0_a14.py`, 8 tests, OK le 12/11/2026). Script : `scripts_navigateur/a14b.js`.

## Tests relancés pendant l'audit

`python manage.py test dashboard.tests.verif_g0_a14 maintenance.tests.verif_g0_a20 maintenance.tests.verif_g0_a25` sur la copie isolée de l'état B : **29 tests, OK** (42,9 s). Ces fichiers n'existent dans aucun dépôt applicatif : ils sont archivés ici.
