"""Interface web du module Quarts/services (Phase 2 — Vie quotidienne).

Périmètre de cette tâche (cf. tâche Notion « Quarts/services ») : un chef de
liste désigné crée une liste (Quart ou ServiceGarde) sur une période, y
affecte des marins sur des créneaux, et la publie. Explicitement hors
périmètre (tâches séparées à venir) : échange de service entre marins,
génération automatique de répartition, affichage des créneaux dans le
calendrier personnel du marin — cette dernière limite volontairement la
visibilité en lecture ci-dessous à une simple fiche détail, pas une
intégration calendrier.
"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views import View

from accounts.models import FonctionQuartChoice, ServiceFunctionChoice
from matrix.core.roles import user_role_level
from matrix.core.scopes import scope_filters_for_user
from org.models import Sector, Section, Service, Ship

from .models import (
    ChefDeListe,
    CreneauQuart,
    CreneauServiceGarde,
    NIVEAU_REQUIS_DESIGNATION_CHEF_DE_LISTE,
    NIVEAU_SUPERVISION_GLOBALE_LISTE,
    Quart,
    ServiceGarde,
    peut_gerer_liste,
    utilisateur_autorise_pour_perimetre,
)

User = get_user_model()


def _resoudre_perimetre(valeur_postee):
    """Résout une valeur postée du type "section:12" en un tuple
    (ship, service, sector, section) où trois valeurs sur quatre sont None —
    même convention d'encodage que le champ "équipement affilié" de
    logistics/web_views.py (StockPieceListView, "installation:<id>"/"asset:<id>")."""
    if not valeur_postee or ":" not in valeur_postee:
        return None, None, None, None
    type_perimetre, _, id_brut = valeur_postee.partition(":")
    try:
        pk = int(id_brut)
    except ValueError:
        return None, None, None, None
    modeles = {"ship": Ship, "service": Service, "sector": Sector, "section": Section}
    modele = modeles.get(type_perimetre)
    if modele is None:
        return None, None, None, None
    obj = modele.objects.filter(pk=pk).first()
    if obj is None:
        return None, None, None, None
    return {
        "ship": (obj, None, None, None),
        "service": (None, obj, None, None),
        "sector": (None, None, obj, None),
        "section": (None, None, None, obj),
    }[type_perimetre]


def _encoder_perimetre(obj):
    for type_perimetre, modele in (("ship", Ship), ("service", Service), ("sector", Sector), ("section", Section)):
        if isinstance(obj, modele):
            return f"{type_perimetre}:{obj.pk}"
    return ""


def _libelle_perimetre(obj):
    if isinstance(obj, Ship):
        return f"Unité — {obj.name}"
    if isinstance(obj, Service):
        return f"Service — {obj}"
    if isinstance(obj, Sector):
        return f"Secteur — {obj}"
    if isinstance(obj, Section):
        return f"Section — {obj}"
    return str(obj)


def _perimetres_org_disponibles(user, borne_par_scope=True):
    """Périmètres organisationnels sélectionnables par `user` dans les
    formulaires de ce module : bornés à son propre périmètre
    (scope_filters_for_user) si `borne_par_scope`, ou l'ensemble de la flotte
    pour une supervision globale — même principe que le menu déroulant de
    secteurs de StockPieceListView (logistics/web_views.py), généralisé aux
    quatre niveaux navire/service/secteur/section."""
    filtres = scope_filters_for_user(user) if borne_par_scope else {}
    ships = Ship.objects.all()
    services = Service.objects.select_related("ship")
    sectors = Sector.objects.select_related("service", "service__ship")
    sections = Section.objects.select_related("sector", "sector__service", "sector__service__ship")
    if filtres:
        (cle, valeur), = filtres.items()
        if cle == "ship_id":
            ships = ships.filter(pk=valeur)
            services = services.filter(ship_id=valeur)
            sectors = sectors.filter(service__ship_id=valeur)
            sections = sections.filter(sector__service__ship_id=valeur)
        elif cle == "service_id":
            ships = Ship.objects.none()
            services = services.filter(pk=valeur)
            sectors = sectors.filter(service_id=valeur)
            sections = sections.filter(sector__service_id=valeur)
        elif cle == "sector_id":
            ships = Ship.objects.none()
            services = Service.objects.none()
            sectors = sectors.filter(pk=valeur)
            sections = sections.filter(sector_id=valeur)
        elif cle == "section_id":
            ships = Ship.objects.none()
            services = Service.objects.none()
            sectors = Sector.objects.none()
            sections = sections.filter(pk=valeur)
    tous = list(ships) + list(services) + list(sectors) + list(sections)
    return [{"valeur": _encoder_perimetre(o), "label": _libelle_perimetre(o)} for o in tous]


def _perimetre_autorise_pour_designation(user, ship, service, sector, section):
    """Vrai si `user` peut désigner/retirer un chef de liste pour le périmètre
    donné : COMMANDANT+ sans restriction (supervision globale), ou
    CHEF_SERVICE+ dont le périmètre organisationnel personnel couvre le
    périmètre visé — un chef ne délègue la responsabilité de chef de liste
    que sur ce qui est déjà sous sa propre autorité, jamais au-delà (cf.
    tâche Notion « Quarts/services », point (c) du cadrage : seuil laissé au
    choix du dev, tranché ici en cohérence avec
    logistics/web_views.py::_secteur_dans_perimetre)."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_LISTE:
        return True
    if user_role_level(user) < NIVEAU_REQUIS_DESIGNATION_CHEF_DE_LISTE:
        return False
    filtres = scope_filters_for_user(user)
    if not filtres:
        return True
    (cle, valeur), = filtres.items()
    valeur = str(valeur)
    if cle == "section_id":
        return section is not None and str(section.pk) == valeur
    if cle == "sector_id":
        if sector is not None:
            return str(sector.pk) == valeur
        if section is not None:
            return str(section.sector_id) == valeur
        return False
    if cle == "service_id":
        if service is not None:
            return str(service.pk) == valeur
        if sector is not None:
            return str(sector.service_id) == valeur
        if section is not None:
            return str(section.sector.service_id) == valeur
        return False
    if cle == "ship_id":
        if ship is not None:
            return str(ship.pk) == valeur
        if service is not None:
            return str(service.ship_id) == valeur
        if sector is not None:
            return str(sector.service.ship_id) == valeur
        if section is not None:
            return str(section.sector.service.ship_id) == valeur
        return False
    return False


