"""Dashboards transverses par spécialité et par classe de navire
(dashboard/web_views.py).

Sous-domaine extrait lors du découpage du fichier (tâche Notion « [ARCH]
Découper dashboard/web_views.py (1063 lignes) par sous-domaine »,
dashboard/web_views.py ayant dépassé 800 lignes) :

Deux rôles transverses désormais possibles (accounts.ResponsableSpecialite,
org.ResponsableClasseNavire), indépendants de la hiérarchie Navire →
Service → Secteur → Section : un marin peut être désigné responsable
d'UNE spécialité ou d'UNE classe de navire pour TOUTE LA FLOTTE, sans que
cela ne change son rôle hiérarchique habituel. La désignation reste
réservée à MASTER_ADMIN (matrix/core/role_thresholds.py, onglet
« Référentiels globaux » des Réglages) ; la consultation des deux
dashboards ci-dessous est réservée au(x) responsable(s) désigné(s) pour
l'objet consulté, ou à MASTER_ADMIN (supervision globale de la flotte,
même principe que is_master_admin ailleurs dans ce module).

Contenu volontairement différent entre les deux dashboards, cohérent avec
le cadrage métier du 12/09/2026 :
- Spécialité : combine une vue RH (marins qui l'exercent, répartition par
  unité, qualifications/formations associées) ET une vue technique
  (maintenances/tickets correctifs assignés à ces marins, toute la flotte).
- Classe de navire : comparatif de DISPONIBILITÉ OPÉRATIONNELLE entre les
  navires de la classe (taux de pannes, maintenance en retard, installations
  critiques hors service) — PAS l'équité des quarts/gardes (hors périmètre
  de ce dashboard, couverte par le module quarts). Même agrégation que
  VueFlotteView pour les totaux de la classe (dashboard/vue_flotte_views.py
  ::_agrege_maintenance_ticket_stock), étendue à plusieurs navires,
  complétée par un comparatif PAR NAVIRE (_disponibilite_par_navire).

Refactor pur : reproduit exactement le comportement d'origine."""
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from accounts.models import ResponsableSpecialite, SpecialityChoice
from assets.models import Asset, Installation
from logistics.models import CorrectiveTicket, STATUTS_TICKET_OUVERTS
from maintenance.models import MaintenanceOccurrence
from matrix.core.scopes import is_master_admin
from org.models import ResponsableClasseNavire, Ship
from training.services import qualifications_validees_de

from .vue_flotte_views import _agrege_maintenance_ticket_stock
from .web_views import _STATUTS_MAINTENANCE_TERMINES

User = get_user_model()


def _specialites_responsable_de(user):
    """Spécialités (accounts.SpecialityChoice) pour lesquelles `user` est
    désigné responsable transverse — ou l'ensemble des spécialités actives
    pour un MASTER_ADMIN (supervision globale de la flotte)."""
    if is_master_admin(user):
        return SpecialityChoice.objects.filter(active=True).order_by("name")
    return (
        SpecialityChoice.objects.filter(responsables__user=user)
        .distinct()
        .order_by("name")
    )


def _classes_navire_responsable_de(user):
    """Classes de navire (valeurs libres de org.Ship.classe_navire) pour
    lesquelles `user` est désigné responsable transverse — ou l'ensemble des
    classes existant dans la flotte pour un MASTER_ADMIN."""
    if is_master_admin(user):
        return list(
            Ship.objects.exclude(classe_navire="")
            .values_list("classe_navire", flat=True)
            .distinct()
            .order_by("classe_navire")
        )
    return list(
        ResponsableClasseNavire.objects.filter(user=user)
        .values_list("classe_navire", flat=True)
        .distinct()
        .order_by("classe_navire")
    )


