"""Vue web de la page d'accueil — tableau de bord + espace personnel du marin.

Principe fondamental n°3 (CLAUDE.md) : chaque marin voit SES tâches, SES
formations, SES maintenances assignées, dès la connexion, sans avoir à
chercher. Cette vue construit le contexte de l'accueil pour ça, en plus
des graphiques Chart.js déjà en place (T5) et du bouton "Générer le bilan"
(T10), qui restent inchangés.
"""
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from assets.models import Installation, InstallationMaintenance
from dashboard.models import ItemAppareillage, SessionAppareillage
from logistics.models import CorrectiveTicket, STATUTS_TICKET_OUVERTS, StockPiece
from maintenance.models import MaintenanceOccurrence
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, section_id_for_user, sector_id_for_user, ship_id_for_user
from notifications.models import Notification
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


# Nombre de jours au-delà duquel un dernier relevé technique (heures de marche,
# vibration, isolement) sur une installation critique est considéré comme "pas
# récent" dans le tableau « Prêt à appareillage » ci-dessous. Un seuil unique,
# simple à expliquer au Commandant (principe n°2 CLAUDE.md : pas de jargon), à
# ne pas confondre avec l'échéance précise par installation (vib_days_a/b/c,
# iso_periodicity) utilisée par generate_installation_notifications pour ses
# alertes récurrentes — ici on ne veut qu'un repère visuel avant appareillage,
# pas recalculer cette échéance métier plus fine.
SEUIL_RELEVE_RECENT_JOURS = 90


def _dernier_releve(installation, related_name, formateur_valeur):
    """Dernier relevé technique d'une installation pour un type de mesure donné
    (heures de marche / vibration / isolement), sous forme de dict prêt à
    afficher : date, valeur formatée, et statut visuel (badge-conforme /
    text-bg-warning / text-bg-danger) selon l'ancienneté par rapport à
    SEUIL_RELEVE_RECENT_JOURS ci-dessus.

    `related_name` est le related_name du queryset déjà préchargé par
    prefetch_related sur `installation` (ex. "hour_readings"), pour éviter une
    requête par installation."""
    dernier = max(getattr(installation, related_name).all(), key=lambda r: r.date, default=None)
    if dernier is None:
        return {"releve": None, "date": None, "valeur": None, "badge_classe": "text-bg-danger", "badge_libelle": "Jamais relevé"}
    anciennete = (timezone.localdate() - dernier.date).days
    if anciennete > SEUIL_RELEVE_RECENT_JOURS:
        badge_classe, badge_libelle = "text-bg-warning", "Relevé ancien"
    else:
        badge_classe, badge_libelle = "badge-conforme", "Récent"
    return {
        "releve": dernier,
        "date": dernier.date,
        "valeur": formateur_valeur(dernier),
        "badge_classe": badge_classe,
        "badge_libelle": badge_libelle,
    }


