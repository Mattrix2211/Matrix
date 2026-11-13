# Mesure de base — contrôles appliqués à l'ancien dossier (calibrage, non bloquant)

| Contrôle | Bloquants | Avertissements | Information |
|---|---|---|---|
| C3 | 0 | 5 |  |
| C5 | 417 | 0 | 108 pages PDF contrôlées pour la mention |
| C8 | 9 | 19 | [diffusable] 108 pages ; 7 pages < 40 % ; 0 titres orphelins ; 1 légendes en haut ; 0 pages à texte petit ; 0 syntaxes visibles; [restreint] 143 pages ; 11 page |
| C13 | 0 | 0 | 0 fichier(s) hors documentation modifié(s) depuis 637de94; tête distante de main : 6ef16adcfe8e |

## C3
- avertissement diffusable/02_vue_ensemble.md : « 135 modèles » en dur (utiliser {{fait:n_modeles}})
- avertissement diffusable/02_vue_ensemble.md : « 721 routes » en dur (utiliser {{fait:n_routes}})
- avertissement diffusable/02_vue_ensemble.md : « 20 tâches planifiées » en dur (utiliser {{fait:n_taches_planifiees}})
- avertissement diffusable/02_vue_ensemble.md : « 18 commandes de gestion » en dur (utiliser {{fait:n_commandes}})
- avertissement diffusable/01_vision.md : « 14 modules activables » en dur (utiliser {{fait:n_modules_activables}})