def _agrege_technique_marins(marins_ids):
    """Vue TECHNIQUE d'un dashboard spécialité (cadrage du 12/09/2026, point 2) :
    maintenances et tickets correctifs assignés aux marins de cette spécialité,
    sur toute la flotte. Aucun lien direct n'existe en base entre une spécialité
    (accounts.SpecialityChoice) et une installation/un matériel : le seul lien
    disponible est la PERSONNE assignée (MaintenanceOccurrence.assignees /
    CorrectiveTicket.assignees), déjà utilisée par « Mes maintenances »/« Mes
    tickets » sur le tableau de bord personnel (dashboard/tableau_bord_views.py
    ::TableauDeBordView).

    Le stock (StockPiece) n'a pas de notion d'assigné : il n'entre pas dans
    cette vue par spécialité, à la différence de la Vue flotte et du dashboard
    classe de navire, tous deux scopés par navire/secteur/section."""
    occurrences = MaintenanceOccurrence.objects.filter(assignees__id__in=marins_ids).distinct()
    maintenances_en_retard = occurrences.filter(status="OVERDUE").count()
    total_actives = occurrences.exclude(status__in=_STATUTS_MAINTENANCE_TERMINES).count()
    maintenances_en_retard_pct = (
        round(maintenances_en_retard / total_actives * 100) if total_actives else 0
    )

    # Même pattern que _agrege_maintenance_ticket_stock (vue_flotte_views.py) :
    # une requête agrégée par statut, avec Count(distinct=True) car le filtre
    # sur assignees (M2M) peut dupliquer les lignes d'un ticket ayant plusieurs
    # assignés.
    totaux_par_statut = dict(
        CorrectiveTicket.objects.filter(assignees__id__in=marins_ids, status__in=STATUTS_TICKET_OUVERTS)
        .values("status")
        .annotate(total=Count("id", distinct=True))
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
    total_tickets_ouverts = sum(t["total"] for t in tickets_par_statut)

    return {
        "technique_maintenances_en_retard": maintenances_en_retard,
        "technique_maintenances_en_retard_pct": maintenances_en_retard_pct,
        "technique_tickets_par_statut": tickets_par_statut,
        "technique_total_tickets_ouverts": total_tickets_ouverts,
        "technique_tickets_chart_labels_json": json.dumps([t["libelle"] for t in tickets_par_statut]),
        "technique_tickets_chart_values_json": json.dumps([t["total"] for t in tickets_par_statut]),
    }


def _disponibilite_par_navire(navires):
    """Comparatif de disponibilité opérationnelle entre les navires d'une classe
    (cadrage du 12/09/2026, point 3) : taux de pannes, maintenance en retard,
    installations critiques hors service — PAS l'équité des quarts/gardes
    (couverte ailleurs, module quarts). Un tableau/graphique PAR NAVIRE, pas un
    total agrégé de la classe : c'est le comparatif lui-même qui est la donnée
    utile pour un responsable de classe.

    Installation ne porte aucun champ de statut « hors service » en base
    (contrairement à Asset.status) : une installation critique dont au moins
    une échéance de maintenance est en retard est prise comme signal de
    substitution raisonnable d'indisponibilité opérationnelle, à défaut d'un
    statut explicite sur le modèle."""
    comparatif = []
    for navire in navires:
        filtre_occurrence = Q(asset__ship_id=navire.id) | Q(
            installation_maintenance__installation__ship_id=navire.id
        )
        occurrences = MaintenanceOccurrence.objects.filter(filtre_occurrence)
        maintenances_en_retard = occurrences.filter(status="OVERDUE").count()
        total_actives = occurrences.exclude(status__in=_STATUTS_MAINTENANCE_TERMINES).count()
        maintenances_en_retard_pct = (
            round(maintenances_en_retard / total_actives * 100) if total_actives else 0
        )

        # Taux de pannes : proportion du matériel mobile du navire ayant
        # actuellement un ticket correctif ouvert (même liste de statuts
        # ouverts que le reste des dashboards, STATUTS_TICKET_OUVERTS).
        total_assets = Asset.objects.filter(ship_id=navire.id).count()
        tickets_ouverts = CorrectiveTicket.objects.filter(
            asset__ship_id=navire.id, status__in=STATUTS_TICKET_OUVERTS
        ).count()
        taux_pannes_pct = round(tickets_ouverts / total_assets * 100) if total_assets else 0

        installations_critiques = Installation.objects.filter(ship_id=navire.id, critique=True)
        installations_critiques_hors_service = (
            installations_critiques.filter(maintenances__occurrences__status="OVERDUE").distinct().count()
        )

        comparatif.append({
            "navire": navire,
            "maintenances_en_retard": maintenances_en_retard,
            "maintenances_en_retard_pct": maintenances_en_retard_pct,
            "tickets_ouverts": tickets_ouverts,
            "taux_pannes_pct": taux_pannes_pct,
            "installations_critiques_total": installations_critiques.count(),
            "installations_critiques_hors_service": installations_critiques_hors_service,
        })
    return comparatif


class DashboardSpecialiteChoixView(LoginRequiredMixin, View):
    """Point d'entrée du dashboard spécialité : redirige directement vers
    l'unique spécialité accessible (principe n°2 CLAUDE.md — pas de clic
    superflu), ou propose un choix si plusieurs le sont (référent de
    plusieurs spécialités, ou MASTER_ADMIN)."""

    def get(self, request):
        specialites = list(_specialites_responsable_de(request.user))
        if not specialites:
            raise PermissionDenied("Aucune spécialité transverse ne vous est confiée.")
        if len(specialites) == 1:
            return redirect("dashboard-specialite", pk=specialites[0].pk)
        return render(request, "dashboard/choix_specialite.html", {"specialites": specialites})


class DashboardSpecialiteView(LoginRequiredMixin, TemplateView):
    """Dashboard transverse d'une spécialité, agrégé sur TOUTE LA FLOTTE :
    répartition des marins de cette spécialité par navire, et vue d'ensemble
    de leurs qualifications (formations) — réservé au(x) responsable(s)
    désigné(s) de cette spécialité précise, ou à MASTER_ADMIN."""

    template_name = "dashboard/specialite.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        specialite = get_object_or_404(SpecialityChoice, pk=kwargs["pk"])
        user = self.request.user
        autorise = is_master_admin(user) or ResponsableSpecialite.objects.filter(
            specialite=specialite, user=user
        ).exists()
        if not autorise:
            raise PermissionDenied("Cette spécialité ne vous est pas confiée.")

        # profile.specialite est un texte libre alimenté par le référentiel
        # SpecialityChoice (accounts/web_views.py, formulaires de l'annuaire) :
        # comparaison directe au nom, sans FK (le champ historique n'a jamais
        # été une FK, cf. accounts/models.py::UserProfile.specialite).
        marins = list(
            User.objects.filter(profile__specialite=specialite.name)
            .select_related("profile", "profile__ship", "profile__service")
            .order_by("profile__ship__name", "last_name", "first_name", "username")
        )

        contexte["specialite"] = specialite
        contexte["marins"] = marins
        contexte["total_marins"] = len(marins)

        # Vue technique (cadrage 12/09/2026, point 2) : maintenances/tickets
        # correctifs assignés aux marins de cette spécialité, toute la flotte.
        contexte.update(_agrege_technique_marins([marin.id for marin in marins]))

        # Répartition par navire (principe n°5 CLAUDE.md : un graphique plutôt
        # qu'une colonne de chiffres).
        par_navire = {}
        for marin in marins:
            navire = getattr(marin.profile, "ship", None)
            cle = navire.name if navire else "Sans unité"
            par_navire[cle] = par_navire.get(cle, 0) + 1
        contexte["nombre_navires"] = len(
            {marin.profile.ship_id for marin in marins if getattr(marin.profile, "ship_id", None)}
        )
        contexte["repartition_navire_labels_json"] = json.dumps(list(par_navire.keys()))
        contexte["repartition_navire_values_json"] = json.dumps(list(par_navire.values()))

        # Qualifications (formations) de ces marins : réutilise telle quelle
        # training.services.qualifications_validees_de (même badge à
        # jour/bientôt expirée/expirée que « Mes qualifications »), agrégée
        # marin par marin pour donner une vue d'ensemble transverse — aucune
        # nouvelle règle métier de validité introduite ici.
        compteur_badges = {"À jour": 0, "Bientôt expirée": 0, "Expirée": 0}
        for marin in marins:
            for qualification in qualifications_validees_de(marin):
                compteur_badges[qualification.badge_libelle] = (
                    compteur_badges.get(qualification.badge_libelle, 0) + 1
                )
        contexte["qualifications_par_statut"] = compteur_badges
        contexte["qualifications_chart_labels_json"] = json.dumps(list(compteur_badges.keys()))
        contexte["qualifications_chart_values_json"] = json.dumps(list(compteur_badges.values()))
        return contexte


class DashboardClasseNavireChoixView(LoginRequiredMixin, View):
    """Point d'entrée du dashboard classe de navire — même principe de
    redirection directe que DashboardSpecialiteChoixView ci-dessus."""

    def get(self, request):
        classes = _classes_navire_responsable_de(request.user)
        if not classes:
            raise PermissionDenied("Aucune classe de navire transverse ne vous est confiée.")
        if len(classes) == 1:
            return redirect("dashboard-classe-navire", classe=classes[0])
        return render(request, "dashboard/choix_classe_navire.html", {"classes": classes})


class DashboardClasseNavireView(LoginRequiredMixin, TemplateView):
    """Dashboard transverse d'une classe de navire, agrégé sur TOUS LES
    NAVIRES de cette classe : maintenances en retard, tickets correctifs
    ouverts, pièces de stock sous seuil — même agrégation que VueFlotteView
    (_agrege_maintenance_ticket_stock), simplement étendue à plusieurs
    navires au lieu d'un seul. Réservé au(x) responsable(s) désigné(s) de
    cette classe, ou à MASTER_ADMIN."""

    template_name = "dashboard/classe_navire.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        classe = kwargs["classe"]
        user = self.request.user
        autorise = is_master_admin(user) or ResponsableClasseNavire.objects.filter(
            classe_navire=classe, user=user
        ).exists()
        if not autorise:
            raise PermissionDenied("Cette classe de navire ne vous est pas confiée.")

        navires = list(Ship.objects.filter(classe_navire=classe).order_by("name"))
        if not navires:
            raise Http404("Aucune unité de cette classe de navire.")
        ship_ids = [navire.id for navire in navires]

        contexte["classe_navire"] = classe
        contexte["navires"] = navires

        filtre_occurrence = Q(asset__ship_id__in=ship_ids) | Q(
            installation_maintenance__installation__ship_id__in=ship_ids
        )
        filtre_ticket = Q(asset__ship_id__in=ship_ids) | Q(installation__ship_id__in=ship_ids)
        filtre_stock = Q(ship_id__in=ship_ids)
        contexte.update(_agrege_maintenance_ticket_stock(filtre_occurrence, filtre_ticket, filtre_stock))

        # Comparatif de disponibilité opérationnelle PAR NAVIRE (cadrage
        # 12/09/2026, point 3) : le cœur de ce dashboard pour un responsable de
        # classe, en complément des totaux agrégés ci-dessus.
        comparatif = _disponibilite_par_navire(navires)
        contexte["comparatif_navires"] = comparatif
        contexte["comparatif_chart_labels_json"] = json.dumps([r["navire"].name for r in comparatif])
        contexte["comparatif_taux_pannes_json"] = json.dumps([r["taux_pannes_pct"] for r in comparatif])
        contexte["comparatif_maintenance_retard_json"] = json.dumps(
            [r["maintenances_en_retard_pct"] for r in comparatif]
        )
        contexte["comparatif_installations_hors_service_json"] = json.dumps(
            [r["installations_critiques_hors_service"] for r in comparatif]
        )
        return contexte