def _points_de_vigilance_navire(ship_id):
    """Points de vigilance avant appareillage sur les installations critiques
    d'un navire donné, réutilisant exactement les quatre familles de la
    précédente version en lecture seule de cette page (occurrences en retard,
    relevés manquants ou anciens, dérives non résolues, stock sous seuil) —
    seule différence : ce calcul n'est plus refait à chaque affichage, il ne
    sert plus qu'à peupler les items d'une session au moment de son ouverture
    (SessionAppareillageOuvrirView ci-dessous), pour figer l'état constaté à
    cet instant précis (arbitrage utilisateur : une session datée, pas un
    état permanent recalculé en continu).

    Renvoie une liste de dicts prêts à devenir des ItemAppareillage :
    {"categorie", "libelle", "content_type", "object_id"}."""
    items = []

    installations_critiques = list(
        Installation.objects.filter(ship_id=ship_id, critique=True)
        .prefetch_related("hour_readings", "vibration_readings", "isolation_readings")
    )
    installation_ct = ContentType.objects.get_for_model(Installation)

    for installation in installations_critiques:
        for related_name, formateur, libelle_type in (
            ("hour_readings", lambda r: f"{r.hours} h", "heures de marche"),
            ("vibration_readings", lambda r: r.get_state_display(), "vibration"),
            ("isolation_readings", lambda r: f"{r.ohms} Ω", "isolement"),
        ):
            releve = _dernier_releve(installation, related_name, formateur)
            if releve["badge_classe"] != "badge-conforme":
                items.append({
                    "categorie": ItemAppareillage.CATEGORIE_RELEVE,
                    "libelle": f"{installation.designation} — Relevé {libelle_type} : {releve['badge_libelle'].lower()}",
                    "content_type": installation_ct,
                    "object_id": str(installation.id),
                })

    # Essais de bon fonctionnement / relevés en retard sur une installation
    # critique du navire (même exclusion _STATUTS_MAINTENANCE_TERMINES que le
    # reste du tableau de bord), triés par échéance la plus proche en premier.
    occurrence_ct = ContentType.objects.get_for_model(MaintenanceOccurrence)
    occurrences_a_verifier = (
        MaintenanceOccurrence.objects.select_related(
            "installation_maintenance", "installation_maintenance__installation"
        )
        .filter(
            installation_maintenance__installation__ship_id=ship_id,
            installation_maintenance__installation__critique=True,
        )
        .exclude(status__in=_STATUTS_MAINTENANCE_TERMINES)
        .order_by("scheduled_for")
    )
    for occurrence in occurrences_a_verifier:
        items.append({
            "categorie": ItemAppareillage.CATEGORIE_OCCURRENCE,
            "libelle": (
                f"{occurrence.titre_affiche} — échéance {occurrence.scheduled_for} "
                f"({occurrence.get_status_display()})"
            ),
            "content_type": occurrence_ct,
            "object_id": str(occurrence.id),
        })

    # Dérives détectées non résolues (detect_installation_drift,
    # notifications/tasks.py) : réutilise directement les notifications déjà
    # créées par cette tâche, identifiées par leur object_id
    # ("<installation>:DERIVE_ISOLEMENT" / "<maintenance>:DERIVE_HEURES") —
    # l'item pointe ensuite vers le vrai identifiant de l'objet concerné (pas
    # le couple composite propre au système de notifications).
    maintenance_ct = ContentType.objects.get_for_model(InstallationMaintenance)
    ids_installations_critiques = [installation.id for installation in installations_critiques]
    ids_maintenances_critiques = list(
        InstallationMaintenance.objects.filter(
            installation_id__in=ids_installations_critiques
        ).values_list("id", flat=True)
    )
    objets_isolement = {f"{installation_id}:DERIVE_ISOLEMENT" for installation_id in ids_installations_critiques}
    objets_heures = {f"{maintenance_id}:DERIVE_HEURES" for maintenance_id in ids_maintenances_critiques}
    derives_qs = (
        Notification.objects.filter(is_read=False)
        .filter(
            Q(content_type=installation_ct, object_id__in=objets_isolement)
            | Q(content_type=maintenance_ct, object_id__in=objets_heures)
        )
        .order_by("verb")
    )
    # _signaler_ou_resoudre_derive (notifications/tasks.py) crée une
    # Notification par destinataire (CHEF_SERVICE, CHEF_SECTEUR, CHEF_SECTION...)
    # pour une même dérive physique : .distinct() sans argument ne déduplique
    # rien ici puisque id/user_id/created_at diffèrent d'une notification à
    # l'autre. On déduplique donc explicitement en Python par (content_type,
    # object_id) — l'identifiant de la dérive physique, indépendant du
    # destinataire — en ne gardant que la première notification rencontrée pour
    # fournir le libellé affiché.
    derives_par_cle = {}
    for derive in derives_qs:
        cle = (derive.content_type_id, derive.object_id)
        derives_par_cle.setdefault(cle, derive)
    for derive in derives_par_cle.values():
        items.append({
            "categorie": ItemAppareillage.CATEGORIE_DERIVE,
            "libelle": derive.verb,
            "content_type": derive.content_type,
            "object_id": derive.object_id.split(":")[0],
        })

    # Stock sous seuil du navire (même requête que VueFlotteView) : pas de lien
    # direct StockPiece <-> Installation en base, donc pas de restriction
    # supplémentaire aux seules installations critiques (même hypothèse que la
    # précédente version de cette page : le stock pertinent avant un
    # appareillage est celui du navire concerné, pas seulement les pièces
    # d'installations critiques).
    stock_ct = ContentType.objects.get_for_model(StockPiece)
    pieces_sous_seuil = StockPiece.objects.filter(
        ship_id=ship_id, quantite__lt=F("quantite_minimale")
    ).order_by("reference")
    for piece in pieces_sous_seuil:
        items.append({
            "categorie": ItemAppareillage.CATEGORIE_STOCK,
            "libelle": f"{piece.reference} — {piece.designation} ({piece.quantite}/{piece.quantite_minimale})",
            "content_type": stock_ct,
            "object_id": str(piece.id),
        })

    return items


def _items_groupes_par_categorie(session):
    """Items d'une session d'appareillage regroupés par catégorie, dans l'ordre
    d'affichage du template (mêmes quatre familles que _points_de_vigilance_navire
    ci-dessus)."""
    items = list(session.items.select_related("verifie_par").order_by("libelle"))
    groupes = []
    for code, libelle in ItemAppareillage.CATEGORIES:
        items_categorie = [item for item in items if item.categorie == code]
        if items_categorie:
            groupes.append({"code": code, "libelle": libelle, "items": items_categorie})
    return groupes


