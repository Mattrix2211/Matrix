# Comparaison ciblée entre la version de référence (`main`) et la V1.1

Référence : `main` = `6ef16ad` (2026-10-28) ; version auditée : `1c37f22` ; 117 commits d'écart. But : séparer les **défauts préexistants** des **régressions réellement introduites**. Méthode : (1) différences de code sur les fichiers concernés (`git diff --numstat`) ; (2) rejeu des mêmes sondes sur un **worktree de `main`** avec sa propre base de démonstration (`seed_demo` seul : `main` n'a pas les trois autres générateurs) ; (3) matrice de droits comparée cellule par cellule. Aucun fichier de `main` n'a été modifié.

## 1. Résultat d'ensemble

- **Aucune régression de sécurité ou de droits introduite par la V1.1** n'a été trouvée : sur 683 cellules comparables (profil × action) de la matrice des droits des quarts, **501 sont identiques, 182 sont plus restrictives en V1.1, 0 est plus permissive**.
- **La grande majorité des anomalies du registre sont préexistantes** (37 sur 42), identiques à `main` par le code ou par exécution.
- La V1.1 **corrige** deux défauts de `main` (AUD-001, AUD-026) et **atténue** AUD-008 côté données.
- Elle **introduit** : un résidu de Rondes (AUD-007, retrait décidé le 02/11) et une page nouvelle (« mouvements du bâtiment ») dont le lien est affiché à des profils qui la reçoivent en refus (une part de AUD-016).

## 2. Anomalie par anomalie

| Anomalie | `main` | V1.1 | Verdict |
|---|---|---|---|
| AUD-001 création de feuille par tout marin | **confirmé par exécution** : 10 profils sur 11 créent une feuille, dont `equipier_a` | 2 profils (rédacteurs désignés) | **Préexistant, corrigé** |
| AUD-014 visas intermédiaires élargis | `peut_viser_secteur` identique ligne à ligne | identique | Préexistant |
| AUD-015 voies directes sur listes publiées | aucune cellule plus permissive en V1.1 | idem | Préexistant (non aggravé) |
| AUD-019 structure réservée au compte de flotte (écran) / API pour l'administrateur d'unité | **identique** (403 aux mêmes profils, 201 par l'API) ; `matrix/views.py` n'a changé que par le retrait de Rondes | identique | Préexistant |
| AUD-020 suppression d'unité : marins détachés | **identique** (4 marins section → secteur) | identique | Préexistant |
| AUD-021 erreur 500 sur secteur portant du matériel | **identique** (ProtectedError non interceptée) | identique | Préexistant |
| AUD-034 suppression de compte | **identique** (tâches, difficultés, audit) | identique | Préexistant |
| AUD-008 lien d'accueil vers un ticket hors périmètre | lien « ticket » du chef de secteur renvoie 400 ; `dashboard/aujourdhui.py` filtre les tickets assignés comme en V1.1 | 404 avec `seed_demo` seul, absent avec le pipeline complet | Préexistant ; instance atténuée par les données |
| AUD-016 liens refusés | importer (10 comptes), exécuter (10), RETEX nouveau, et `/anomalies/signaler/` en 404 | importer (37), exécuter, mouvements (8), RETEX nouveau | Mixte : préexistant + une page nouvelle |
| AUD-023 message « ticket ouvert » faux pour une installation | `_execute_done.html` et signal **identiques** | identiques | Préexistant |
| AUD-026 brouillon de signalement, route périmée | **404** reproduit (le lien reprend l'adresse enregistrée telle quelle) | 200 : `adresse_de_reprise` + `ROUTES_DE_REPRISE` ajoutés | **Corrigé en V1.1** (explique l'observation initiale du PO) |
| AUD-009, 010, 011, 017, 035 sécurité et déploiement | `settings.py` n'a aucune modification de sécurité entre les deux | idem | Préexistants |
| AUD-018 titre d'onglet unique | `base.html` : `<title>Matrix</title>` | identique | Préexistant |
| AUD-007 résidu Rondes | module complet | routes retirées, modèles conservés | **Introduit** (retrait décidé) |
| Montée de version `main` → V1.1 | — | **21 migrations appliquées sans erreur** sur base peuplée, SQLite (9,6 s) et PostgreSQL 16 ; aucune ligne perdue (seules des permissions et types de contenu s'ajoutent) ; aucune migration manquante ; connexions et accueils fonctionnels | **Aucune régression de données** |

## 3. Limites de la comparaison

- Les 182 cellules « plus restrictives » mêlent un vrai durcissement (création de feuille : 12 profils → 2, mesuré à état égal) et des écarts d'**état des objets de démonstration** entre les deux bases (feuille et gardes dans des états différents) : seul le sens « jamais plus permissif » est une conclusion robuste.
- `main` ne dispose pas du pipeline de démonstration complet ; les sondes dépendantes de données absentes de `main` n'ont pas été rejouées (échanges, tâches bloquées, double équipage dense).
- Une régression de comportement **non couverte par une sonde** (calendrier, maintenance, formations) ne peut pas être exclue ; la suite de 3 829 tests couvre ces zones pour la V1.1 seulement.
