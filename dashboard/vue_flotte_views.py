"""Vue flotte agrégée par périmètre (dashboard/web_views.py).

Sous-domaine extrait lors du découpage du fichier (tâche Notion « [ARCH]
Découper dashboard/web_views.py (1063 lignes) par sous-domaine »,
dashboard/web_views.py ayant dépassé 800 lignes) : la vue agrégée du
périmètre du chef connecté (maintenances en retard, tickets correctifs
ouverts par statut, pièces de stock sous seuil).

_agrege_maintenance_ticket_stock est réutilisée telle quelle par
dashboard/dashboards_transverses_views.py::DashboardClasseNavireView, d'où
son maintien ici plutôt qu'un déplacement complet — même import circulaire
volontaire que le reste du découpage (voir dashboard/web_views.py).

Refactor pur : reproduit exactement le comportement d'origine."""
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from django.views.generic import TemplateView

from logistics.models import CorrectiveTicket, STATUTS_TICKET_OUVERTS, StockPiece
from maintenance.models import MaintenanceOccurrence
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, section_id_for_user, sector_id_for_user, ship_id_for_user

from .web_views import _STATUTS_MAINTENANCE_TERMINES

# Champ de périmètre (direct sur Asset/Installation/StockPiece, cf.
# assets/models.py et logistics/models.py) correspondant à chaque niveau
# d'agrégation de la Vue flotte.
_CHAMP_PERIMETRE = {"navire": "ship_id", "secteur": "sector_id", "section": "section_id"}

# Titre affiché en tête de la Vue flotte selon le périmètre effectif de
# l'utilisateur connecté (cf. _perimetre_agregation ci-dessous) — cohérent
# avec le principe "espace personnel" de CLAUDE.md : le libellé doit refléter
# ce que le chef voit réellement, pas un intitulé générique.
_TITRE_PERIMETRE = {
    "flotte": "Vue de la flotte",
    "navire": "Vue de mon unité",
    "secteur": "Vue de mon secteur",
    "section": "Vue de ma section",
}

# Préfixe (avec article accordé) utilisé pour construire la phrase d'intro de
# la Vue flotte quand un nom de périmètre est disponible, ex. "Vue agrégée du
# secteur « Passerelle »." — évite de gérer l'accord masculin/féminin dans le
# template.
_PREFIXE_SOUS_TITRE_PERIMETRE = {
    "navire": "de l'unité",
    "secteur": "du secteur",
    "section": "de la section",
}

# Message affiché quand le rôle donne accès à la Vue flotte mais qu'aucun
# objet du niveau attendu n'est renseigné sur le profil (ex. CHEF_SECTEUR
# sans secteur rattaché) — accord au masculin/féminin selon le niveau.
_MESSAGE_AUCUN_PERIMETRE = {
    "navire": "Aucune unité n'est associée à votre profil : impossible d'afficher la vue flotte.",
    "secteur": "Aucun secteur n'est associé à votre profil : impossible d'afficher la vue flotte.",
    "section": "Aucune section n'est associée à votre profil : impossible d'afficher la vue flotte.",
}


def _perimetre_agregation(user):
    """Détermine le périmètre effectif d'agrégation de la Vue flotte selon le
    rôle de l'utilisateur connecté, plutôt que selon le niveau le plus précis
    de son profil (contrairement à profil.scope / scope_filters_for_user,
    utilisés ailleurs pour filtrer les listes détaillées de l'utilisateur) :
    - MASTER_ADMIN (ou superutilisateur) : flotte entière, tous navires.
    - CHEF_SERVICE et rôles supérieurs (ETAT_MAJOR, COMMANDANT, ADMIN_NAVIRE) :
      navire entier — comportement historique de cette vue, inchangé.
    - CHEF_SECTEUR : borné à son secteur.
    - CHEF_SECTION : borné à sa section (niveau le plus bas admis par
      dispatch()).

    Renvoie un triplet (niveau, id_perimetre, nom_perimetre) où niveau vaut
    "flotte"/"navire"/"secteur"/"section", id_perimetre est l'id de l'objet
    correspondant (ou None si non renseigné sur le profil) et nom_perimetre
    son nom à afficher (ou None)."""
    if is_master_admin(user):
        return "flotte", None, None

    profile = getattr(user, "profile", None)
    if user_role_level(user) >= RoleLevel.CHEF_SERVICE:
        ship = getattr(profile, "ship", None)
        return "navire", ship_id_for_user(user), (ship.name if ship else None)
    if user_role_level(user) == RoleLevel.CHEF_SECTEUR:
        sector = getattr(profile, "sector", None)
        return "secteur", sector_id_for_user(user), (sector.name if sector else None)
    # CHEF_SECTION : niveau le plus bas autorisé par dispatch() ci-dessous.
    section = getattr(profile, "section", None)
    return "section", section_id_for_user(user), (section.name if section else None)


