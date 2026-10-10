"""Interface web du module Quarts/services (Phase 2 — Vie quotidienne).

Périmètre de ce module (cf. tâche Notion « Quarts/services ») : un chef de
liste désigné crée une liste (Quart ou ServiceGarde) sur une période, y
affecte des marins sur des créneaux, et la publie. S'y ajoutent les échanges
de tour entre marins, la feuille de service quotidienne (en-tête + personnel, circuit de visa).

L'affichage des créneaux assignés dans le calendrier personnel du marin (cf.
tâche Notion « Quarts/services : afficher les créneaux assignés dans le
calendrier personnel du marin ») est désormais fait — mais PAS ici : il vit
dans calendar_app (calendar_app/evenements_sources.py::_creneaux_quart_assignes/
_creneaux_garde_assignes, calendar_events, ical_views.py), qui agrège déjà
toutes les sources d'événements du calendrier central, pour ne pas dupliquer
cette mécanique. La visibilité en lecture ci-dessous reste volontairement
limitée à une simple fiche détail d'une liste précise (_peut_lire_liste),
consultée depuis le lien "Voir la fiche complète" du popover calendrier.

Fichier découpé par sous-domaine fonctionnel (tâche Notion « [ARCH] Découper
quarts/web_views.py (1086 lignes) par sous-domaine »), suivant le même
principe que le découpage déjà en place sur assets/web_views.py,
training/web_views.py et dashboard/web_views.py : un module par sous-domaine,
regroupés ici :
- quarts/listes_views.py — listes de quarts/gardes (création, créneaux,
  affectation, publication) et désignation des chefs de liste
- quarts/echanges_views.py — échanges de tours de service entre marins
- quarts/feuille_service_views.py — feuille de service quotidienne (en-tête,
  personnel automatique, circuit de visa secteur/service/COMAEQ)

Ce fichier ne contient plus que ce qui est RÉELLEMENT partagé entre plusieurs
de ces sous-domaines (_peut_lire_liste, utilisée par listes_views ET
echanges_views). Les classes de vues sont réimportées ci-dessous pour que
`from .web_views import ListeIndexView` (ou `from quarts.web_views import
...`, cf. web_urls.py) continuent de fonctionner sans changement de
comportement. L'import a lieu APRÈS la définition de _peut_lire_liste
ci-dessous, car listes_views et echanges_views la réimportent en retour
(`from .web_views import _peut_lire_liste`) — même import circulaire
volontaire, déjà en place pour dashboard/web_views.py avant ce découpage."""
from django.contrib.auth import get_user_model

from matrix.core.roles import user_role_level

from .models import NIVEAU_LECTURE_GLOBALE_LISTE, marins_du_perimetre

User = get_user_model()


def _peut_lire_liste(user, liste):
    """Lecture d'une liste déjà PUBLIÉE, ouverte à tout marin qui en relève
    (même règle de cascade que les marins affectables sur un créneau, cf.
    marins_du_perimetre) — une liste encore en BROUILLON reste visible
    uniquement à ses chefs de liste gérants (cf. peut_gerer_liste)."""
    if user_role_level(user) >= NIVEAU_LECTURE_GLOBALE_LISTE:
        # Commandant et commandant en second : toutes les listes de leur navire
        # (leur équipage), y compris en brouillon ou proposées.
        from .listes_views import _listes_visibles

        return _listes_visibles(type(liste), user).filter(pk=liste.pk).exists()
    if liste.statut != liste.STATUT_PUBLIEE:
        return False
    return User.objects.filter(marins_du_perimetre(liste), pk=user.pk).exists()


# Réimports pour compatibilité (voir docstring de ce fichier ci-dessus) :
# placés après _peut_lire_liste ci-dessus, car listes_views et echanges_views
# la réimportent depuis CE module.
from .listes_views import (  # noqa: E402,F401
    _listes_visibles,
    ChefDeListeReglagesView,
    CreerListeView,
    ListeIndexView,
    QuartDetailView,
    ServiceGardeDetailView,
)
from .echanges_views import (  # noqa: E402,F401
    EchangeActionView,
    EchangesIndexView,
    ProposerEchangeView,
)
from .alertes_views import OrganisationAlerteView  # noqa: E402,F401
from .feuille_service_views import (  # noqa: E402,F401
    FeuilleServiceDetailView,
    FeuilleServiceIndexView,
    FeuilleServiceReglagesView,
)
