# Chapitre 6 (technique) — Accueil, pilotage, passation, rapports : mécanismes

> **Diffusion restreinte.** Complète `diffusable/06_accueil_pilotage.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** comment la page « Aujourd'hui » est construite, les règles de visibilité des vues de pilotage, le fonctionnement de la passation et des bilans, et les points d'entrée.

---

## 6T.1 La page « Aujourd'hui »

Le module `dashboard` ne définit **aucun moteur de calcul propre** : il appelle les services des autres paquets (graphe de dépendances, chapitre 18 : `dashboard` lit 13 paquets).

| Bloc | Fonction | Contenu et règle |
|---|---|---|
| « À faire » | `a_faire` (`dashboard/aujourdhui.py:91`) | Entrées triées par : retard, attente de validation, criticité (5 = la plus critique), échéance. Sources : occurrences de maintenance, tickets correctifs, tâches (`taches_a_suivre`), sessions de formation du jour, propositions et versions de fiche à viser, annonces à lire, demandes à traiter, qualifications à renouveler, réponses attendues. Un **chef** (seuil de supervision et périmètre non vide) voit aussi les maintenances et tickets **non assignés** de son périmètre |
| « Ma journée » | `journee` (`:211`) | Créneaux de quart (listes **publiées**) et de garde (`CreneauServiceGarde.applicables()`) du marin, formations du jour, puis tâches du jour sans heure |
| « Supervision » | `supervision` (`:277`) | `None` sans droit (`peut_superviser`, `:245`) ; sinon, dans le périmètre (`build_scope_q`) et l'équipage (`assignes_equipage_q`) : occurrences en retard et en attente de validation (5 lignes), formations et candidatures à valider, échanges à valider (`echanges_a_valider`), indisponibilités (statuts matériel `OUT_OF_SERVICE`, `FAULTY`, installations critiques en retard). Le champ « peut valider » reprend la règle de la fiche d'exécution (assigné, ou seuil `maintenance_occurrence_gestion_tiers`) |
| Indicateurs | `indicateurs_maintenance` (`dashboard/indicateurs.py:14`) | Compteurs retard, à venir (`A_VENIR_JOURS = 7`, `maintenance/perimetre.py:27`), en validation, tickets ouverts ; chaque chiffre porte l'URL du dossier filtré |
| Niveaux d'urgence | `DANGER`, `ATTENTION`, `NORMAL` | Rang d'urgence : le retard passe avant l'attente de validation |

Vue : `AujourdhuiView` (`dashboard/web_views.py:46`) ; présentation : `dashboard/a_faire_presentation.py`.

**Utilisateur à terre.** `dashboard/aujourdhui_terre.py` : `batiments_suivis` (`:18`) renvoie les bâtiments du périmètre si l'utilisateur n'a **aucun rattachement** à un bâtiment ; `a_faire_terre` (`:29`) liste les validations de maintenance en attente (**sans bouton**, URL vide) et les tickets **bloqués** (bouton « Commenter ») ; `cartes_batiments` (`:61`) compose une carte par bâtiment.

## 6T.2 Visibilité des vues de pilotage

| Vue | Classe / fonction | Règle d'accès |
|---|---|---|
| Vue flotte | `VueFlotteView` (`dashboard/web_views.py:177`) | `user_role_level` ≥ chef de section (`dispatch`) ; périmètre d'agrégation par `_perimetre_agregation` (`:146`) : administrateur général = flotte ; **chef de service et au-dessus** = bâtiment ; chef de secteur = secteur ; chef de section = section |
| Vue COMANAV | `VueComanavView` (`dashboard/comanav.py:221`) | `peut_voir_vue_comanav` (`:38`) : titulaire COMANAV, commandement (commandant, second, administrateur d'unité) ou administrateur général ; `blocs_comanav` (`:204`) borne au bâtiment et **étanche par équipage** |
| Dashboard spécialité | `DashboardSpecialiteView` (`dashboard/web_views.py:935`) | Responsables de spécialité désignés (`accounts.ResponsableSpecialite`) ; lecture seule ; agrège **toute la flotte** |
| Dashboard classe | `DashboardClasseNavireView` (`dashboard/web_views.py:1014`) | Responsables de la classe (`org.ResponsableClasseNavire`) ; agrège les bâtiments de la classe avec les mêmes agrégats que la Vue flotte |
| Prêt à appareiller | `PretAppareillageView` (`dashboard/web_views.py:531`) | Chapitre 16 |

`peut_voir_vue_flotte` (`dashboard/templatetags/dashboard_extras.py:13`) pilote l'affichage de l'entrée de menu ; le serveur revérifie.

## 6T.3 La passation

- `passation_activee` (`dashboard/passation.py:40`) : activée par défaut ; l'administrateur général peut la désactiver pour la flotte (`org.ParametresPassation`).
- `generer_passation` (`dashboard/passation.py:254`) : appelée à l'**application d'une relève** (`matrix/core/equipage.py`, `_appliquer`) ; fige un instantané JSON du bâtiment (`contenu_passation`, `dashboard/passation.py:220` : vue COMANAV, qualifications visibles, annonces, listes de service) ; **aucune étanchéité par équipage** dans le contenu (l'équipage montant lit tout). La relève reste appliquée même si la génération échoue (trace `passation_echec`) ; `generer_passation_manuelle` offre un bouton au commandement.
- `peut_generer_passation` (`dashboard/passation.py:45`) : commandement du bâtiment ou administrateur général.
- `syntheses_visibles` (`dashboard/passation.py:53`) : administrateur général = toutes ; sinon, synthèses du **bâtiment** de l'utilisateur ; au niveau commandant en second ou plus : toutes celles du bâtiment ; sinon, **s'il a un équipage et `peut_superviser`** : celles où son équipage est sortant ou montant ; sinon aucune. *(Aucune borne par section : voir A14.)*
- `PassationView` (`dashboard/passation.py:306`) : page imprimable ; `PassationPdfView` : PDF.
- Modèles : `org.SynthesePassation` (1-1 facultatif avec `ReleveEquipage`), `org.ParametresPassation`.

## 6T.4 Les bilans

- `GenererBilanView` (`reports/web_views.py:53`) : refuse sous le niveau chef de section ; périmètre = `profile.scope` (aucun choix) ; sans périmètre : message et retour à l'accueil ; paramètres `format` (`pdf` par défaut, `csv`, `xlsx`) et `date_debut` / `date_fin` pour le mode période ; `PerimetreNonAutorise` → message.
- Générateurs (`reports/services.py`) : `construire_contexte_instantane` (`:145`) et `construire_contexte_periode` (`:393`) ; même contexte rendu en PDF (`html_vers_pdf`, **facultatif** : `pdf_disponible`, `:65`), CSV, XLSX (`generer_bilan_instantane_xlsx`, `:386`). Nom de fichier `bilan_<niveau>_<date>.<ext>`.
- Route : `/rapports/bilan/` (`reports/web_urls.py`).
- Exports génériques des listes : `matrix/core/export.py` (CSV et Excel).

## 6T.5 Routes

`/` (Aujourd'hui), `/dashboard/flotte/`, `/dashboard/comanav/`, `/dashboard/specialite/…`, `/dashboard/classe-navire/…`, `/dashboard/passation/<id>/` et `…/pdf/`, `/dashboard/pret-appareillage/…`, `/rapports/bilan/`. API : `/api/dashboard/` (inventaire généré, `couverture/etat_B/ROUTES.md` : 17 routes pour le paquet `dashboard`).

## 6T.6 Tests

`dashboard/tests/` (261 fonctions de test), `reports/tests/`.

## 6T.7 Limites et éléments non vérifiés

- ⚪ `a_faire` effectue plusieurs requêtes par type d'objet ; aucune mesure de performance n'a été faite.
- ⚪ La borne « un chef de section ne consulte que sa section » pour la passation n'a pas été trouvée (A14).
- ⚪ Le PDF n'a pas été rejoué (bibliothèques natives absentes de l'environnement).
- ⚪ Chaque indicateur de la Vue flotte, de la Vue COMANAV et des dashboards transverses n'est pas détaillé ici.

---

**Sources (état B).** Références en ligne ; `couverture/etat_B/INVENTAIRE.md` (dépendances de `dashboard`) ; `restreint/ECARTS_DECISIONS_CODE.md` (A14).