class VueFlotteView(LoginRequiredMixin, TemplateView):
    """Vue agrégée du périmètre du chef connecté — réservée à CHEF_SECTION et
    aux rôles supérieurs.

    Contrairement à TableauDeBordView (espace personnel du marin, principe
    fondamental n°3 de CLAUDE.md), cette vue donne aux chefs une photo
    d'ensemble de leur périmètre : maintenances en retard, tickets correctifs
    ouverts par statut, pièces de stock sous seuil. Aucune donnée nouvelle,
    aucun nouveau système de périmètre : les mêmes requêtes que
    notify_overdue_occurrences, CorrectiveOpenChartView et notify_low_stock
    (notifications/tasks.py, dashboard/views.py), simplement agrégées.

    Un seul écran pour tous les niveaux (décision PO, pour éviter 3 vues
    quasi identiques) : le périmètre effectif (navire / secteur / section /
    flotte entière) est calculé par _perimetre_agregation() selon le rôle de
    l'utilisateur, et le même jeu de requêtes est simplement filtré sur le
    champ de périmètre correspondant (_CHAMP_PERIMETRE).
    """

    template_name = "dashboard/flotte.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied("Réservé aux chefs de section et rôles supérieurs.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        user = self.request.user

        niveau_perimetre, perimetre_id, nom_perimetre = _perimetre_agregation(user)
        flotte_entiere = niveau_perimetre == "flotte"

        contexte["niveau_perimetre"] = niveau_perimetre
        contexte["titre_perimetre"] = _TITRE_PERIMETRE[niveau_perimetre]
        contexte["nom_perimetre"] = nom_perimetre
        contexte["flotte_entiere"] = flotte_entiere
        if flotte_entiere:
            contexte["sous_titre_perimetre"] = "Vue agrégée de la flotte entière (toutes unités confondues)."
        elif nom_perimetre:
            contexte["sous_titre_perimetre"] = (
                f"Vue agrégée {_PREFIXE_SOUS_TITRE_PERIMETRE[niveau_perimetre]} « {nom_perimetre} »."
            )
        else:
            contexte["sous_titre_perimetre"] = "Vue agrégée de votre périmètre."

        if not flotte_entiere and perimetre_id is None:
            # Profil sans objet du niveau attendu renseigné : rien à agréger,
            # message clair plutôt qu'une page vide sans explication.
            contexte["aucun_perimetre"] = True
            contexte["message_aucun_perimetre"] = _MESSAGE_AUCUN_PERIMETRE[niveau_perimetre]
            contexte["maintenances_en_retard"] = 0
            contexte["maintenances_en_retard_pct"] = 0
            contexte["tickets_par_statut"] = []
            contexte["total_tickets_ouverts"] = 0
            contexte["tickets_chart_labels_json"] = json.dumps([])
            contexte["tickets_chart_values_json"] = json.dumps([])
            contexte["pieces_sous_seuil"] = []
            contexte["pieces_sous_seuil_pct"] = 0
            return contexte

        # Une occurrence porte soit sur du matériel mobile (asset), soit sur une
        # installation fixe (installation_maintenance) — jamais les deux à la fois,
        # même logique que MaintenanceOccurrenceViewSet.get_scoped_filters().
        filtre_occurrence = Q()
        filtre_ticket = Q()
        filtre_stock = Q()
        if not flotte_entiere:
            champ = _CHAMP_PERIMETRE[niveau_perimetre]
            filtre_occurrence = Q(**{f"asset__{champ}": perimetre_id}) | Q(
                **{f"installation_maintenance__installation__{champ}": perimetre_id}
            )
            filtre_ticket = Q(**{f"asset__{champ}": perimetre_id}) | Q(**{f"installation__{champ}": perimetre_id})
            filtre_stock = Q(**{champ: perimetre_id})

        contexte.update(_agrege_maintenance_ticket_stock(filtre_occurrence, filtre_ticket, filtre_stock))
        contexte["aucun_perimetre"] = False
        return contexte


