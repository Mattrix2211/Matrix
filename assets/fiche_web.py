"""Écrans de la fiche de maintenance d'une installation : consultation, assistant de rédaction, visas."""
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from logistics.models import StockPiece
from matrix.core.mixins import build_scope_q
from matrix.core.saisie import entier_ou_none
from threads.utils import ajouter_commentaire, contexte_discussion
from training.models import TrainingCourse

from . import fiche_maintenance, fiche_validation as validation
from .mesures import formater_heures, heures_depuis_visite_maintenance
from .models import (
    ChecklistTemplate, FichePreparation, Installation, InstallationHourReading, InstallationMaintenance, ModeDeclenchement,
)
from .proposition_article import ErreurCircuit

Etat = ChecklistTemplate.Etat
BADGES = {Etat.VALIDEE: "ok", Etat.REFUSEE: "danger"}


def _fiche(request, pk):
    """Fiche d'une installation visible par l'utilisateur ; sinon 404 (jamais d'indice hors périmètre)."""
    return get_object_or_404(
        InstallationMaintenance.objects.filter(installation__isnull=False)
        .filter(build_scope_q(request.user, "installation__")).select_related("installation__service", "installation__ship"), pk=pk)


def _installation(request, pk):
    try:
        pk = uuid.UUID(str(pk))
    except ValueError:
        raise Http404("Installation introuvable")
    return get_object_or_404(Installation.objects.filter(build_scope_q(request.user, "")), pk=pk)


def _nombre(texte):
    """Entier lu dans un champ de formulaire, None si vide ou illisible."""
    return entier_ou_none((texte or "").strip().replace(" ", "").replace(" ", ""))


def _flottant(texte):
    texte = (texte or "").strip().replace(",", ".")
    try:
        return float(texte) if texte else None
    except ValueError:
        return None


def lire_formulaire(post):
    """Contenu d'une version lu dans le formulaire de l'assistant (les lignes vides sont ignorées)."""
    mode = post.get("mode_declenchement")
    contenu = {
        "name": post.get("name", "").strip(), "description": post.get("description", "").strip(),
        "resume_modifications": post.get("resume_modifications", "").strip(),
        "mode_declenchement": mode if mode in ModeDeclenchement.values else ModeDeclenchement.CALENDRIER,
        "intervalle": _nombre(post.get("intervalle")), "unite_intervalle": post.get("unite_intervalle") or None,
        "seuil_heures": _nombre(post.get("seuil_heures")),
        "duree_estimee_min": _nombre(post.get("duree_estimee_min")) or 0, "nb_personnes": max(1, _nombre(post.get("nb_personnes")) or 1),
        "qualification": _nombre(post.get("qualification")),
    }
    types = dict(FichePreparation.Type.choices)
    contenu["preparations"] = [
        {"type": t, "libelle": lib.strip(), "quantite": max(1, _nombre(q) or 1), "piece": _nombre(piece)}
        for t, lib, q, piece in zip(post.getlist("prep_type"), post.getlist("prep_libelle"), post.getlist("prep_quantite"),
                                    post.getlist("prep_piece")) if lib.strip() and t in types]
    contenu["etapes"] = [{"texte": t.strip(), "attention": a.strip()}
                         for t, a in zip(post.getlist("etape_texte"), post.getlist("etape_attention")) if t.strip()]
    contenu["lignes"] = [
        {"cle": cle or None, "label": lab.strip(), "field_type": "number" if t == "number" else "checkbox", "unit": u.strip(),
         "valeur_min": _flottant(mn), "valeur_max": _flottant(mx)}
        for cle, t, lab, u, mn, mx in zip(post.getlist("ligne_cle"), post.getlist("ligne_type"), post.getlist("ligne_label"),
                                          post.getlist("ligne_unite"), post.getlist("ligne_min"), post.getlist("ligne_max"))
        if lab.strip()]
    return contenu


