"""Feuille de service quotidienne (quarts/web_views.py).

Sous-domaine extrait lors du découpage du fichier (tâche Notion « [ARCH]
Découper quarts/web_views.py (1086 lignes) par sous-domaine »,
quarts/web_views.py ayant dépassé 800 lignes) : consultation, rédaction,
circuit de visa à 3 paliers et publication de la feuille de service
quotidienne (tâche Notion « Feuille de service quotidienne — personnel de
service et en-tête (à quai) »). Cf. quarts/models.py pour le détail du
workflow et des choix de conception (correspondance fonction <-> poste,
approximation du visa COMAEQ, versionnage propre).

Refactor pur : reproduit exactement le comportement d'origine."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View

from accounts.models import AuditLog
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from matrix.core.saisie import entier_ou_none
from matrix.core.scopes import ship_id_for_user
from org.models import Ship

from .alertes import etat_alertes, peut_proposer_organisation_alerte, peut_valider_organisation_alerte
from .models import (
    FeuilleService,
    FonctionFeuilleService,
    NIVEAU_SUPERVISION_GLOBALE_LISTE,
    RubriqueEnTeteFeuilleService,
    equipage_de_feuille_pour,
    feuille_du_jour,
    peut_gerer_brouillon_feuille,
    peut_lire_feuille_service,
    peut_rediger_feuille_service,
    peut_viser_comaeq,
    peut_viser_secteur,
    peut_viser_service,
    personnel_du_jour,
)


def _navires_disponibles_feuille_service(user):
    """Navires que `user` peut consulter/rédiger en feuille de service : le
    sien (ou toute la flotte pour la supervision globale) — la feuille de
    service n'a de sens qu'à l'échelle du bâtiment entier, contrairement aux
    listes de quarts/gardes qui peuvent être bornées à un secteur/service."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_LISTE:
        return Ship.objects.all()
    ship_id = ship_id_for_user(user)
    return Ship.objects.filter(pk=ship_id) if ship_id else Ship.objects.none()


def _redirection_detail(ship, date_, equipage):
    """Retour sur la feuille du jour ; l'équipage n'est passé dans l'adresse que
    s'il y en a un (administrateur général choisissant l'équipage à consulter)."""
    adresse = reverse("feuille-service-detail", kwargs={"ship_id": ship.pk, "date_str": date_.isoformat()})
    return redirect(f"{adresse}?equipage={equipage.pk}" if equipage else adresse)


class FeuilleServiceIndexView(LoginRequiredMixin, View):
    """Point d'entrée du module : redirige vers la feuille du jour du navire
    de l'utilisateur."""

    def get(self, request):
        navire = _navires_disponibles_feuille_service(request.user).first()
        if navire is None:
            messages.error(request, "Aucune unité n'est associée à votre profil.")
            return redirect("home")
        return redirect(
            "feuille-service-detail", ship_id=navire.pk, date_str=timezone.localdate().isoformat()
        )