def _listes_visibles(model, user):
    """Listes (Quart ou ServiceGarde) que `user` gère : celles de la
    supervision globale (bornées à son périmètre, comme la Vue flotte) ou
    celles correspondant EXACTEMENT à l'un de ses périmètres de chef de
    liste."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_LISTE:
        filtres = scope_filters_for_user(user)
        return model.objects.filter(**filtres) if filtres else model.objects.all()
    q = Q(pk__in=[])
    trouve = False
    for cdl in ChefDeListe.objects.filter(user=user):
        filtres = {
            k: v for k, v in {
                "ship_id": cdl.ship_id, "service_id": cdl.service_id,
                "sector_id": cdl.sector_id, "section_id": cdl.section_id,
            }.items() if v is not None
        }
        if filtres:
            q |= Q(**filtres)
            trouve = True
    return model.objects.filter(q) if trouve else model.objects.none()


def _listes_publiees_me_concernant(model, user):
    """Listes déjà PUBLIÉES dont le périmètre couvre le rattachement
    organisationnel de `user` (son propre niveau, ou tout niveau ANCÊTRE qui
    l'englobe — ex. un marin d'une section voit aussi les listes publiées au
    niveau du secteur, du service ou du navire) — seul moyen, dans le
    périmètre de cette tâche, pour un marin sans rôle de chef de liste de
    consulter une liste le concernant (l'intégration au calendrier personnel
    est une tâche séparée à venir, cf. docstring de module)."""
    profile = getattr(user, "profile", None)
    if not profile:
        return model.objects.none()
    q = Q(pk__in=[])
    if profile.section_id:
        section = profile.section
        q |= Q(section_id=section.pk) | Q(sector_id=section.sector_id) \
            | Q(service_id=section.sector.service_id) | Q(ship_id=section.sector.service.ship_id)
    elif profile.sector_id:
        sector = profile.sector
        q |= Q(sector_id=sector.pk) | Q(service_id=sector.service_id) | Q(ship_id=sector.service.ship_id)
    elif profile.service_id:
        q |= Q(service_id=profile.service_id) | Q(ship_id=profile.service.ship_id)
    elif profile.ship_id:
        q |= Q(ship_id=profile.ship_id)
    else:
        return model.objects.none()
    return model.objects.filter(q, statut=model.STATUT_PUBLIEE)


def _q_marins_du_perimetre(liste):
    """Marins affectables sur un créneau de `liste` : tout le périmètre visé
    et tout ce qui en descend (ex. une liste au niveau secteur peut affecter
    n'importe quel marin d'une section de ce secteur) — à ne pas confondre
    avec la règle de gestion de la liste elle-même (peut_gerer_liste), qui ne
    tolère aucune cascade."""
    if liste.section_id:
        return Q(profile__section_id=liste.section_id)
    if liste.sector_id:
        return Q(profile__sector_id=liste.sector_id) | Q(profile__section__sector_id=liste.sector_id)
    if liste.service_id:
        return (
            Q(profile__service_id=liste.service_id)
            | Q(profile__sector__service_id=liste.service_id)
            | Q(profile__section__sector__service_id=liste.service_id)
        )
    if liste.ship_id:
        return (
            Q(profile__ship_id=liste.ship_id)
            | Q(profile__service__ship_id=liste.ship_id)
            | Q(profile__sector__service__ship_id=liste.ship_id)
            | Q(profile__section__sector__service__ship_id=liste.ship_id)
        )
    return Q(pk__in=[])


def _peut_lire_liste(user, liste):
    """Lecture d'une liste déjà PUBLIÉE, ouverte à tout marin qui en relève
    (même règle de cascade que les marins affectables sur un créneau, cf.
    _q_marins_du_perimetre) — une liste encore en BROUILLON reste visible
    uniquement à ses chefs de liste gérants (cf. peut_gerer_liste)."""
    if liste.statut != liste.STATUT_PUBLIEE:
        return False
    return User.objects.filter(_q_marins_du_perimetre(liste), pk=user.pk).exists()


class ListeIndexView(LoginRequiredMixin, View):
    """Tableau de bord du module : listes gérées par l'utilisateur (s'il est
    chef de liste ou en supervision globale), listes publiées le concernant,
    et création d'une nouvelle liste."""

    template_name = "quarts/liste_index.html"

    def _contexte(self, user):
        supervision_globale = user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_LISTE
        mes_perimetres = ChefDeListe.objects.filter(user=user).select_related("ship", "service", "sector", "section")
        if supervision_globale:
            perimetres_creation = _perimetres_org_disponibles(user, borne_par_scope=False)
        else:
            perimetres_creation = [
                {"valeur": _encoder_perimetre(cdl.perimetre), "label": _libelle_perimetre(cdl.perimetre)}
                for cdl in mes_perimetres
            ]
        return {
            "quarts": _listes_visibles(Quart, user),
            "services_garde": _listes_visibles(ServiceGarde, user),
            "quarts_publies_me_concernant": _listes_publiees_me_concernant(Quart, user),
            "gardes_publiees_me_concernant": _listes_publiees_me_concernant(ServiceGarde, user),
            "perimetres_creation": perimetres_creation,
            "peut_creer": bool(perimetres_creation),
            "peut_designer_chef_de_liste": user_role_level(user) >= NIVEAU_REQUIS_DESIGNATION_CHEF_DE_LISTE,
            # Fonction obligatoire par liste (correction de cadrage du
            # 09/09/2026, cf. docstring de quarts/models.py) : deux
            # référentiels distincts selon le type de liste créée.
            "fonctions_quart": FonctionQuartChoice.objects.filter(active=True).order_by("name"),
            "fonctions_service": ServiceFunctionChoice.objects.filter(active=True).order_by("name"),
        }

    def get(self, request):
        return render(request, self.template_name, self._contexte(request.user))

    def post(self, request):
        action = request.POST.get("action")
        if action not in ("creer_quart", "creer_service_garde"):
            return HttpResponseBadRequest("Action inconnue.")

        ship, service, sector, section = _resoudre_perimetre(request.POST.get("perimetre"))
        if not any([ship, service, sector, section]):
            messages.error(request, "Le périmètre est obligatoire.")
            return redirect("quarts-index")
        if not utilisateur_autorise_pour_perimetre(request.user, ship, service, sector, section):
            raise PermissionDenied

        date_debut = parse_date(request.POST.get("date_debut", ""))
        date_fin = parse_date(request.POST.get("date_fin", ""))
        if not date_debut or not date_fin:
            messages.error(request, "La période (début et fin) est obligatoire.")
            return redirect("quarts-index")

        champs_communs = dict(
            nom=request.POST.get("nom", "").strip(),
            ship=ship, service=service, sector=sector, section=section,
            date_debut=date_debut, date_fin=date_fin,
            created_by=request.user, updated_by=request.user,
        )
        # Fonction obligatoire, référentiel distinct selon le type de liste
        # (cf. docstring de quarts/models.py, correction du 09/09/2026) :
        # une liste de quarts choisit une FonctionQuartChoice, une liste de
        # garde réutilise le référentiel ServiceFunctionChoice déjà existant.
        if action == "creer_quart":
            fonction = FonctionQuartChoice.objects.filter(pk=request.POST.get("fonction_quart"), active=True).first()
            liste = Quart(fonction=fonction, **champs_communs)
            url_name = "quart-detail"
        else:
            fonction = ServiceFunctionChoice.objects.filter(pk=request.POST.get("fonction_service"), active=True).first()
            liste = ServiceGarde(fonction=fonction, **champs_communs)
            url_name = "garde-detail"

        try:
            liste.full_clean()
        except ValidationError as exc:
            for erreurs in exc.message_dict.values():
                for erreur in erreurs:
                    messages.error(request, erreur)
            return redirect("quarts-index")

        liste.save()
        messages.success(request, "Liste créée en brouillon : ajoutez les créneaux puis publiez-la.")
        return redirect(url_name, pk=liste.pk)