def _agrege_maintenance_ticket_stock(filtre_occurrence, filtre_ticket, filtre_stock):
    """Agrège maintenances en retard, tickets correctifs ouverts par statut et
    pièces de stock sous seuil pour un périmètre donné (filtres Q déjà
    construits par l'appelant), sous forme de dict de contexte prêt à
    fusionner dans un template.

    Factorisé depuis VueFlotteView.get_context_data (comportement strictement
    inchangé, cf. dashboard/tests/test_vue_flotte.py) pour être réutilisé tel
    quel par DashboardClasseNavireView (dashboard/dashboards_transverses_views.py)
    — un dashboard « classe de navire » n'est qu'une Vue flotte dont le
    périmètre couvre plusieurs navires (ceux de la classe) au lieu d'un seul,
    la même agrégation s'applique donc à l'identique."""
    contexte = {}
    contexte["maintenances_en_retard"] = MaintenanceOccurrence.objects.filter(
        filtre_occurrence, status="OVERDUE"
    ).count()
    # Jauge (principe n°5 CLAUDE.md) : proportion de retard parmi les
    # maintenances encore actives (mêmes statuts exclus que TableauDeBordView),
    # plus parlante pour un chef qu'un chiffre brut sans dénominateur.
    total_maintenances_actives = MaintenanceOccurrence.objects.filter(
        filtre_occurrence
    ).exclude(status__in=_STATUTS_MAINTENANCE_TERMINES).count()
    contexte["maintenances_en_retard_pct"] = (
        round(contexte["maintenances_en_retard"] / total_maintenances_actives * 100)
        if total_maintenances_actives else 0
    )

    # Une seule requête agrégée par statut, même pattern que
    # dashboard/views.py::CorrectiveOpenChartView.
    totaux_par_statut = dict(
        CorrectiveTicket.objects.filter(filtre_ticket, status__in=STATUTS_TICKET_OUVERTS)
        .values("status")
        .annotate(total=Count("id"))
        .values_list("status", "total")
    )
    libelles_statut = dict(CorrectiveTicket.STATUS)
    tickets_par_statut = [
        {
            "statut": statut,
            "libelle": libelles_statut.get(statut, statut),
            "total": totaux_par_statut.get(statut, 0),
        }
        for statut in STATUTS_TICKET_OUVERTS
    ]

    contexte["tickets_par_statut"] = tickets_par_statut
    contexte["total_tickets_ouverts"] = sum(t["total"] for t in tickets_par_statut)
    # Données du doughnut Chart.js (principe n°5 CLAUDE.md) : même composant que
    # dashboard/index.html (chartCorrective), mais alimenté directement par le
    # contexte déjà scopé au navire plutôt qu'un appel à l'API globale
    # /api/dashboard/corrective_open/ (non scopée navire, incohérente ici).
    contexte["tickets_chart_labels_json"] = json.dumps(
        [t["libelle"] for t in tickets_par_statut]
    )
    contexte["tickets_chart_values_json"] = json.dumps(
        [t["total"] for t in tickets_par_statut]
    )

    contexte["pieces_sous_seuil"] = list(
        StockPiece.objects.filter(filtre_stock, quantite__lt=F("quantite_minimale"))
        .select_related("ship", "service", "sector", "section")
        .order_by("reference")
    )
    # Jauge : proportion des pièces de stock sous seuil parmi l'ensemble du
    # périmètre, même logique que la jauge des maintenances en retard ci-dessus.
    total_pieces = StockPiece.objects.filter(filtre_stock).count()
    contexte["pieces_sous_seuil_pct"] = (
        round(len(contexte["pieces_sous_seuil"]) / total_pieces * 100)
        if total_pieces else 0
    )
    return contexte
