"""Listes de quarts/gardes (quarts/web_views.py) : création, créneaux,
publication et désignation des chefs de liste.

Sous-domaine extrait lors du découpage du fichier (tâche Notion « [ARCH]
Découper quarts/web_views.py (1086 lignes) par sous-domaine »,
quarts/web_views.py ayant dépassé 800 lignes) : un chef de liste désigné crée
une liste (Quart ou ServiceGarde) sur une période, y affecte des marins sur
des créneaux, et la publie (cf. docstring de quarts/web_views.py pour le
périmètre complet du module).

Refactor pur : reproduit exactement le comportement d'origine. La fonction
_peut_lire_liste reste partagée avec quarts/echanges_views.py (voir
quarts/web_views.py, import circulaire volontaire déjà en place pour
dashboard/web_views.py avant ce découpage)."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views import View

from accounts.models import FonctionQuartChoice, ServiceFunctionChoice
from matrix.core.roles import user_role_level
from matrix.core.scopes import equipage_agissant, equipage_marin_q, perimetre_navire_q, scope_filters_for_user
from org.models import Sector, Section, Service, Ship
from training.models import TrainingCourse

from .echanges import annuler_echanges_du_creneau
from .models import (
    ChefDeListe,
    CreneauQuart,
    CreneauServiceGarde,
    EchangeService,
    NIVEAU_REQUIS_DESIGNATION_CHEF_DE_LISTE,
    NIVEAU_LECTURE_GLOBALE_LISTE,
    NIVEAU_SUPERVISION_GLOBALE_LISTE,
    Quart,
    ServiceGarde,
    equipage_du_perimetre,
    listes_de_l_equipage_q,
    marins_du_perimetre,
    perimetre_de_mon_equipage,
    peut_gerer_liste,
    peut_publier_liste,
    utilisateur_autorise_pour_perimetre,
)
from .echanges_views import _echanges_visibles, _grouper_echanges
from .services import compteurs_equite_perimetre
from .web_views import _peut_lire_liste

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
    if not perimetre_de_mon_equipage(user, equipage_du_perimetre(user)):
        return False
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
    if user_role_level(user) >= NIVEAU_LECTURE_GLOBALE_LISTE:
        filtres = scope_filters_for_user(user)
        visibles = model.objects.filter(**filtres) if filtres else model.objects.all()
        return visibles.filter(listes_de_l_equipage_q(user))
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
    return model.objects.filter(q).filter(listes_de_l_equipage_q(user)) if trouve else model.objects.none()


def _listes_publiees_me_concernant(model, user):
    """Listes déjà PUBLIÉES dont le périmètre couvre le rattachement
    organisationnel de `user` (son propre niveau, ou tout niveau ANCÊTRE qui
    l'englobe — ex. un marin d'une section voit aussi les listes publiées au
    niveau du secteur, du service ou du navire) — moyen, pour un marin sans
    rôle de chef de liste, de consulter la fiche complète d'une liste le
    concernant depuis ce tableau de bord (ses créneaux personnels affectés
    apparaissent en plus directement sur son calendrier, cf. docstring de
    module de quarts/web_views.py)."""
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
    return model.objects.filter(q, statut=model.STATUT_PUBLIEE).filter(listes_de_l_equipage_q(user))


def _perimetres_creation(user):
    """Périmètres où `user` peut créer une liste : toute la flotte en supervision
    globale, sinon ses périmètres de chef de liste."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_LISTE:
        return _perimetres_org_disponibles(user, borne_par_scope=False)
    return [
        {"valeur": _encoder_perimetre(cdl.perimetre), "label": _libelle_perimetre(cdl.perimetre)}
        for cdl in ChefDeListe.objects.filter(user=user).select_related("ship", "service", "sector", "section")
    ]


class ListeIndexView(LoginRequiredMixin, View):
    """Tableau de bord du module : listes gérées par l'utilisateur (s'il est
    chef de liste ou en supervision globale), listes publiées le concernant,
    et création d'une nouvelle liste."""

    template_name = "quarts/liste_index.html"

    def _contexte(self, user):
        perimetres_creation = _perimetres_creation(user)
        return {
            "quarts": _listes_visibles(Quart, user),
            "services_garde": _listes_visibles(ServiceGarde, user),
            "quarts_publies_me_concernant": _listes_publiees_me_concernant(Quart, user),
            "gardes_publiees_me_concernant": _listes_publiees_me_concernant(ServiceGarde, user),
            "perimetres_creation": perimetres_creation,
            "peut_creer": bool(perimetres_creation),
            "peut_designer_chef_de_liste": user_role_level(user) >= NIVEAU_REQUIS_DESIGNATION_CHEF_DE_LISTE,
        }

    def get(self, request):
        return render(request, self.template_name, self._contexte(request.user))

    def post(self, request):
        action = request.POST.get("action")
        if action not in ("creer_quart", "creer_service_garde"):
            return HttpResponseBadRequest("Action inconnue.")
        return _creer_liste(request, action, "quarts-index")


