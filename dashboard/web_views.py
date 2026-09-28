"""Fonctions et constante partagées par les vues web de l'app dashboard, et
point d'entrée unique pour les URLs (dashboard/web_urls.py), matrix/urls.py
et logistics/tests/test_ticket_installation.py.

Fichier découpé par sous-domaine fonctionnel (tâche Notion « [ARCH]
Découper dashboard/web_views.py (1063 lignes) par sous-domaine »), suivant le
même principe que le découpage déjà en place sur assets/web_views.py et
training/web_views.py : un module par sous-domaine, regroupés ici :
- dashboard/tableau_bord_views.py — tableau de bord personnel du marin
  (TableauDeBordView), principe fondamental n°3 de CLAUDE.md
- dashboard/vue_flotte_views.py — vue agrégée par périmètre (Vue flotte),
  réservée à CHEF_SECTION et aux rôles supérieurs
- dashboard/pret_appareillage_views.py — sessions « Prêt à appareillage »
  (ouverture, pointage, signature, historique)
- dashboard/dashboards_transverses_views.py — dashboards par spécialité et
  par classe de navire (accounts.ResponsableSpecialite,
  org.ResponsableClasseNavire)

Ce fichier ne contient plus que la constante RÉELLEMENT partagée entre
plusieurs de ces sous-domaines (statuts de maintenance considérés comme
terminés, utilisée par les quatre sous-domaines ci-dessus) — les constantes
propres à un seul sous-domaine ont été déplacées avec lui. Les classes de
vues sont réimportées ci-dessous pour que `from .web_views import
TableauDeBordView` (ou `from dashboard.web_views import ...`, cf.
web_urls.py, matrix/urls.py et logistics/tests/test_ticket_installation.py)
continuent de fonctionner sans changement de comportement. L'import a lieu
APRÈS la définition de la constante ci-dessous, car les quatre modules la
réimportent en retour (`from .web_views import
_STATUTS_MAINTENANCE_TERMINES`) — même import circulaire volontaire, déjà en
place pour assets/web_views.py avant ce découpage."""

# Occurrences considérées comme terminées : on ne les affiche pas dans "Mes
# maintenances" ni dans les dashboards agrégés, seules celles qui restent à
# faire intéressent le marin ou le chef. Partagée par les quatre sous-domaines
# ci-dessus (TableauDeBordView, VueFlotteView, Prêt à appareillage, dashboards
# transverses).
_STATUTS_MAINTENANCE_TERMINES = ["DONE", "CANCELLED"]

# Réimports pour compatibilité (voir docstring de ce fichier ci-dessus) :
# placés après la constante ci-dessus, car les quatre modules la réimportent
# depuis CE module.
from .tableau_bord_views import TableauDeBordView  # noqa: E402,F401
from .vue_flotte_views import VueFlotteView, _agrege_maintenance_ticket_stock  # noqa: E402,F401
from .pret_appareillage_views import (  # noqa: E402,F401
    HistoriqueAppareillageView,
    ItemAppareillageCocherView,
    PretAppareillageView,
    SessionAppareillageDetailView,
    SessionAppareillageOuvrirView,
    SessionAppareillageSignerView,
)
from .dashboards_transverses_views import (  # noqa: E402,F401
    DashboardClasseNavireChoixView,
    DashboardClasseNavireView,
    DashboardSpecialiteChoixView,
    DashboardSpecialiteView,
)