class FeuilleServiceDetailView(LoginRequiredMixin, View):
    """Fiche du jour (ou d'un autre jour, pour préparer à l'avance) : en-tête
    + personnel de service calculé automatiquement depuis les tours publiés,
    et actions du circuit de visa (proposer/viser/renvoyer), cf.
    quarts/models.py::FeuilleService."""

    template_name = "quarts/feuille_service_detail.html"

    def _charger(self, request, ship_id, date_str):
        ship = get_object_or_404(Ship, pk=ship_id)
        date_ = parse_date(date_str)
        # Double équipage : une feuille par équipage, celle de l'équipage de l'appelant.
        equipage = equipage_de_feuille_pour(request.user, ship, request.GET.get("equipage"))
        feuille = None
        if date_ is not None:
            feuille = feuille_du_jour(ship, date_, equipage)
            if feuille is not None:
                feuille = FeuilleService.objects.select_related(
                    "secteur_redacteur", "service_redacteur", "created_by", "equipage",
                ).get(pk=feuille.pk)
        return ship, date_, feuille, equipage

    def get(self, request, ship_id, date_str):
        ship, date_, feuille, equipage = self._charger(request, ship_id, date_str)
        if date_ is None:
            return HttpResponseBadRequest("Date invalide.")
        if feuille is not None and not peut_lire_feuille_service(request.user, feuille):
            raise PermissionDenied
        return render(request, self.template_name, self._contexte(request, ship, date_, feuille, equipage))

    def _peut_configurer(self, request):
        return user_role_level(request.user) >= niveau_requis_pour(request.user, "feuille_service_configuration")

    def _rattacher_feuille(self, request, ship):
        """Rattache une feuille historique sans équipage à un équipage du
        bâtiment (double équipage), pour qu'elle reste retrouvable ; tracé dans l'AuditLog."""
        if not self._peut_configurer(request):
            raise PermissionDenied
        feuille = FeuilleService.objects.filter(
            pk=entier_ou_none(request.POST.get("feuille_id")) or 0, ship=ship, equipage__isnull=True
        ).first()
        equipage = ship.equipages.filter(pk=entier_ou_none(request.POST.get("equipage_id")) or 0).first()
        if not ship.double_equipage or feuille is None or equipage is None:
            messages.error(request, "Feuille sans équipage ou équipage introuvable sur cette unité.")
        elif FeuilleService.objects.filter(ship=ship, equipage=equipage, date=feuille.date).exists():
            messages.error(
                request,
                f"L'équipage {equipage.nom} a déjà une feuille de service au {feuille.date:%d/%m/%Y} : "
                "rattachez cette feuille à l'autre équipage.",
            )
        else:
            feuille.equipage = equipage
            feuille.save(update_fields=["equipage", "updated_at"])
            AuditLog.objects.create(
                actor=request.user, action="rattacher_feuille_service",
                details=f"navire={ship.name}; feuille du {feuille.date.isoformat()} (pk={feuille.pk}); "
                        f"sans équipage -> {equipage.nom}",
            )
            messages.success(request, f"Feuille du {feuille.date:%d/%m/%Y} rattachée à l'équipage {equipage.nom}.")

    def _contexte(self, request, ship, date_, feuille, equipage):
        peut_configurer = self._peut_configurer(request)
        # Feuilles à ne pas perdre de vue : sans équipage sur un double équipage
        # (à rattacher), ou d'un autre équipage le même jour sur un équipage unique.
        if ship.double_equipage:
            feuilles_sans_equipage = FeuilleService.objects.filter(ship=ship, equipage__isnull=True).order_by("-date")[:30]
            autres_feuilles = []
        else:
            feuilles_sans_equipage = []
            autres_feuilles = FeuilleService.objects.filter(
                ship=ship, date=date_, equipage__isnull=False
            ).exclude(pk=feuille.pk if feuille else 0).select_related("equipage")
        if feuille is not None:
            rubriques = feuille.rubriques_affichees
            personnel = feuille.personnel
        else:
            rubriques = [
                {"rubrique": r, "valeur": r.valeur_fixe if r.type_saisie == r.TYPE_FIXE else ""}
                for r in RubriqueEnTeteFeuilleService.objects.filter(ship=ship, actif=True)
            ]
            personnel = personnel_du_jour(ship, date_, equipage)
        je_suis_de_service = any(
            e["creneau"] and e["creneau"].marin_id == request.user.pk for e in personnel
        )
        return {
            "ship": ship,
            "equipage": equipage,
            "date": date_,
            "veille": date_ - timezone.timedelta(days=1),
            "lendemain": date_ + timezone.timedelta(days=1),
            "aujourdhui": timezone.localdate(),
            "feuille": feuille,
            "rubriques": rubriques,
            "personnel": personnel,
            "je_suis_de_service": je_suis_de_service,
            "peut_rediger": peut_rediger_feuille_service(request.user, ship),
            "peut_gerer_brouillon": feuille is not None and peut_gerer_brouillon_feuille(request.user, feuille),
            "peut_viser_secteur": (
                feuille is not None and feuille.statut == FeuilleService.STATUT_VISA_SECTEUR
                and peut_viser_secteur(request.user, feuille)
            ),
            "peut_viser_service": (
                feuille is not None and feuille.statut == FeuilleService.STATUT_VISA_SERVICE
                and peut_viser_service(request.user, feuille)
            ),
            "peut_viser_comaeq": (
                feuille is not None and feuille.statut == FeuilleService.STATUT_VISA_COMAEQ
                and peut_viser_comaeq(request.user, feuille)
            ),
            "alertes": etat_alertes(ship, date_, equipage),
            "peut_gerer_alertes": (
                peut_proposer_organisation_alerte(request.user, ship)
                or peut_valider_organisation_alerte(request.user, ship)
            ),
            "versions": feuille.versions.all() if feuille is not None else None,
            "peut_configurer": peut_configurer,
            # Double équipage sans équipage à bord défini : rien n'est affiché
            # au hasard, l'écran demande de corriger la configuration.
            "etat_incoherent": ship.double_equipage and equipage is None,
            "feuilles_sans_equipage": feuilles_sans_equipage,
            "equipages_rattachement": ship.equipages.all() if ship.double_equipage else [],
            "autres_feuilles": autres_feuilles,
        }

    def post(self, request, ship_id, date_str):
        ship, date_, feuille, equipage = self._charger(request, ship_id, date_str)
        if date_ is None:
            return HttpResponseBadRequest("Date invalide.")
        action = request.POST.get("action")

        if action == "rattacher_feuille":
            self._rattacher_feuille(request, ship)
            return _redirection_detail(ship, date_, equipage)
        if ship.double_equipage and equipage is None:
            messages.error(
                request, "Aucun équipage à bord n'est défini : corrigez-le d'abord dans la page « Équipages »."
            )
            return _redirection_detail(ship, date_, equipage)

        if action == "creer":
            if not peut_rediger_feuille_service(request.user, ship):
                raise PermissionDenied
            if feuille is None:
                FeuilleService.objects.create(
                    ship=ship, equipage=equipage if ship.double_equipage else None, date=date_,
                    created_by=request.user, updated_by=request.user,
                )
                messages.success(
                    request, "Brouillon créé : complétez l'en-tête puis proposez-le à la validation."
                )
            return _redirection_detail(ship, date_, equipage)

        if feuille is None:
            return HttpResponseBadRequest("Feuille introuvable : créez-la d'abord.")

        if action == "enregistrer_entete":
            if not peut_gerer_brouillon_feuille(request.user, feuille):
                raise PermissionDenied
            valeurs = dict(feuille.valeurs_entete)
            for rubrique in RubriqueEnTeteFeuilleService.objects.filter(
                ship=ship, type_saisie=RubriqueEnTeteFeuilleService.TYPE_QUOTIDIENNE
            ):
                cle = f"rubrique_{rubrique.pk}"
                if cle in request.POST:
                    valeurs[str(rubrique.pk)] = request.POST.get(cle, "").strip()
            feuille.valeurs_entete = valeurs
            feuille.updated_by = request.user
            feuille.save(update_fields=["valeurs_entete", "updated_by", "updated_at"])
            messages.success(request, "En-tête enregistré.")
        elif action == "proposer":
            if feuille.statut != FeuilleService.STATUT_BROUILLON or not peut_gerer_brouillon_feuille(
                request.user, feuille
            ):
                raise PermissionDenied
            feuille.proposer(request.user)
            messages.success(request, "Feuille proposée à la validation.")
        elif action == "viser_secteur":
            if feuille.statut != FeuilleService.STATUT_VISA_SECTEUR or not peut_viser_secteur(request.user, feuille):
                raise PermissionDenied
            feuille.viser_secteur(request.user)
            messages.success(request, "Visa du chef de secteur enregistré.")
        elif action == "viser_service":
            if feuille.statut != FeuilleService.STATUT_VISA_SERVICE or not peut_viser_service(request.user, feuille):
                raise PermissionDenied
            feuille.viser_service(request.user)
            messages.success(request, "Visa du chef de service enregistré.")
        elif action == "viser_comaeq":
            if feuille.statut != FeuilleService.STATUT_VISA_COMAEQ or not peut_viser_comaeq(request.user, feuille):
                raise PermissionDenied
            feuille.viser_comaeq(request.user)
            messages.success(
                request, "Feuille visée par le COMAEQ et publiée : la fraction de service a été notifiée."
            )
        elif action == "renvoyer":
            verificateur = {
                FeuilleService.STATUT_VISA_SECTEUR: peut_viser_secteur,
                FeuilleService.STATUT_VISA_SERVICE: peut_viser_service,
                FeuilleService.STATUT_VISA_COMAEQ: peut_viser_comaeq,
            }.get(feuille.statut)
            if verificateur is None or not verificateur(request.user, feuille):
                raise PermissionDenied
            motif = request.POST.get("motif", "").strip()
            if not motif:
                messages.error(request, "Un motif est obligatoire pour renvoyer la feuille en brouillon.")
                return _redirection_detail(ship, date_, equipage)
            feuille.renvoyer(request.user, motif)
            messages.info(request, "Feuille renvoyée en brouillon pour correction.")
        else:
            return HttpResponseBadRequest("Action inconnue.")
        return _redirection_detail(ship, date_, equipage)