## C5
- **bloquant** diffusable/05_comptes_roles_autorisations.md : motif « chemin_de_code » : outils/generer_exemples_droits.py
- **bloquant** diffusable/05_comptes_roles_autorisations.md : motif « chemin_de_code » : accounts/tests/test_matrice_droits.py
- **bloquant** diffusable/12_maintenance_anomalies_tickets.md : motif « chemin_de_code » : notifications/tasks.py
- **bloquant** diffusable/08_quarts_services_feuille.md : motif « chemin_de_code » : quarts/models.py
- **bloquant** diffusable/08_quarts_services_feuille.md : motif « chemin_de_code » : quarts/echanges.py
- **bloquant** diffusable/08_quarts_services_feuille.md : motif « chemin_de_code » : quarts/activation.py
- **bloquant** diffusable/08_quarts_services_feuille.md : motif « chemin_de_code » : quarts/mouvements.py
- **bloquant** diffusable/08_quarts_services_feuille.md : motif « chemin_de_code » : quarts/remplacement.py
- **bloquant** diffusable/08_quarts_services_feuille.md : motif « chemin_de_code » : quarts/rectificatif.py
- **bloquant** diffusable/08_quarts_services_feuille.md : motif « chemin_de_code » : quarts/services.py
- **bloquant** diffusable/06_accueil_pilotage.md : motif « chemin_de_code » : dashboard/aujourdhui.py
- **bloquant** diffusable/06_accueil_pilotage.md : motif « chemin_de_code » : dashboard/aujourdhui_terre.py
- **bloquant** diffusable/06_accueil_pilotage.md : motif « chemin_de_code » : dashboard/comanav.py
- **bloquant** diffusable/06_accueil_pilotage.md : motif « chemin_de_code » : dashboard/passation.py
- **bloquant** diffusable/06_accueil_pilotage.md : motif « chemin_de_code » : dashboard/indicateurs.py
- **bloquant** diffusable/06_accueil_pilotage.md : motif « chemin_de_code » : dashboard/web_views.py
- **bloquant** diffusable/16_preparation_appareillage.md : motif « chemin_de_code » : dashboard/models.py
- **bloquant** diffusable/16_preparation_appareillage.md : motif « chemin_de_code » : dashboard/web_views.py
- **bloquant** diffusable/04_organisation.md : motif « chemin_de_code » : org/archivage.py
- **bloquant** diffusable/04_organisation.md : motif « chemin_de_code » : org/tests/test_archivage.py
- **bloquant** diffusable/04_organisation.md : motif « chemin_de_code » : org/tests/test_suppression_unites.py
- **bloquant** diffusable/09_communication.md : motif « chemin_de_code » : matrix/core/recherche.py
- **bloquant** diffusable/10_taches_demandes_programme_postes.md : motif « chemin_de_code » : taches/models.py
- **bloquant** diffusable/10_taches_demandes_programme_postes.md : motif « chemin_de_code » : taches/services.py
- **bloquant** diffusable/10_taches_demandes_programme_postes.md : motif « chemin_de_code » : demandes/models.py
- **bloquant** diffusable/10_taches_demandes_programme_postes.md : motif « chemin_de_code » : demandes/services.py
- **bloquant** diffusable/10_taches_demandes_programme_postes.md : motif « chemin_de_code » : programme/models.py
- **bloquant** diffusable/10_taches_demandes_programme_postes.md : motif « chemin_de_code » : programme/services.py
- **bloquant** diffusable/10_taches_demandes_programme_postes.md : motif « chemin_de_code » : postes/models.py
- **bloquant** diffusable/10_taches_demandes_programme_postes.md : motif « chemin_de_code » : postes/services.py
- **bloquant** diffusable/13_logistique.md : motif « chemin_de_code » : logistics/models.py
- **bloquant** diffusable/13_logistique.md : motif « chemin_de_code » : logistics/stock.py
- **bloquant** diffusable/13_logistique.md : motif « chemin_de_code » : logistics/web_views.py
- **bloquant** diffusable/13_logistique.md : motif « chemin_de_code » : notifications/tasks.py
- **bloquant** diffusable/01_vision.md : motif « chemin_de_code » : Chart.js
- **bloquant** diffusable/17_ergonomie_navigation.md : motif « chemin_de_code » : matrix/core/navigation.py
- **bloquant** diffusable/17_ergonomie_navigation.md : motif « chemin_de_code » : accounts/preferences.py
- **bloquant** diffusable/17_ergonomie_navigation.md : motif « chemin_de_code » : matrix/core/inactivite.py
- **bloquant** diffusable/17_ergonomie_navigation.md : motif « chemin_de_code » : matrix/core/brouillons.py
- **bloquant** PDF p.4 : motif « chemin_de_code » : Chart.js
- **bloquant** PDF p.20 : motif « chemin_de_code » : org/archivage.py
- **bloquant** PDF p.20 : motif « chemin_de_code » : org/tests/test_archivage.py
- **bloquant** PDF p.20 : motif « chemin_de_code » : org/tests/test_suppression_unites.py
- **bloquant** PDF p.24 : motif « chemin_de_code » : outils/generer_exemples_droits.py
- **bloquant** PDF p.30 : motif « chemin_de_code » : accounts/tests/test_matrice_droits.py
- **bloquant** PDF p.34 : motif « chemin_de_code » : dashboard/aujourdhui.py
- **bloquant** PDF p.34 : motif « chemin_de_code » : dashboard/aujourdhui_terre.py
- **bloquant** PDF p.34 : motif « chemin_de_code » : dashboard/comanav.py
- **bloquant** PDF p.34 : motif « chemin_de_code » : dashboard/passation.py
- **bloquant** PDF p.34 : motif « chemin_de_code » : dashboard/indicateurs.py
- **bloquant** PDF p.34 : motif « chemin_de_code » : dashboard/web_views.py
- **bloquant** PDF p.46 : motif « chemin_de_code » : quarts/models.py
- **bloquant** PDF p.46 : motif « chemin_de_code » : quarts/echanges.py
- **bloquant** PDF p.46 : motif « chemin_de_code » : quarts/activation.py
- **bloquant** PDF p.46 : motif « chemin_de_code » : quarts/mouvements.py
- **bloquant** PDF p.46 : motif « chemin_de_code » : quarts/remplacement.py
- **bloquant** PDF p.46 : motif « chemin_de_code » : quarts/rectificatif.py
- **bloquant** PDF p.46 : motif « chemin_de_code » : quarts/services.py
- **bloquant** PDF p.50 : motif « chemin_de_code » : matrix/core/recherche.py
- **bloquant** PDF p.55 : motif « chemin_de_code » : taches/models.py
- **bloquant** PDF p.55 : motif « chemin_de_code » : taches/services.py
- **bloquant** PDF p.55 : motif « chemin_de_code » : demandes/models.py
- **bloquant** PDF p.55 : motif « chemin_de_code » : demandes/services.py
- **bloquant** PDF p.55 : motif « chemin_de_code » : programme/models.py
- **bloquant** PDF p.55 : motif « chemin_de_code » : programme/services.py
- **bloquant** PDF p.55 : motif « chemin_de_code » : postes/models.py
- **bloquant** PDF p.55 : motif « chemin_de_code » : postes/services.py
- **bloquant** PDF p.68 : motif « chemin_de_code » : notifications/tasks.py
- **bloquant** PDF p.72 : motif « chemin_de_code » : logistics/models.py
- **bloquant** PDF p.72 : motif « chemin_de_code » : logistics/stock.py
- **bloquant** PDF p.72 : motif « chemin_de_code » : logistics/web_views.py
- **bloquant** PDF p.72 : motif « chemin_de_code » : notifications/tasks.py
- **bloquant** PDF p.87 : motif « chemin_de_code » : dashboard/models.py
- **bloquant** PDF p.87 : motif « chemin_de_code » : dashboard/web_views.py
- **bloquant** PDF p.93 : motif « chemin_de_code » : matrix/core/navigation.py
- **bloquant** PDF p.93 : motif « chemin_de_code » : accounts/preferences.py
- **bloquant** PDF p.93 : motif « chemin_de_code » : matrix/core/inactivite.py
- **bloquant** PDF p.93 : motif « chemin_de_code » : matrix/core/brouillons.py
- **bloquant** PDF p.107 : motif « chemin_de_code » : outils/generer_annexes_e4.py
- **bloquant** diffusable/26_historique_versions_lots.md : motif « branche_interne » : claude/l03-suppression-sure-v11
- … 337 autre(s) bloquant(s)

