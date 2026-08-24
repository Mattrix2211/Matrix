"""Vue web de la page d'accueil — tableau de bord + espace personnel du marin.

Principe fondamental n°3 (CLAUDE.md) : chaque marin voit SES tâches, SES
formations, SES maintenances assignées, dès la connexion, sans avoir à
chercher. Cette vue construit le contexte de l'accueil pour ça, en plus
des graphiques Chart.js déjà en place (T5) et du bouton "Générer le bilan"
(T10), qui restent inchangés.
"""
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from django.utils import timezone
from django.views.generic import TemplateView

from logistics.models import CorrectiveTicket, STATUTS_TICKET_OUVERTS, StockPiece
from maintenance.models import MaintenanceOccurrence
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, section_id_for_user, sector_id_for_user, ship_id_for_user
from notifications.tasks import JOURS_ALERTE_EXPIRATION_FORMATION
from training.models import TrainingRecord, TrainingSession

# Occurrences considérées comme terminées : on ne les affiche pas dans "Mes
# maintenances", seules celles qui restent à faire intéressent le marin.
_STATUTS_MAINTENANCE_TERMINES = ["DONE", "CANCELLED"]

# Tickets correctifs considérés comme clos : on ne les affiche pas dans "Mes
# tickets", même logique que _STATUTS_MAINTENANCE_TERMINES ci-dessus.
_STATUTS_TICKET_TERMINES = ["CLOSED", "CANCELLED"]

# Classe de badge Bootstrap par statut d'occurrence — surchargée par
# matrix.css pour respecter la palette du design system (--red, --amber...).
_BADGE_STATUT_MAINTENANCE = {
    "OVERDUE": "bg-danger",
    "WAITING_VALIDATION": "bg-warning",
}

# Seuil (en jours) sous lequel une qualification déjà validée est considérée
# "bientôt expirée" plutôt que "à jour" dans la carte "Mes qualifications" :
# aligné sur la plus lointaine échéance de notify_expiring_training
# (notifications/tasks.py), pour que le badge de la carte corresponde à
# l'alerte que le marin a déjà pu recevoir.
_SEUIL_QUALIFICATION_BIENTOT_EXPIREE_JOURS = max(JOURS_ALERTE_EXPIRATION_FORMATION)


def _badge_qualification(record, aujourdhui):
    """Classe de badge + libellé pour une qualification (TrainingRecord),
    même palette que logistics/stock_list.html (badge-conforme/text-bg-warning/
    text-bg-danger) : expirée si la date d'expiration est passée, bientôt
    expirée si elle tombe dans le seuil d'alerte ci-dessus, à jour sinon."""
    if record.expires_at < aujourdhui:
        return "text-bg-danger", "Expirée"
    if record.expires_at <= aujourdhui + timezone.timedelta(days=_SEUIL_QUALIFICATION_BIENTOT_EXPIREE_JOURS):
        return "text-bg-warning", "Bientôt expirée"
    return "badge-conforme", "À jour"