class FicheDetailView(LoginRequiredMixin, View):
    """Fiche (version validée, ou version choisie), frise de validation et actions du valideur."""

    def get(self, request, pk):
        fiche = _fiche(request, pk)
        numero = _nombre(request.GET.get("v"))
        versions = list(fiche.versions.select_related("redacteur", "qualification").order_by("-numero"))
        en_cours = next((v for v in versions if v.etat != Etat.VALIDEE), None)
        validee = next((v for v in versions if v.etat == Etat.VALIDEE), None)
        affichee = next((v for v in versions if v.numero == numero), None) or validee or en_cours
        if affichee is None:
            raise Http404("Cette fiche n'a pas encore de contenu.")
        suivie = affichee if affichee.etat != Etat.VALIDEE else en_cours
        peut, _ = validation.peut_agir(request.user, suivie) if suivie else (False, "")
        peut_rediger, _ = validation.peut_rediger(request.user, fiche.installation)
        contexte = {
            "fiche": fiche, "installation": fiche.installation, "version": affichee, "versions": versions,
            "validee": validee, "en_cours": en_cours, "suivie": suivie, "peut_agir": peut,
            "frise": validation.frise(suivie) if suivie else [],
            "blocage": validation.message_blocage(suivie) if suivie else "",
            "valideurs": validation.valideurs(suivie) if suivie else [],
            "peut_corriger": bool(en_cours and en_cours.etat == Etat.REFUSEE and en_cours.redacteur_id == request.user.pk and peut_rediger),
            "peut_proposer": peut_rediger and en_cours is None,
            "evenements": affichee.evenements.select_related("user"),
            "preparations": affichee.preparations.select_related("piece"),
            "etapes": affichee.etapes.all(), "lignes": affichee.items.order_by("order", "pk"),
            "destinations": (Installation.objects.filter(build_scope_q(request.user, "")).exclude(pk=fiche.installation_id)
                             .select_related("ship") if peut_rediger and validee else []),
            "sous_titre": f"Fiche de maintenance · {fiche.installation.designation}",
            **self._entete(fiche, affichee, validee, en_cours),
            **contexte_discussion(fiche, "fiche-comment-create"),
        }
        modifier = reverse("fiche-modifier", args=[fiche.pk])
        if contexte["peut_proposer"]:
            contexte["action_fiche"] = {"libelle": "Proposer une modification", "icone": "modification", "url": modifier}
        elif contexte["peut_corriger"]:
            contexte["action_fiche"] = {"libelle": "Corriger et soumettre à nouveau", "icone": "modification", "url": modifier}
        return render(request, "assets/fiche/detail.html", contexte)

    @staticmethod
    def _entete(fiche, affichee, validee, en_cours):
        heures = None
        if fiche.seuil_heures and fiche.mode_declenchement != ModeDeclenchement.CALENDRIER:
            releves = list(InstallationHourReading.objects.filter(installation=fiche.installation))
            depuis = heures_depuis_visite_maintenance(fiche, releves)
            heures = {"libelle": "Depuis la dernière visite", "valeur": "—" if depuis is None else formater_heures(depuis),
                      "detail": f"Gamme {fiche_maintenance.libelle_gamme(fiche.mode_declenchement, None, None, fiche.seuil_heures)}",
                      "etat": "danger" if depuis is not None and depuis >= fiche.seuil_heures else ""}
        heures_min, minutes = divmod(affichee.duree_estimee_min, 60)
        indicateurs = [
            {"libelle": "Gamme", "valeur": fiche_maintenance.gamme_de(affichee)},
            {"libelle": "Durée estimée", "valeur": f"{heures_min} h {minutes:02d}" if heures_min else f"{minutes} min"},
            {"libelle": "Personnes", "valeur": affichee.nb_personnes},
            {"libelle": "Qualification", "valeur": affichee.qualification.title if affichee.qualification_id else "Aucune"},
        ]
        if heures:
            indicateurs.insert(1, heures)
        version = {}
        if validee:
            version["publiee_le"] = validee.valide_le
        if en_cours and en_cours.etat != Etat.REFUSEE:
            version.update(proposition_par=validation.nom(en_cours.redacteur), proposition_le=en_cours.created_at)
        return {
            "indicateurs_fiche": indicateurs, "badge_etat": BADGES.get(affichee.etat, "attention"),
            "version_fiche": version if validee else None,
        }