def _creer_liste(request, action, retour_erreur):
    """Crée le brouillon d'une liste depuis la saisie postée (index ou assistant)."""
    ship, service, sector, section = _resoudre_perimetre(request.POST.get("perimetre"))
    if not any([ship, service, sector, section]):
        messages.error(request, "Le périmètre est obligatoire.")
        return redirect(retour_erreur)
    if not utilisateur_autorise_pour_perimetre(request.user, ship, service, sector, section):
        raise PermissionDenied

    date_debut = parse_date(request.POST.get("date_debut", ""))
    date_fin = parse_date(request.POST.get("date_fin", ""))
    if not date_debut or not date_fin:
        messages.error(request, "La période (début et fin) est obligatoire.")
        return redirect(retour_erreur)

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
        return redirect(retour_erreur)

    liste.save()
    messages.success(request, "Liste créée en brouillon : ajoutez les créneaux puis publiez-la.")
    return redirect(url_name, pk=liste.pk)


class CreerListeView(LoginRequiredMixin, View):
    """Assistant de création d'une liste : type, période, périmètre (sauté s'il
    est unique), règles puis vérification. La création finale réutilise
    `_creer_liste` : mêmes contrôles et mêmes droits que l'index."""

    template_name = "quarts/liste_creer.html"

    def _etapes(self, perimetres):
        etapes = [("type", "Type"), ("periode", "Période"), ("perimetre", "Périmètre"), ("regles", "Règles"), ("verification", "Vérification")]
        return [e for e in etapes if e[0] != "perimetre" or len(perimetres) > 1]

    def _valeurs_initiales(self, request, perimetres):
        """Pré-remplissage : période qui suit la dernière liste, sinon lundi prochain."""
        aujourdhui = timezone.localdate()
        derniere = max(
            (q.date_fin for q in _listes_visibles(Quart, request.user)),
            default=None,
        )
        derniere_garde = max((g.date_fin for g in _listes_visibles(ServiceGarde, request.user)), default=None)
        fins = [d for d in (derniere, derniere_garde) if d and d >= aujourdhui]
        debut = max(fins) + timezone.timedelta(days=1) if fins else aujourdhui + timezone.timedelta(days=7 - aujourdhui.weekday())
        return {
            "type_liste": "creer_service_garde" if request.GET.get("type") == "garde" else "creer_quart",
            "perimetre": perimetres[0]["valeur"] if perimetres else "",
            "date_debut": str(debut),
            "date_fin": str(debut + timezone.timedelta(days=6)),
        }

    def _afficher(self, request, perimetres, etape, valeurs, statut=200):
        etapes = self._etapes(perimetres)
        contexte = {
            "etapes": [libelle for _, libelle in etapes],
            "etape": etape,
            "cle_etape": etapes[etape - 1][0],
            "valeurs": valeurs,
            "perimetres_creation": perimetres,
            "fonctions_quart": FonctionQuartChoice.objects.filter(active=True).order_by("name"),
            "fonctions_service": ServiceFunctionChoice.objects.filter(active=True).order_by("name"),
        }
        if etapes[etape - 1][0] == "verification":
            est_quart = valeurs.get("type_liste") == "creer_quart"
            fonctions = contexte["fonctions_quart" if est_quart else "fonctions_service"]
            ship, service, sector, section = _resoudre_perimetre(valeurs.get("perimetre"))
            contexte["synthese"] = {
                "type": "Quart (rotation de postes)" if est_quart else "Service à quai / garde",
                "perimetre": _libelle_perimetre(ship or service or sector or section),
                "fonction": fonctions.filter(pk=valeurs.get("fonction_quart" if est_quart else "fonction_service") or 0).first(),
                "date_debut": parse_date(valeurs.get("date_debut", "")),
                "date_fin": parse_date(valeurs.get("date_fin", "")),
            }
        return render(request, self.template_name, contexte, status=statut)

    def _controler(self, cle, valeurs, perimetres):
        """Message d'erreur de l'étape, ou None si elle est valide."""
        if cle == "type" and valeurs.get("type_liste") not in ("creer_quart", "creer_service_garde"):
            return "Choisissez le type de liste."
        if cle == "periode":
            debut, fin = parse_date(valeurs.get("date_debut", "")), parse_date(valeurs.get("date_fin", ""))
            if not debut or not fin:
                return "La période (début et fin) est obligatoire."
            if fin < debut:
                return "La fin de période précède le début."
        if cle == "perimetre" and valeurs.get("perimetre") not in {p["valeur"] for p in perimetres}:
            return "Choisissez le périmètre de la liste."
        if cle == "regles":
            champ = "fonction_quart" if valeurs.get("type_liste") == "creer_quart" else "fonction_service"
            if not valeurs.get(champ):
                return "La fonction est obligatoire."
        return None

    def get(self, request):
        perimetres = _perimetres_creation(request.user)
        if not perimetres:
            raise PermissionDenied
        return self._afficher(request, perimetres, 1, self._valeurs_initiales(request, perimetres))

    def post(self, request):
        perimetres = _perimetres_creation(request.user)
        if not perimetres:
            raise PermissionDenied
        if len(perimetres) == 1:
            request.POST = request.POST.copy()
            request.POST["perimetre"] = perimetres[0]["valeur"]
        valeurs = dict(request.POST.items())
        etapes = self._etapes(perimetres)
        try:
            etape = min(max(int(valeurs.get("etape") or 1), 1), len(etapes))
        except ValueError:
            etape = 1
        if valeurs.get("action") == "precedent":
            return self._afficher(request, perimetres, max(etape - 1, 1), valeurs)
        if etape < len(etapes):
            erreur = self._controler(etapes[etape - 1][0], valeurs, perimetres)
            if erreur:
                messages.error(request, erreur)
                return self._afficher(request, perimetres, etape, valeurs, 400)
            return self._afficher(request, perimetres, etape + 1, valeurs)
        for rang, (cle, _) in enumerate(etapes, 1):
            erreur = self._controler(cle, valeurs, perimetres)
            if erreur:
                messages.error(request, erreur)
                return self._afficher(request, perimetres, rang, valeurs, 400)
        return _creer_liste(request, valeurs["type_liste"], "quarts-creer")


