"""Sessions « Prêt à appareillage » (dashboard/web_views.py).

Sous-domaine extrait lors du découpage du fichier (tâche Notion « [ARCH]
Découper dashboard/web_views.py (1063 lignes) par sous-domaine »,
dashboard/web_views.py ayant dépassé 800 lignes) : la checklist datée et
tracée de préparation à l'appareillage (ouverture, pointage des items,
signature, historique).

Refactor pur : reproduit exactement le comportement d'origine."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from assets.models import Installation, InstallationMaintenance
from logistics.models import StockPiece
from maintenance.models import MaintenanceOccurrence
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, ship_id_for_user
from notifications.models import Notification

from .models import ItemAppareillage, SessionAppareillage
from .web_views import _STATUTS_MAINTENANCE_TERMINES

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
            messages.error(request, "Aucune unité n'est associée à votre profil : impossible d'ouvrir une session.")
            return redirect("pret-appareillage")

        if SessionAppareillage.objects.filter(ship_id=ship_id, cloturee_le__isnull=True).exists():
            messages.warning(request, "Une session d'appareillage est déjà ouverte pour cette unité.")
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