class FicheAssistantView(LoginRequiredMixin, View):
    """Assistant en étapes : nouvelle fiche (installation) ou nouvelle version (fiche), ou correction d'une version renvoyée."""

    def _contexte(self, request, installation, fiche, contenu, correction=None, erreur=""):
        return render(request, "assets/fiche/assistant.html", {
            "installation": installation, "fiche": fiche, "contenu": contenu, "correction": correction, "erreur": erreur,
            "modes": ModeDeclenchement.choices, "unites": InstallationMaintenance.UNITE_INTERVALLE_CHOICES,
            "types_preparation": FichePreparation.Type.choices,
            "pieces": StockPiece.objects.filter(ship_id=installation.ship_id).order_by("designation"),
            "qualifications": TrainingCourse.objects.order_by("title"),
            "annuler": reverse("fiche-detail", args=[fiche.pk]) if fiche else reverse("installation-detail", args=[installation.pk]),
        })

    def _charger(self, request, pk=None, fiche_pk=None):
        if fiche_pk is not None:
            fiche = _fiche(request, fiche_pk)
            installation, correction = fiche.installation, fiche.version_en_cours
            if correction is not None and not (correction.etat == Etat.REFUSEE and correction.redacteur_id == request.user.pk):
                raise PermissionDenied("Une version de cette fiche est déjà en cours de validation.")
        else:
            installation, fiche, correction = _installation(request, pk), None, None
        autorise, raison = validation.peut_rediger(request.user, installation)
        if not autorise:
            raise PermissionDenied(raison)
        return installation, fiche, correction

    def get(self, request, pk=None, fiche_pk=None):
        installation, fiche, correction = self._charger(request, pk, fiche_pk)
        base = correction or (fiche.version_validee if fiche else None)
        contenu = fiche_maintenance.contenu_de(base) if base else fiche_maintenance.contenu_initial()
        if fiche:
            contenu["resume_modifications"] = ""
        return self._contexte(request, installation, fiche, contenu, correction)

    def post(self, request, pk=None, fiche_pk=None):
        installation, fiche, correction = self._charger(request, pk, fiche_pk)
        contenu = lire_formulaire(request.POST)
        try:
            if correction:
                validation.resoumettre(request.user, correction.pk, contenu)
                version = correction
            else:
                version = validation.soumettre(request.user, installation, contenu, fiche)
        except ErreurCircuit as erreur:
            return self._contexte(request, installation, fiche, contenu, correction, str(erreur))
        messages.success(request, "Version proposée : elle suit maintenant le circuit de visas.")
        return redirect(f"{reverse('fiche-detail', args=[version.fiche_id])}?v={version.numero}")


class _ActionView(LoginRequiredMixin, View):
    """POST d'une étape : l'étape attendue vient du formulaire affiché, pour refuser un envoi périmé."""

    def post(self, request, pk):
        version = get_object_or_404(validation.versions_visibles(request.user), pk=pk)
        try:
            self.agir(request, version, request.POST.get("etape", ""))
        except ErreurCircuit as erreur:
            messages.error(request, str(erreur))
        return redirect(f"{reverse('fiche-detail', args=[version.fiche_id])}?v={version.numero}")


class FicheViserView(_ActionView):
    def agir(self, request, version, etape):
        validation.viser(request.user, version.pk, etape)
        messages.success(request, "Visa enregistré.")


class FicheRefuserView(_ActionView):
    def agir(self, request, version, etape):
        validation.refuser(request.user, version.pk, etape, request.POST.get("motif"))
        messages.success(request, "Version renvoyée au rédacteur.")


class FicheDupliquerView(LoginRequiredMixin, View):
    """Copie indépendante de la version validée vers une autre installation."""

    def post(self, request, pk):
        fiche = _fiche(request, pk)
        cible = _installation(request, request.POST.get("installation"))
        validee = fiche.version_validee
        if validee is None:
            raise PermissionDenied("Seule une fiche validée peut être copiée.")
        try:
            version = validation.dupliquer(request.user, validee, cible)
        except ErreurCircuit as erreur:
            messages.error(request, str(erreur))
            return redirect("fiche-detail", pk=fiche.pk)
        messages.success(request, f"Fiche copiée vers {cible.designation} : elle suit le circuit de visas de cette installation.")
        return redirect(f"{reverse('fiche-detail', args=[version.fiche_id])}?v={version.numero}")


class FicheCommentaireView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fiche = _fiche(request, pk)
        corps = request.POST.get("body", "").strip()
        if corps:
            ajouter_commentaire(fiche, request.user, corps)
            messages.success(request, "Commentaire ajouté.")
        else:
            messages.error(request, "Le commentaire ne peut pas être vide.")
        return redirect("fiche-detail", pk=fiche.pk)