## C8
- **bloquant** [diffusable] p.100 légende en haut de page, à vérifier : Schéma S40 — De la V1 à l'état B.
Date 
- **bloquant** [restreint] p.5 légende en haut de page, à vérifier : Schéma S10 — Organisation et comptes (ex
- **bloquant** [restreint] p.37 syntaxe visible : pipe parasite
- **bloquant** [restreint] p.79 syntaxe visible : séparateur Markdown
- **bloquant** [restreint] p.79 syntaxe visible : pipe parasite
- **bloquant** [restreint] p.130 syntaxe visible : **
- **bloquant** [restreint] p.131 syntaxe visible : **
- **bloquant** [restreint] p.134 syntaxe visible : accent grave
- **bloquant** [restreint] p.135 syntaxe visible : **
- avertissement [diffusable] p.5 remplie à 38 % (< 40 %)
- avertissement [diffusable] p.6 remplie à 34 % (< 40 %)
- avertissement [diffusable] p.14 remplie à 15 % (< 40 %)
- avertissement [diffusable] p.20 remplie à 31 % (< 40 %)
- avertissement [diffusable] p.82 remplie à 20 % (< 40 %)
- avertissement [diffusable] p.93 remplie à 23 % (< 40 %)
- avertissement [diffusable] p.106 remplie à 13 % (< 40 %)
- avertissement [restreint] p.8 remplie à 27 % (< 40 %)
- avertissement [restreint] p.18 remplie à 17 % (< 40 %)
- avertissement [restreint] p.24 remplie à 23 % (< 40 %)
- avertissement [restreint] p.39 remplie à 14 % (< 40 %)
- avertissement [restreint] p.41 remplie à 14 % (< 40 %)
- avertissement [restreint] p.45 remplie à 14 % (< 40 %)
- avertissement [restreint] p.57 remplie à 30 % (< 40 %)
- avertissement [restreint] p.61 remplie à 21 % (< 40 %)
- avertissement [restreint] p.85 remplie à 21 % (< 40 %)
- avertissement [restreint] p.113 remplie à 30 % (< 40 %)
- avertissement [restreint] p.119 remplie à 27 % (< 40 %)
- avertissement [restreint] p.4 texte petit : 26 % < 7 pt