class _DetailListeViewBase(LoginRequiredMixin, View):
    """Fiche détail générique d'une liste (créneaux + affectations +
    publication), paramétrée par QuartDetailView et ServiceGardeDetailView
    ci-dessous pour ne pas dupliquer cette mécanique entre les deux modèles
    concrets (cf. docstring de quarts/models.py)."""

    model = None
    creneau_model = None
    fk_attr = None
    url_prefix = None
    template_name = "quarts/liste_detail.html"

    def _liste(self, pk):
        return self.model.objects.filter(pk=pk).first()

    def get(self, request, pk):
        liste = self._liste(pk)
        if liste is None:
            return HttpResponseBadRequest("Liste introuvable.")
        peut_gerer = peut_gerer_liste(request.user, liste)
        if not peut_gerer and not _peut_lire_liste(request.user, liste):
            return HttpResponseBadRequest("Liste introuvable ou hors de votre périmètre.")
        contexte = {
            "liste": liste,
            "creneaux": liste.creneaux.select_related("marin").all(),
            "peut_gerer": peut_gerer,
            "url_prefix": self.url_prefix,
            "marins_perimetre": (
                User.objects.filter(_q_marins_du_perimetre(liste)).select_related("profile")
                .order_by("username").distinct()
                if peut_gerer else User.objects.none()
            ),
        }
        return render(request, self.template_name, contexte)

    def post(self, request, pk):
        liste = self._liste(pk)
        if liste is None:
            return HttpResponseBadRequest("Liste introuvable.")
        if not peut_gerer_liste(request.user, liste):
            return HttpResponseBadRequest("Liste introuvable ou hors de votre périmètre.")

        action = request.POST.get("action")
        if action == "ajouter_creneau":
            self._ajouter_creneau(request, liste)
        elif action == "supprimer_creneau":
            self._supprimer_creneau(request, liste)
        elif action == "publier":
            liste.publier(request.user)
            messages.success(request, "Liste publiée : les marins affectés ont été notifiés.")
        else:
            return HttpResponseBadRequest("Action inconnue.")
        return redirect(f"{self.url_prefix}-detail", pk=liste.pk)

    def _ajouter_creneau(self, request, liste):
        poste = request.POST.get("poste", "").strip()
        debut = parse_datetime(request.POST.get("debut", "").strip())
        if not poste or debut is None:
            messages.error(request, "Le poste et l'heure de début sont obligatoires.")
            return
        if timezone.is_naive(debut):
            debut = timezone.make_aware(debut)

        fin = parse_datetime(request.POST.get("fin", "").strip())
        if fin is not None and timezone.is_naive(fin):
            fin = timezone.make_aware(fin)
        if fin is None:
            # Pas de fin saisie : calculée à partir de la durée par défaut
            # configurée sur la liste (jamais une durée codée en dur, cf.
            # Quart/ServiceGarde.duree_creneau_heures).
            fin = debut + timezone.timedelta(hours=liste.duree_creneau_heures)

        marin = None
        marin_id = request.POST.get("marin")
        if marin_id:
            marin = User.objects.filter(_q_marins_du_perimetre(liste), pk=marin_id).distinct().first()
            if marin is None:
                messages.error(request, "Le marin choisi ne fait pas partie du périmètre de cette liste.")
                return

        creneau = self.creneau_model(
            poste=poste, debut=debut, fin=fin, marin=marin,
            note=request.POST.get("note", "").strip(),
            **{self.fk_attr: liste},
        )
        try:
            creneau.full_clean()
        except ValidationError as exc:
            for erreurs in exc.message_dict.values():
                for erreur in erreurs:
                    messages.error(request, erreur)
            return
        creneau.save()
        messages.success(request, "Créneau ajouté.")

    def _supprimer_creneau(self, request, liste):
        creneau = self.creneau_model.objects.filter(
            pk=request.POST.get("creneau_id"), **{self.fk_attr: liste}
        ).first()
        if creneau is None:
            messages.error(request, "Créneau introuvable.")
            return
        creneau.delete()
        messages.info(request, "Créneau supprimé.")