def _semaines(liste, creneaux):
    """Planning en grille : semaines (lundi à dimanche) couvrant la période de la
    liste et tous ses créneaux ; chaque jour porte ses créneaux."""
    par_jour = {}
    for c in creneaux:
        par_jour.setdefault(timezone.localtime(c.debut).date(), []).append(c)
    bornes = [liste.date_debut, liste.date_fin, *par_jour]
    debut, fin = min(bornes), max(bornes)
    debut -= timezone.timedelta(days=debut.weekday())
    aujourdhui = timezone.localdate()
    semaines, jour = [], debut
    while jour <= fin:
        semaines.append([
            {
                "date": j, "creneaux": par_jour.get(j, []),
                "dans_periode": liste.date_debut <= j <= liste.date_fin,
                "aujourdhui": j == aujourdhui,
            }
            for j in (jour + timezone.timedelta(days=i) for i in range(7))
        ])
        jour += timezone.timedelta(days=7)
    return semaines


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
        # Un publicateur habilité (peut_publier_liste) doit pouvoir consulter
        # une liste PROPOSEE pour décider de la publier, même s'il n'est pas
        # le chef de liste qui la gère (rôle distinct, cf. docstring de
        # module de quarts/models.py).
        if not peut_gerer and not peut_publier_liste(request.user, liste) and not _peut_lire_liste(request.user, liste):
            return HttpResponseBadRequest("Liste introuvable ou hors de votre périmètre.")
        return render(request, self.template_name, self._contexte(request, liste, peut_gerer))

    def _contexte(self, request, liste, peut_gerer):
        """Contexte de la fiche détail."""
        peut_publier = peut_publier_liste(request.user, liste)
        contexte = {
            "liste": liste,
            "creneaux": liste.creneaux.select_related("marin").all(),
            "peut_gerer": peut_gerer,
            "peut_publier": peut_publier,
            "url_prefix": self.url_prefix,
            "marins_perimetre": (
                User.objects.filter(marins_du_perimetre(liste)).select_related("profile")
                .order_by("username").distinct()
                if peut_gerer else User.objects.none()
            ),
            # Compteur d'équité (Phase 2, tâche Notion « Services/gardes :
            # compteur d'équité par marin ») : uniquement pour les services de
            # garde (pas les quarts, cf. docstring de quarts/services.py), et
            # réservé au chef de liste gérant cette liste — un marin lambda
            # consulte son propre total depuis son tableau de bord personnel
            # (dashboard/tableau_bord_views.py), pas ici.
            "compteurs_equite": (
                compteurs_equite_perimetre(liste) if peut_gerer and isinstance(liste, ServiceGarde) else None
            ),
            # Historique des versions (cf. quarts/models.py::creer_version) :
            # réservé à qui gère ou peut publier la liste, pas ouvert à tout
            # marin lecteur d'une liste publiée (hypothèse de cadrage, cf.
            # docstring de module de quarts/models.py).
            "versions": liste.versions.all() if (peut_gerer or peut_publier) else None,
        }
        date_consultee = parse_date(request.GET.get("le", ""))
        if date_consultee and (peut_gerer or peut_publier):
            contexte["date_consultee"] = date_consultee
            contexte["version_consultee"] = liste.version_a_la_date(date_consultee)
        if isinstance(liste, ServiceGarde) and liste.statut == liste.STATUT_PUBLIEE:
            # Bouton « Proposer un échange » : tours futurs des autres marins
            # de la même liste, et tours déjà engagés dans un échange en cours.
            contexte["tours_echangeables"] = liste.creneaux.select_related("marin").filter(
                marin__isnull=False, debut__gt=timezone.now()
            ).exclude(marin=request.user)
            en_echange = {
                i for paire in EchangeService.objects.filter(statut__in=EchangeService.STATUTS_EN_COURS)
                .values_list("creneau_demandeur_id", "creneau_cible_id") for i in paire
            }
            contexte["creneaux"] = list(contexte["creneaux"])
            for c in contexte["creneaux"]:
                c.en_echange = c.pk in en_echange
                c.peut_echanger = (
                    c.marin_id == request.user.pk and c.debut > timezone.now()
                    and not c.en_echange and bool(contexte["tours_echangeables"])
                )
        if isinstance(liste, ServiceGarde) and peut_gerer:
            contexte["formations_disponibles"] = TrainingCourse.objects.order_by("title")
        contexte.update(self._contexte_vues(request, liste, contexte, peut_gerer))
        return contexte

    def _contexte_vues(self, request, liste, contexte, peut_gerer):
        """Onglets (Planning, Échanges, Équité, Historique, Paramètres), grille, en-tête et échanges de la liste."""
        creneaux = list(contexte["creneaux"])
        est_garde = isinstance(liste, ServiceGarde)
        onglets = [("planning", "Planning")]
        if est_garde:
            onglets.append(("echanges", "Échanges"))
        if contexte["compteurs_equite"] is not None:
            onglets.append(("equite", "Équité"))
        if contexte["versions"] is not None:
            onglets.append(("historique", "Historique"))
        if peut_gerer:
            onglets.append(("parametres", "Paramètres"))
        vue = request.GET.get("vue")
        if vue not in {cle for cle, _ in onglets}:
            vue = "planning"
        non_affectes = sum(1 for c in creneaux if c.marin_id is None)
        # Circuit proposer -> valider -> publier : l'action principale suit l'état de la liste.
        action = None
        if peut_gerer and liste.statut == liste.STATUT_BROUILLON:
            action = {
                "libelle": "Proposer la publication", "icone": "terminee", "formulaire": "form-action",
                "nom": "proposer", "confirmation": "Proposer cette liste pour publication ?",
            }
        elif contexte["peut_publier"] and liste.statut == liste.STATUT_PROPOSEE:
            action = {
                "libelle": "Publier la liste", "icone": "terminee", "formulaire": "form-action",
                "nom": "publier", "confirmation": "Publier cette liste ? Les marins affectés seront notifiés.",
            }
        resultat = {
            "onglets": onglets,
            "vue": vue,
            "badge_etat": "ok" if liste.statut == liste.STATUT_PUBLIEE else "attention",
            "semaines": _semaines(liste, creneaux),
            "indicateurs": [
                {"libelle": "Créneaux", "valeur": len(creneaux)},
                {"libelle": "Non affectés", "valeur": non_affectes, "etat": "attention" if non_affectes else "ok"},
            ],
            "action": action,
        }
        if est_garde and vue == "echanges":
            echanges = [
                e for e in _echanges_visibles(request.user)
                if e.creneau_demandeur.service_garde_id == liste.pk
            ]
            resultat.update(_grouper_echanges(echanges, request.user))
        return resultat

    def post(self, request, pk):
        liste = self._liste(pk)
        if liste is None:
            return HttpResponseBadRequest("Liste introuvable.")
        peut_gerer = peut_gerer_liste(request.user, liste)
        peut_publier = peut_publier_liste(request.user, liste)
        if not peut_gerer and not peut_publier:
            return HttpResponseBadRequest("Liste introuvable ou hors de votre périmètre.")

        action = request.POST.get("action")

        # Publier exige un rôle DISTINCT de celui qui gère/propose la liste
        # (workflow proposer -> valider/publier, cahier des charges §34) :
        # contrôlé séparément, avant la vérification générique peut_gerer
        # ci-dessous, pour qu'un publicateur habilité non désigné chef de
        # liste puisse tout de même publier.
        if action == "publier":
            if not peut_publier:
                return HttpResponseBadRequest(
                    "Vous n'êtes pas habilité à publier cette liste : rôle de publication requis "
                    "(distinct de celui de chef de liste), cf. réglages de sécurité du navire."
                )
            self._publier(request, liste)
            return redirect(f"{self.url_prefix}-detail", pk=liste.pk)

        if not peut_gerer:
            return HttpResponseBadRequest("Liste introuvable ou hors de votre périmètre.")
        if action == "ajouter_creneau":
            self._ajouter_creneau(request, liste)
        elif action == "supprimer_creneau":
            self._supprimer_creneau(request, liste)
        elif action == "regler_echanges" and isinstance(liste, ServiceGarde):
            self._regler_echanges(request, liste)
            return redirect(f"{reverse(f'{self.url_prefix}-detail', args=[liste.pk])}?vue=parametres")
        elif action == "proposer":
            self._proposer(request, liste)
        else:
            return HttpResponseBadRequest("Action inconnue.")
        return redirect(f"{self.url_prefix}-detail", pk=liste.pk)

    def _proposer(self, request, liste):
        """BROUILLON -> PROPOSEE : réservé au chef de liste (peut_gerer),
        cf. docstring de module de quarts/models.py."""
        if liste.statut != liste.STATUT_BROUILLON:
            messages.error(request, "Seul un brouillon peut être proposé à la publication.")
            return
        liste.proposer(request.user)
        messages.success(
            request, "Liste proposée à la publication : un publicateur habilité doit maintenant la valider."
        )

    def _publier(self, request, liste):
        """PROPOSEE (ou déjà PUBLIEE, pour une republication après
        correction) -> PUBLIEE. La toute première publication doit
        obligatoirement transiter par l'étape Proposée (CLAUDE.md §2 : ne
        pas imposer ce détour pour une simple correction ultérieure)."""
        if liste.statut == liste.STATUT_BROUILLON:
            messages.error(request, "Proposez d'abord la liste avant de pouvoir la publier.")
            return
        liste.publier(request.user)
        messages.success(request, "Liste publiée : les marins affectés ont été notifiés.")

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
            marin = User.objects.filter(marins_du_perimetre(liste), pk=marin_id).distinct().first()
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
        if self.fk_attr == "service_garde":
            annuler_echanges_du_creneau(creneau, request.user)
        creneau.delete()
        messages.info(request, "Créneau supprimé.")

    def _regler_echanges(self, request, liste):
        """Règles des échanges de tour propres à cette liste (configurables,
        CLAUDE.md §6) : habilitations exigées et délai minimal de demande."""
        try:
            delai = int(request.POST.get("delai_minimal_echange_heures") or 0)
        except ValueError:
            delai = -1
        if delai < 0:
            messages.error(request, "Le délai minimal doit être un nombre d'heures positif ou nul.")
            return
        liste.delai_minimal_echange_heures = delai
        liste.save(update_fields=["delai_minimal_echange_heures", "updated_at"])
        liste.formations_requises.set(TrainingCourse.objects.filter(pk__in=request.POST.getlist("formations_requises")))
        messages.success(request, "Règles d'échange enregistrées.")


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
            ).filter(equipage_marin_q(request.user, "user__profile__")).order_by("user__username"),
            "perimetres_disponibles": _perimetres_org_disponibles(
                request.user, borne_par_scope=user_role_level(request.user) < NIVEAU_SUPERVISION_GLOBALE_LISTE
            ),
            "utilisateurs": User.objects.filter(equipage_marin_q(request.user), is_active=True).order_by("username"),
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
            candidat = User.objects.filter(equipage_marin_q(request.user), pk=request.POST.get("user_id")).first()
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
            cdl = ChefDeListe.objects.filter(equipage_marin_q(request.user, "user__profile__"), pk=request.POST.get("pk")).first()
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