def _meme_navire_ou_master_admin(user, ship_id):
    """Vrai si l'utilisateur appartient au même navire que celui de la session/
    de l'item consulté, ou s'il a un accès flotte entière (MASTER_ADMIN/
    superutilisateur, cf. is_master_admin) — isolation stricte par navire pour
    tous les autres rôles."""
    if is_master_admin(user):
        return True
    return ship_id_for_user(user) == ship_id


class PretAppareillageView(LoginRequiredMixin, TemplateView):
    """Page « Prêt à appareillage » : affiche la session de préparation
    actuellement ouverte pour le navire de l'utilisateur connecté (checklist à
    cocher), ou propose d'en ouvrir une nouvelle s'il n'y en a pas.

    Contrairement à la précédente version (lecture seule, réservée à
    COMMANDANT+), cette page est ouverte à tout marin authentifié du navire
    (EQUIPIER+, aucune restriction de rôle) : la saisie — cocher un point
    vérifié — doit rester accessible à quiconque effectue la vérification sur
    le terrain (arbitrage utilisateur documenté dans le commentaire [Dev] de
    la tâche Notion). Seules l'ouverture d'une session et sa signature restent
    réservées à CHEF_SECTEUR et aux rôles supérieurs (cf. vues ci-dessous)."""

    template_name = "dashboard/pret_appareillage.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        user = self.request.user

        contexte["peut_ouvrir_session"] = user_role_level(user) >= RoleLevel.CHEF_SECTEUR
        contexte["peut_signer"] = user_role_level(user) >= RoleLevel.CHEF_SECTEUR

        if is_master_admin(user):
            # Une session porte sur un seul navire : un MASTER_ADMIN (rattaché à
            # aucun navire en particulier) ne peut pas en ouvrir une ici — il
            # consulte l'historique de tous les navires (HistoriqueAppareillageView).
            contexte["aucun_navire"] = False
            contexte["multi_navires"] = True
            contexte["session"] = None
            return contexte

        ship_id = ship_id_for_user(user)
        if ship_id is None:
            contexte["aucun_navire"] = True
            contexte["multi_navires"] = False
            contexte["session"] = None
            return contexte

        contexte["aucun_navire"] = False
        contexte["multi_navires"] = False
        session = (
            SessionAppareillage.objects.filter(ship_id=ship_id, cloturee_le__isnull=True)
            .select_related("ship")
            .order_by("-ouverte_le")
            .first()
        )
        contexte["session"] = session
        if session:
            contexte["items_par_categorie"] = _items_groupes_par_categorie(session)
        return contexte


class SessionAppareillageOuvrirView(LoginRequiredMixin, View):
    """Ouvre une nouvelle session d'appareillage pour le navire de
    l'utilisateur connecté, avec les items générés une fois pour toutes par
    _points_de_vigilance_navire ci-dessus.

    Réservée à CHEF_SECTEUR et aux rôles supérieurs : même seuil minimum que la
    signature (SessionAppareillageSignerView) — ouvrir une session officielle
    de préparation à l'appareillage est un acte de même nature que la
    clôturer. Le PO ne fixe pas ce point précis dans sa spécification (qui ne
    cadre explicitement que le rôle signataire) ; c'est une hypothèse de
    cadrage du Dev, à confirmer en revue."""

    def post(self, request):
        user = request.user
        if user_role_level(user) < RoleLevel.CHEF_SECTEUR:
            raise PermissionDenied("Réservé aux chefs de secteur et aux rôles supérieurs.")

        ship_id = ship_id_for_user(user)
        if ship_id is None:
            messages.error(request, "Aucun navire n'est associé à votre profil : impossible d'ouvrir une session.")
            return redirect("pret-appareillage")

        if SessionAppareillage.objects.filter(ship_id=ship_id, cloturee_le__isnull=True).exists():
            messages.warning(request, "Une session d'appareillage est déjà ouverte pour ce navire.")
            return redirect("pret-appareillage")

        session = SessionAppareillage.objects.create(ship_id=ship_id, created_by=user, updated_by=user)
        items = [
            ItemAppareillage(session=session, **item_data)
            for item_data in _points_de_vigilance_navire(ship_id)
        ]
        ItemAppareillage.objects.bulk_create(items)

        if items:
            messages.success(request, f"Session d'appareillage ouverte : {len(items)} point(s) à vérifier.")
        else:
            messages.success(request, "Session d'appareillage ouverte : aucun point de vigilance détecté.")
        return redirect("pret-appareillage")