class TableauDeBordView(LoginRequiredMixin, TemplateView):
    """Page d'accueil : graphiques du service + espace personnel du marin connecté."""

    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)

        mes_maintenances = list(
            MaintenanceOccurrence.objects.select_related(
                "asset",
                "installation_maintenance",
                "installation_maintenance__installation",
            )
            .filter(assignees=self.request.user)
            .exclude(status__in=_STATUTS_MAINTENANCE_TERMINES)
            .order_by("scheduled_for")
        )
        for occurrence in mes_maintenances:
            occurrence.badge_classe = _BADGE_STATUT_MAINTENANCE.get(
                occurrence.status, "bg-secondary"
            )

        # Formations où le marin est inscrit par un référent (attendees) OU où
        # il a réservé sa place lui-même en libre-service (reservations, cf.
        # T-FORM réservation) — les deux mécanismes doivent apparaître dans
        # son espace personnel, d'où le OU plutôt qu'un simple filtre.
        mes_formations = list(
            TrainingSession.objects.select_related("course")
            .filter(Q(attendees=self.request.user) | Q(reservations=self.request.user), status="PLANNED")
            .distinct()
            .order_by("scheduled_at")
        )

        mes_tickets = list(
            CorrectiveTicket.objects.select_related("asset")
            .filter(assignees=self.request.user)
            .exclude(status__in=_STATUTS_TICKET_TERMINES)
            .order_by("-severity", "reported_at")
        )

        aujourdhui = timezone.localdate()

        # Formations déjà validées par le marin (TrainingRecord), avec leur
        # date d'expiration — jusqu'ici cette information n'apparaissait que
        # sous forme de notification ponctuelle (notify_expiring_training,
        # notifications/tasks.py) qui disparaît une fois passée, sans vue
        # d'ensemble permanente dans l'espace personnel du marin.
        #
        # Une seule ligne par formation : en cas de renouvellement, seul le
        # dernier enregistrement (le plus récent completed_at, created_at en
        # cas d'égalité) doit apparaître — l'ancien enregistrement expiré n'a
        # pas d'intérêt une fois remplacé (arbitrage PO sur la page Notion de
        # la tâche).
        derniere_qualification_par_formation = {}
        for qualification in (
            TrainingRecord.objects.select_related("course")
            .filter(user=self.request.user)
            .order_by("-completed_at", "-created_at")
        ):
            derniere_qualification_par_formation.setdefault(qualification.course_id, qualification)
        mes_qualifications = sorted(
            derniere_qualification_par_formation.values(), key=lambda q: q.expires_at
        )
        for qualification in mes_qualifications:
            qualification.badge_classe, qualification.badge_libelle = _badge_qualification(
                qualification, aujourdhui
            )

        contexte["mes_maintenances"] = mes_maintenances
        contexte["mes_formations"] = mes_formations
        contexte["mes_tickets"] = mes_tickets
        contexte["mes_qualifications"] = mes_qualifications
        contexte["aujourdhui"] = aujourdhui
        return contexte


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
    "navire": "Vue de mon navire",
    "secteur": "Vue de mon secteur",
    "section": "Vue de ma section",
}

# Préfixe (avec article accordé) utilisé pour construire la phrase d'intro de
# la Vue flotte quand un nom de périmètre est disponible, ex. "Vue agrégée du
# secteur « Passerelle »." — évite de gérer l'accord masculin/féminin dans le
# template.
_PREFIXE_SOUS_TITRE_PERIMETRE = {
    "navire": "du navire",
    "secteur": "du secteur",
    "section": "de la section",
}

# Message affiché quand le rôle donne accès à la Vue flotte mais qu'aucun
# objet du niveau attendu n'est renseigné sur le profil (ex. CHEF_SECTEUR
# sans secteur rattaché) — accord au masculin/féminin selon le niveau.
_MESSAGE_AUCUN_PERIMETRE = {
    "navire": "Aucun navire n'est associé à votre profil : impossible d'afficher la vue flotte.",
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
            contexte["sous_titre_perimetre"] = "Vue agrégée de la flotte entière (tous navires confondus)."
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
            filtre_ticket = Q(**{f"asset__{champ}": perimetre_id})
            filtre_stock = Q(**{champ: perimetre_id})

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
            .select_related("service", "sector", "section")
            .order_by("reference")
        )
        # Jauge : proportion des pièces de stock sous seuil parmi l'ensemble du
        # périmètre, même logique que la jauge des maintenances en retard ci-dessus.
        total_pieces = StockPiece.objects.filter(filtre_stock).count()
        contexte["pieces_sous_seuil_pct"] = (
            round(len(contexte["pieces_sous_seuil"]) / total_pieces * 100)
            if total_pieces else 0
        )
        contexte["aucun_perimetre"] = False
        return contexte