class QuartDetailView(_DetailListeViewBase):
    model = Quart
    creneau_model = CreneauQuart
    fk_attr = "quart"
    url_prefix = "quart"


class ServiceGardeDetailView(_DetailListeViewBase):
    model = ServiceGarde
    creneau_model = CreneauServiceGarde
    fk_attr = "service_garde"
    url_prefix = "garde"


class ChefDeListeReglagesView(LoginRequiredMixin, View):
    """Désignation/retrait des chefs de liste — réservé à CHEF_SERVICE et
    au-dessus, dans la limite de leur propre périmètre organisationnel (cf.
    _perimetre_autorise_pour_designation)."""

    template_name = "quarts/reglages.html"

    def get(self, request):
        if user_role_level(request.user) < NIVEAU_REQUIS_DESIGNATION_CHEF_DE_LISTE:
            raise PermissionDenied
        contexte = {
            "chefs_de_liste": ChefDeListe.objects.select_related(
                "user", "ship", "service", "sector", "section"
            ).order_by("user__username"),
            "perimetres_disponibles": _perimetres_org_disponibles(
                request.user, borne_par_scope=user_role_level(request.user) < NIVEAU_SUPERVISION_GLOBALE_LISTE
            ),
            "utilisateurs": User.objects.filter(is_active=True).order_by("username"),
        }
        return render(request, self.template_name, contexte)

    def post(self, request):
        if user_role_level(request.user) < NIVEAU_REQUIS_DESIGNATION_CHEF_DE_LISTE:
            raise PermissionDenied
        action = request.POST.get("action")

        if action == "designer":
            ship, service, sector, section = _resoudre_perimetre(request.POST.get("perimetre"))
            if not any([ship, service, sector, section]):
                messages.error(request, "Le périmètre est obligatoire.")
                return redirect("quarts-reglages")
            if not _perimetre_autorise_pour_designation(request.user, ship, service, sector, section):
                raise PermissionDenied
            candidat = User.objects.filter(pk=request.POST.get("user_id")).first()
            if candidat is None:
                messages.error(request, "Marin introuvable.")
                return redirect("quarts-reglages")
            _, cree = ChefDeListe.objects.get_or_create(
                user=candidat, ship=ship, service=service, sector=sector, section=section
            )
            if cree:
                messages.success(request, f"{candidat.get_full_name() or candidat.username} désigné(e) chef de liste.")
            else:
                messages.info(request, "Cette désignation existe déjà.")
        elif action == "retirer":
            cdl = ChefDeListe.objects.filter(pk=request.POST.get("pk")).first()
            if cdl is None:
                messages.error(request, "Désignation introuvable.")
                return redirect("quarts-reglages")
            if not _perimetre_autorise_pour_designation(request.user, cdl.ship, cdl.service, cdl.sector, cdl.section):
                raise PermissionDenied
            cdl.delete()
            messages.info(request, "Désignation retirée.")
        else:
            return HttpResponseBadRequest("Action inconnue.")
        return redirect("quarts-reglages")