class FeuilleServiceReglagesView(LoginRequiredMixin, View):
    """Configuration par navire des rubriques d'en-tête et des fonctions de
    service (CLAUDE.md §6 : rien n'est codé en dur), en saisie groupée façon
    tableur : toutes les lignes existantes sont ré-enregistrées en un seul
    clic, une ligne « nouvelle rubrique/fonction » permet d'en ajouter une."""

    template_name = "quarts/feuille_service_reglages.html"

    def _ship(self, request):
        pk = request.GET.get("ship") or request.POST.get("ship")
        return get_object_or_404(_navires_disponibles_feuille_service(request.user), pk=pk)

    def _verifier_habilitation(self, request):
        if user_role_level(request.user) < niveau_requis_pour(request.user, "feuille_service_configuration"):
            raise PermissionDenied

    def get(self, request):
        self._verifier_habilitation(request)
        ship = self._ship(request)
        return render(request, self.template_name, {
            "ship": ship,
            "navires": _navires_disponibles_feuille_service(request.user),
            "rubriques": RubriqueEnTeteFeuilleService.objects.filter(ship=ship),
            "fonctions": FonctionFeuilleService.objects.filter(ship=ship),
        })

    def post(self, request):
        self._verifier_habilitation(request)
        ship = self._ship(request)
        action = request.POST.get("action")
        if action == "enregistrer_rubriques":
            self._enregistrer_rubriques(request, ship)
        elif action == "enregistrer_fonctions":
            self._enregistrer_fonctions(request, ship)
        elif action == "supprimer_rubrique":
            RubriqueEnTeteFeuilleService.objects.filter(pk=request.POST.get("pk"), ship=ship).delete()
            messages.info(request, "Rubrique supprimée.")
        elif action == "supprimer_fonction":
            FonctionFeuilleService.objects.filter(pk=request.POST.get("pk"), ship=ship).delete()
            messages.info(request, "Fonction supprimée.")
        else:
            return HttpResponseBadRequest("Action inconnue.")
        return redirect(f"{reverse('feuille-service-reglages')}?ship={ship.pk}")

    def _enregistrer_rubriques(self, request, ship):
        for rubrique in RubriqueEnTeteFeuilleService.objects.filter(ship=ship):
            prefixe = f"rubrique_{rubrique.pk}_"
            if f"{prefixe}libelle" not in request.POST:
                continue
            rubrique.libelle = request.POST.get(f"{prefixe}libelle", rubrique.libelle).strip()
            rubrique.ordre = int(request.POST.get(f"{prefixe}ordre") or rubrique.ordre)
            rubrique.type_saisie = request.POST.get(f"{prefixe}type_saisie", rubrique.type_saisie)
            rubrique.valeur_fixe = request.POST.get(f"{prefixe}valeur_fixe", "").strip()
            rubrique.actif = f"{prefixe}actif" in request.POST
            rubrique.save()
        nouveau_libelle = request.POST.get("nouvelle_rubrique_libelle", "").strip()
        if nouveau_libelle:
            RubriqueEnTeteFeuilleService.objects.create(
                ship=ship, libelle=nouveau_libelle,
                ordre=int(request.POST.get("nouvelle_rubrique_ordre") or 0),
                type_saisie=request.POST.get(
                    "nouvelle_rubrique_type_saisie", RubriqueEnTeteFeuilleService.TYPE_QUOTIDIENNE
                ),
                valeur_fixe=request.POST.get("nouvelle_rubrique_valeur_fixe", "").strip(),
            )
        messages.success(request, "Rubriques d'en-tête enregistrées.")

    def _enregistrer_fonctions(self, request, ship):
        for fonction in FonctionFeuilleService.objects.filter(ship=ship):
            prefixe = f"fonction_{fonction.pk}_"
            if f"{prefixe}libelle" not in request.POST:
                continue
            fonction.libelle = request.POST.get(f"{prefixe}libelle", fonction.libelle).strip()
            fonction.ordre = int(request.POST.get(f"{prefixe}ordre") or fonction.ordre)
            fonction.poste_recherche = request.POST.get(f"{prefixe}poste_recherche", "").strip()
            fonction.actif = f"{prefixe}actif" in request.POST
            fonction.save()
        nouveau_libelle = request.POST.get("nouvelle_fonction_libelle", "").strip()
        if nouveau_libelle:
            FonctionFeuilleService.objects.create(
                ship=ship, libelle=nouveau_libelle,
                ordre=int(request.POST.get("nouvelle_fonction_ordre") or 0),
                poste_recherche=request.POST.get("nouvelle_fonction_poste_recherche", "").strip(),
            )
        messages.success(request, "Fonctions de service enregistrées.")