class ItemAppareillageCocherView(LoginRequiredMixin, View):
    """Coche ou décoche un item d'une session d'appareillage ouverte —
    accessible à tout marin authentifié du navire concerné (EQUIPIER+, aucune
    restriction de rôle, spec PO), tant que la session n'est pas clôturée.

    Rendu HTMX : renvoie la checklist mise à jour (même pattern que
    logistics/_part_requests.html — un hx-post ciblant un conteneur, en
    hx-swap="outerHTML")."""

    def post(self, request, pk):
        try:
            item = ItemAppareillage.objects.select_related("session").get(pk=pk)
        except ItemAppareillage.DoesNotExist:
            return HttpResponseBadRequest("Item introuvable.")

        if not _meme_navire_ou_master_admin(request.user, item.session.ship_id):
            raise PermissionDenied("Hors de votre périmètre.")
        if not item.session.est_ouverte:
            return HttpResponseBadRequest("Session déjà clôturée : plus aucune modification n'est possible.")

        if item.verifie_par_id:
            item.verifie_par = None
            item.verifie_le = None
        else:
            item.verifie_par = request.user
            item.verifie_le = timezone.now()
        item.save(update_fields=["verifie_par", "verifie_le", "updated_at"])

        session = item.session
        contexte = {
            "session": session,
            "items_par_categorie": _items_groupes_par_categorie(session),
            "peut_signer": user_role_level(request.user) >= RoleLevel.CHEF_SECTEUR,
        }
        return render(request, "dashboard/_checklist_appareillage.html", contexte)


class SessionAppareillageSignerView(LoginRequiredMixin, View):
    """Signe et clôture une session d'appareillage — réservée à CHEF_SECTEUR et
    aux rôles supérieurs (spec PO). Réutilise exactement le pattern de
    signature déjà en place sur MaintenanceExecution (maintenance/web_views.py
    ::OccurrenceExecuteView) : vérification par mot de passe
    (request.user.check_password), rien de nouveau inventé."""

    def post(self, request, pk):
        try:
            session = SessionAppareillage.objects.select_related("ship").get(pk=pk)
        except SessionAppareillage.DoesNotExist:
            return HttpResponseBadRequest("Session introuvable.")

        user = request.user
        if not _meme_navire_ou_master_admin(user, session.ship_id):
            raise PermissionDenied("Hors de votre périmètre.")
        if user_role_level(user) < RoleLevel.CHEF_SECTEUR:
            raise PermissionDenied("Réservé aux chefs de secteur et aux rôles supérieurs.")
        if not session.est_ouverte:
            messages.warning(request, "Cette session est déjà clôturée.")
            return redirect("pret-appareillage")

        if not user.check_password(request.POST.get("mot_de_passe", "")):
            messages.error(request, "Mot de passe incorrect : la session n'a pas été signée.")
            return redirect("pret-appareillage")

        maintenant = timezone.now()
        session.valide_par = user
        session.date_validation = maintenant
        session.cloturee_le = maintenant
        session.updated_by = user
        session.save(update_fields=["valide_par", "date_validation", "cloturee_le", "updated_by", "updated_at"])

        messages.success(request, "Session d'appareillage signée et clôturée.")
        return redirect("pret-appareillage")


class HistoriqueAppareillageView(LoginRequiredMixin, TemplateView):
    """Historique des sessions d'appareillage déjà clôturées (signées) —
    consultation en lecture seule, ouverte à tout marin authentifié, scopée au
    navire de l'utilisateur (toute la flotte pour un MASTER_ADMIN, même règle
    que _meme_navire_ou_master_admin ci-dessus)."""

    template_name = "dashboard/historique_appareillage.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        user = self.request.user

        if is_master_admin(user):
            sessions = SessionAppareillage.objects.filter(cloturee_le__isnull=False)
        else:
            ship_id = ship_id_for_user(user)
            if ship_id is None:
                contexte["aucun_navire"] = True
                contexte["sessions"] = []
                return contexte
            sessions = SessionAppareillage.objects.filter(ship_id=ship_id, cloturee_le__isnull=False)

        contexte["aucun_navire"] = False
        contexte["sessions"] = list(
            sessions.select_related("ship", "valide_par").order_by("-cloturee_le")
        )
        return contexte


class SessionAppareillageDetailView(LoginRequiredMixin, TemplateView):
    """Détail en lecture seule d'une session d'appareillage (ouverte ou
    clôturée), accessible depuis l'historique — isolation par navire comme le
    reste de la fonctionnalité."""

    template_name = "dashboard/detail_session_appareillage.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        session = get_object_or_404(
            SessionAppareillage.objects.select_related("ship", "valide_par"), pk=kwargs["pk"]
        )
        if not _meme_navire_ou_master_admin(self.request.user, session.ship_id):
            raise PermissionDenied("Hors de votre périmètre.")

        contexte["session"] = session
        contexte["items_par_categorie"] = _items_groupes_par_categorie(session)
        # Lecture seule dans cette vue historique : la signature ne se fait que
        # depuis la page principale (PretAppareillageView), tant que la session
        # est encore ouverte.
        contexte["peut_signer"] = False
        return contexte
