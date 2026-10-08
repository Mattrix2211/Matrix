"""Écrans de la fiche de maintenance d'une installation : consultation, assistant de rédaction, visas."""
import math
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
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.saisie import entier_ou_none, sans_nul
from threads.utils import ajouter_commentaire, contexte_discussion
from training.models import TrainingCourse

from accounts.models import SpecialityChoice

from . import fiche_adaptation, fiche_comparaison, fiche_flotte, fiche_maintenance, fiche_signalement, fiche_validation as validation
from .mesures import formater_heures, heures_depuis_visite_maintenance
from .models import (
    CategorieCatalogue, ChecklistTemplate, FichePreparation, Installation, InstallationHourReading, InstallationMaintenance,
    ModeDeclenchement, TypeReleve,
)
from .proposition_article import ErreurCircuit

Etat = ChecklistTemplate.Etat
BADGES = {Etat.VALIDEE: "ok", Etat.REFUSEE: "danger"}


def _fiche(request, pk):
    """Fiche visible par l'utilisateur (installation de son périmètre ou fiche flotte consultable) ; sinon 404."""
    return get_object_or_404(validation.fiches_visibles(request.user), pk=pk)


def _installation(request, pk):
    try:
        pk = uuid.UUID(str(pk))
    except ValueError:
        raise Http404("Installation introuvable")
    return get_object_or_404(Installation.objects.filter(build_scope_q(request.user, "")), pk=pk)


def _nombre(texte):
    """Entier lu dans un champ de formulaire, None si vide ou illisible."""
    return entier_ou_none((texte or "").strip().replace(" ", "").replace(" ", ""))


def _entier(texte):
    """Entier d'un champ du formulaire : None si vide, ErreurCircuit si illisible."""
    texte = (texte or "").strip().replace("\u00a0", "").replace(" ", "")
    if not texte:
        return None
    try:
        return int(texte)
    except ValueError:
        raise ErreurCircuit(f"« {texte[:20]} » n'est pas un nombre entier.")


def _flottant(texte):
    texte = (texte or "").strip().replace(",", ".")
    try:
        valeur = float(texte) if texte else None
    except ValueError:
        return None
    return valeur if valeur is None or math.isfinite(valeur) else None


def _cle(texte):
    """Identité de ligne lue dans le formulaire ; None si vide, ErreurCircuit si mal formée."""
    if not texte:
        return None
    try:
        return uuid.UUID(texte)
    except ValueError:
        raise ErreurCircuit("Identifiant de ligne invalide : rechargez l'assistant.")


def _sans_nul(post):
    """Copie du formulaire sans caractère NUL (PostgreSQL les refuse)."""
    copie = post.copy()
    for cle in list(copie):
        copie.setlist(cle, [sans_nul(v) for v in copie.getlist(cle)])
    return copie


def _type_ligne(type_saisi, releve):
    """Les vibrations se saisissent en texte (A, B ou C), les autres relevés en nombre."""
    if releve == TypeReleve.VIBRATIONS:
        return "text"
    return "number" if type_saisi == "number" or releve else "checkbox"


def lire_formulaire(post):
    """Contenu d'une version lu dans le formulaire de l'assistant (les lignes vides sont ignorées)."""
    post = _sans_nul(post)
    mode = post.get("mode_declenchement")
    contenu = {
        "name": post.get("name", "").strip(), "description": post.get("description", "").strip(),
        "resume_modifications": post.get("resume_modifications", "").strip(),
        "mode_declenchement": mode if mode in ModeDeclenchement.values else ModeDeclenchement.CALENDRIER,
        "intervalle": _entier(post.get("intervalle")), "unite_intervalle": post.get("unite_intervalle") or None,
        "seuil_heures": _entier(post.get("seuil_heures")),
        "duree_estimee_min": _entier(post.get("duree_estimee_min")) or 0, "nb_personnes": _entier(post.get("nb_personnes")) or 1,
        "qualification": _entier(post.get("qualification")),
    }
    types = dict(FichePreparation.Type.choices)
    contenu["preparations"] = [
        {"type": t, "libelle": lib.strip(), "quantite": _entier(q) or 1, "piece": _entier(piece)}
        for t, lib, q, piece in zip(post.getlist("prep_type"), post.getlist("prep_libelle"), post.getlist("prep_quantite"),
                                    post.getlist("prep_piece")) if lib.strip() and t in types]
    contenu["etapes"] = [{"texte": t.strip(), "attention": a.strip()}
                         for t, a in zip(post.getlist("etape_texte"), post.getlist("etape_attention")) if t.strip()]
    libelles = post.getlist("ligne_label")
    obligatoires = (post.getlist("ligne_obligatoire") + [""] * len(libelles))[:len(libelles)]
    releves = (post.getlist("ligne_releve") + [""] * len(libelles))[:len(libelles)]
    contenu["lignes"] = [
        {"cle": _cle(cle), "label": lab.strip(), "field_type": _type_ligne(t, releve), "unit": u.strip(), "releve": releve,
         "required": oblig == "1", "valeur_min": _flottant(mn), "valeur_max": _flottant(mx)}
        for cle, t, lab, u, mn, mx, oblig, releve in zip(post.getlist("ligne_cle"), post.getlist("ligne_type"), libelles,
                                                         post.getlist("ligne_unite"), post.getlist("ligne_min"),
                                                         post.getlist("ligne_max"), obligatoires, releves)
        if lab.strip()]
    return contenu


def _fil_ariane(fiche):
    """Fil d'Ariane de la fiche : installation, catégorie du catalogue ou fiches flotte."""
    if fiche.installation_id:
        return [{"libelle": fiche.installation.designation, "url": reverse("installation-detail", args=[fiche.installation_id]) + "?tab=maintenance"}]
    if fiche.categorie_id:
        return [{"libelle": "Catalogue", "url": reverse("catalogue")},
                {"libelle": fiche.categorie.nom, "url": reverse("catalogue") + f"?categorie={fiche.categorie_id}"}]
    return [{"libelle": "Catalogue", "url": reverse("catalogue")}]


def _droits_redaction(user, fiche):
    """(peut_rediger, direct) : l'utilisateur peut-il proposer une version de cette fiche, et le fait-il directement ?"""
    if fiche.niveau == "FLOTTE":
        mode, _ = validation.mode_redaction_flotte(user, fiche.specialite_visee.pk)
        return mode is not None, mode == validation.DIRECT
    return validation.peut_rediger(user, fiche.installation)[0], False


class FicheDetailView(LoginRequiredMixin, View):
    """Fiche (version validée, ou version choisie), frise de validation et actions du valideur."""

    def get(self, request, pk):
        fiche = _fiche(request, pk)
        numero = _nombre(request.GET.get("v"))
        visibles = fiche.versions.select_related("redacteur", "qualification")
        if fiche.niveau == "FLOTTE":
            visibles = visibles.filter(pk__in=validation.versions_visibles(request.user).values("pk"))
        versions = list(visibles.order_by("-numero"))
        en_cours = next((v for v in versions if v.etat != Etat.VALIDEE), None)
        validee = next((v for v in versions if v.etat == Etat.VALIDEE), None)
        affichee = next((v for v in versions if v.numero == numero), None) or validee or en_cours
        if affichee is None:
            raise Http404("Cette fiche n'a pas encore de contenu.")
        suivie = affichee if affichee.etat != Etat.VALIDEE else en_cours
        peut, _ = validation.peut_agir(request.user, suivie) if suivie else (False, "")
        valideurs = validation.valideurs(suivie) if suivie else []
        peut_rediger, direct = _droits_redaction(request.user, fiche)
        a_terre = equipage_a_terre_lecture_seule(request.user)
        bord = fiche.niveau == "BORD"
        peut_traiter = peut_rediger and not a_terre and validation.peut_traiter_signalement(request.user, fiche)[0]
        contexte = {
            "fiche": fiche, "installation": fiche.installation, "version": affichee, "versions": versions,
            "validee": validee, "en_cours": en_cours, "suivie": suivie, "peut_agir": peut,
            "frise": validation.frise(suivie) if suivie else [],
            "blocage": validation.message_blocage(suivie, valideurs) if suivie else "",
            "valideurs": valideurs, "fil": _fil_ariane(fiche), "flotte": not bord,
            "verification": bool(suivie and suivie.etat == Etat.VERIFICATION),
            "peut_corriger": bool(en_cours and en_cours.etat == Etat.REFUSEE and en_cours.redacteur_id == request.user.pk and peut_rediger),
            "peut_proposer": peut_rediger and en_cours is None,
            "evenements": affichee.evenements.select_related("user"),
            "preparations": affichee.preparations.select_related("piece"),
            "etapes": affichee.etapes.all(), "lignes": affichee.items.order_by("order", "pk"),
            "destinations": (Installation.objects.filter(build_scope_q(request.user, "")).exclude(pk=fiche.installation_id)
                             .select_related("ship") if bord and peut_rediger and validee else []),
            "sous_titre": f"Fiche de maintenance · {fiche.cible}" + ("" if bord else " · fiche flotte"),
            "comparaison": fiche_comparaison.comparer(validee, suivie) if suivie and validee and suivie.pk != validee.pk else None,
            "signalements": list(fiche_signalement.ouverts(fiche)) if peut_traiter else [],
            "peut_traiter": peut_traiter and en_cours is None,
            **self._adaptation(request, fiche, peut_rediger, en_cours),
            **self._entete(fiche, affichee, validee, en_cours),
            **contexte_discussion(fiche, "fiche-comment-create"),
        }
        modifier = reverse("fiche-modifier" if bord else "fiche-flotte-modifier", args=[fiche.pk])
        if contexte["peut_proposer"]:
            contexte["action_fiche"] = {"libelle": "Proposer une modification", "icone": "modification", "url": modifier}
        elif contexte["peut_corriger"]:
            contexte["action_fiche"] = {"libelle": "Corriger et soumettre à nouveau", "icone": "modification", "url": modifier}
        contexte["peut_proposer_flotte"] = bord and bool(validee) and validation.peut_proposer_flotte(request.user)[0] and not a_terre
        return render(request, "assets/fiche/detail.html", contexte)

    @staticmethod
    def _adaptation(request, fiche, peut_rediger, en_cours):
        """Adaptation locale : fiche flotte d'origine et changements que le navire doit examiner."""
        a_examiner = bool(fiche.origine_id and fiche.origine_en_attente and peut_rediger and en_cours is None
                          and not equipage_a_terre_lecture_seule(request.user))
        return {"origine": fiche.origine, "origine_a_examiner": a_examiner}

    @staticmethod
    def _entete(fiche, affichee, validee, en_cours):
        heures = None
        if fiche.installation_id and fiche.seuil_heures and fiche.mode_declenchement != ModeDeclenchement.CALENDRIER:
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


def _signalement(request, fiche):
    """Signalement ouvert à partir duquel l'assistant est lancé (?signalement=), s'il concerne cette fiche
    et que l'utilisateur a le droit de le traiter (jamais d'indice sur les autres)."""
    pk = _nombre(request.GET.get("signalement") or request.POST.get("signalement"))
    if not (fiche and pk) or not validation.peut_traiter_signalement(request.user, fiche)[0]:
        return None
    return fiche.signalements.filter(pk=pk, traite=False).first()


def _visas_prevus(user, flotte=False, direct=False):
    """Visas que suivra la version, en clair, selon le rôle du rédacteur."""
    if direct:
        return "visa de votre chef, puis publication"
    profil = getattr(user, "profile", None)
    visas = ["chef de service", "commandant adjoint du service"]
    if profil is not None and profil.role == "CHEF_SECTION":
        visas.insert(0, "chef de secteur")
    if flotte:
        visas += ["vérification par le responsable de spécialité", "visa de son chef, puis publication"]
    return ", ".join(visas)


class _AssistantBase(LoginRequiredMixin, View):
    """Rendu commun de l'assistant en étapes (fiche du bord ou fiche flotte)."""

    def rendre(self, request, contexte, contenu, erreur=""):
        return render(request, "assets/fiche/assistant.html", {
            "contenu": contenu, "erreur": erreur,
            "modes": ModeDeclenchement.choices, "unites": InstallationMaintenance.UNITE_INTERVALLE_CHOICES,
            "types_preparation": FichePreparation.Type.choices, "types_releve": TypeReleve.choices, "calendaire_seul": False,
            "qualifications": TrainingCourse.objects.order_by("title"), "pieces": [],
            **contexte,
        })


class FicheAssistantView(_AssistantBase):
    """Assistant en étapes : nouvelle fiche (installation) ou nouvelle version (fiche), ou correction d'une version renvoyée."""

    def _contexte(self, request, installation, fiche, correction, origine, signalement):
        return {
            "installation": installation, "fiche": fiche, "correction": correction, "origine": origine, "signalement": signalement,
            "pieces": StockPiece.objects.filter(ship_id=installation.ship_id).order_by("designation"),
            "sous_titre": installation.designation, "bouton": "Proposer pour validation",
            "visas": _visas_prevus(request.user),
            "annuler": reverse("fiche-detail", args=[fiche.pk]) if fiche else reverse("installation-detail", args=[installation.pk]),
        }

    def _charger(self, request, pk=None, fiche_pk=None):
        if fiche_pk is not None:
            fiche = _fiche(request, fiche_pk)
            if fiche.niveau != "BORD":
                raise Http404("Fiche introuvable")
            installation, correction = fiche.installation, fiche.version_en_cours
            if correction is not None and not (correction.etat == Etat.REFUSEE and correction.redacteur_id == request.user.pk):
                raise PermissionDenied("Une version de cette fiche est déjà en cours de validation.")
        else:
            installation, fiche, correction = _installation(request, pk), None, None
        autorise, raison = validation.peut_rediger(request.user, installation)
        if not autorise:
            raise PermissionDenied(raison)
        return installation, fiche, correction

    def _origine(self, request, installation):
        """Fiche flotte dont l'adaptation est proposée (?depuis=), si elle vise bien cette installation."""
        pk = _nombre(request.GET.get("depuis") or request.POST.get("depuis"))
        if not pk:
            return None
        origine = InstallationMaintenance.objects.filter(pk=pk).first()
        if origine is None or not fiche_adaptation.flotte_adaptable(installation, origine):
            raise PermissionDenied("Cette fiche flotte ne peut pas être adaptée pour cette installation.")
        return origine

    def get(self, request, pk=None, fiche_pk=None):
        installation, fiche, correction = self._charger(request, pk, fiche_pk)
        origine = self._origine(request, installation) if fiche is None else None
        signalement = _signalement(request, fiche)
        base = correction or (fiche.version_validee if fiche else None)
        if origine:
            contenu = fiche_adaptation.contenu_de_adaptation(origine)
        else:
            contenu = fiche_maintenance.contenu_de(base) if base else fiche_maintenance.contenu_initial()
        if fiche:
            contenu["resume_modifications"] = f"Signalement : {signalement.texte}"[:1000] if signalement else ""
        return self.rendre(request, self._contexte(request, installation, fiche, correction, origine, signalement), contenu)

    def post(self, request, pk=None, fiche_pk=None):
        installation, fiche, correction = self._charger(request, pk, fiche_pk)
        origine = self._origine(request, installation) if fiche is None else None
        signalement = _signalement(request, fiche)
        contexte = self._contexte(request, installation, fiche, correction, origine, signalement)
        try:
            contenu = lire_formulaire(request.POST)
        except ErreurCircuit as erreur:
            return self.rendre(request, contexte, fiche_maintenance.contenu_initial(), str(erreur))
        try:
            if correction:
                validation.resoumettre(request.user, correction.pk, contenu)
                version = correction
            else:
                version = validation.soumettre(request.user, installation, contenu, fiche, origine=origine, signalement=signalement)
        except ErreurCircuit as erreur:
            return self.rendre(request, contexte, contenu, str(erreur))
        messages.success(request, "Version proposée : elle suit maintenant le circuit de visas.")
        return redirect(f"{reverse('fiche-detail', args=[version.fiche_id])}?v={version.numero}")


class FicheFlotteAssistantView(_AssistantBase):
    """Assistant d'une fiche flotte : nouvelle fiche de catégorie (matériel) ou d'installation, nouvelle version,
    correction d'une version renvoyée, ou vérification par le responsable de spécialité."""

    def _charger(self, request, categorie_pk=None, depuis_pk=None, fiche_pk=None, version_pk=None):
        """(fiche, version à corriger ou vérifier, cible d'une nouvelle fiche, spécialité visée)."""
        if version_pk is not None:
            version = get_object_or_404(validation.versions_visibles(request.user), pk=version_pk, fiche__niveau="FLOTTE")
            if version.etat != Etat.VERIFICATION or not validation.peut_agir(request.user, version)[0]:
                raise PermissionDenied("Cette vérification n'est pas à votre charge.")
            return version.fiche, version, None, version.fiche.specialite_visee
        if fiche_pk is not None:
            fiche = _fiche(request, fiche_pk)
            if fiche.niveau != "FLOTTE":
                raise Http404("Fiche introuvable")
            correction = fiche.version_en_cours
            if correction is not None and not (correction.etat == Etat.REFUSEE and correction.redacteur_id == request.user.pk):
                raise PermissionDenied("Une version de cette fiche est déjà en cours de validation.")
            return fiche, correction, None, fiche.specialite_visee
        if categorie_pk is not None:
            categorie = get_object_or_404(CategorieCatalogue.objects.select_related("specialite"), pk=categorie_pk, actif=True)
            return None, None, {"categorie": categorie}, categorie.specialite
        depart = _fiche(request, depuis_pk)
        if depart.niveau != "BORD" or depart.version_validee is None:
            raise Http404("Fiche introuvable")
        installation = depart.installation
        cible = {"equipement": installation.designation, "reference_equipement": installation.reference,
                 "classe_navire": installation.ship.classe_navire}
        return None, None, cible, None

    def _contexte(self, request, fiche, version, cible, specialite, verification):
        categorie = fiche.categorie if fiche else (cible or {}).get("categorie")
        if fiche:
            sous_titre = f"Fiche flotte · {fiche.cible}"
        elif categorie:
            sous_titre = f"Fiche flotte · {categorie.nom} et ses sous-catégories"
        else:
            sous_titre = f"Fiche flotte · {cible['equipement']}"
        direct = specialite is not None and validation.est_responsable(request.user, specialite.pk)
        return {
            "fiche": fiche, "correction": None if verification else version, "installation": None, "flotte": True,
            "verification": verification, "en_verification": version if verification else None, "sous_titre": sous_titre, "calendaire_seul": categorie is not None,
            "cible": cible if categorie is None and fiche is None else None,
            "specialites": SpecialityChoice.objects.filter(active=True).order_by("name") if specialite is None else [],
            "bouton": "Vérifier et transmettre" if verification else "Proposer pour validation",
            "visas": _visas_prevus(request.user, flotte=True, direct=direct),
            "annuler": reverse("fiche-detail", args=[fiche.pk]) if fiche else (
                reverse("catalogue") + (f"?categorie={categorie.pk}" if categorie else "")),
        }

    def _entree(self, request, **url):
        fiche, version, cible, specialite = self._charger(request, **url)
        verification = url.get("version_pk") is not None
        signalement = _signalement(request, fiche)
        contexte = self._contexte(request, fiche, version, cible, specialite, verification)
        contexte["signalement"] = signalement
        if not verification and specialite is not None:
            mode, raison = validation.mode_redaction_flotte(request.user, specialite.pk)
            if mode is None:
                raise PermissionDenied(raison)
        elif not verification:
            autorise, raison = validation.peut_proposer_flotte(request.user)
            if not autorise and not request.user.specialites_dont_il_est_responsable.exists():
                raise PermissionDenied(raison)
        return fiche, version, cible, specialite, verification, signalement, contexte

    def get(self, request, **url):
        fiche, version, cible, specialite, verification, signalement, contexte = self._entree(request, **url)
        depart = None
        if url.get("depuis_pk") is not None:
            depart = _fiche(request, url["depuis_pk"]).version_validee
        elif cible and cible.get("categorie") and _nombre(request.GET.get("depuis")):
            # Remplacement d'une fiche héritée d'une catégorie parente : le contenu de départ est celui du parent.
            parente = fiche_flotte.fiches_applicables(cible["categorie"]).values()
            depart = next((f.version_validee for f in parente if f.pk == _nombre(request.GET.get("depuis"))), None)
        base = version or (fiche.version_validee if fiche else None) or depart
        contenu = fiche_maintenance.contenu_de(base) if base else fiche_maintenance.contenu_initial()
        if base is depart and depart:
            contenu["lignes"] = [ligne | {"cle": None} for ligne in contenu["lignes"]]
        if fiche and not verification:
            contenu["resume_modifications"] = f"Signalement : {signalement.texte}"[:1000] if signalement else ""
        if contenu["mode_declenchement"] != ModeDeclenchement.CALENDRIER and contexte["calendaire_seul"]:
            contenu["mode_declenchement"] = ModeDeclenchement.CALENDRIER
        return self.rendre(request, contexte, contenu)

    def post(self, request, **url):
        fiche, version, cible, specialite, verification, signalement, contexte = self._entree(request, **url)
        try:
            contenu = lire_formulaire(request.POST)
            if cible is not None and cible.get("categorie") is None:
                cible = self._cible_installation(request, cible)
        except ErreurCircuit as erreur:
            return self.rendre(request, contexte, fiche_maintenance.contenu_initial(), str(erreur))
        try:
            if verification:
                validation.verifier(request.user, version.pk, contenu)
                resultat = version
            elif version:
                validation.resoumettre(request.user, version.pk, contenu)
                resultat = version
            else:
                resultat = validation.soumettre_flotte(request.user, contenu, cible, fiche, signalement)
        except ErreurCircuit as erreur:
            return self.rendre(request, contexte, contenu, str(erreur))
        messages.success(request, "Fiche vérifiée et transmise." if verification else "Version proposée : elle suit maintenant le circuit de visas.")
        return redirect(f"{reverse('fiche-detail', args=[resultat.fiche_id])}?v={resultat.numero}")

    @staticmethod
    def _cible_installation(request, cible):
        """Cible d'une fiche flotte d'installation : équipement, référence et classe viennent du formulaire, la spécialité aussi."""
        specialite = SpecialityChoice.objects.filter(pk=_nombre(request.POST.get("specialite")), active=True).first()
        if specialite is None:
            raise ErreurCircuit("Choisissez la spécialité qui vérifiera cette fiche.")
        donnees = _sans_nul(request.POST)
        return {"specialite": specialite, "equipement": donnees.get("equipement", "").strip(),
                "reference_equipement": donnees.get("reference_equipement", "").strip(),
                "classe_navire": donnees.get("classe_navire", "").strip()}


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
        if fiche.niveau != "BORD":
            raise Http404("Fiche introuvable")
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


class FicheOrigineView(LoginRequiredMixin, View):
    """Décision du navire quand la fiche flotte d'origine a changé : reprendre ou garder son adaptation."""
    decision = None

    def post(self, request, pk):
        fiche = _fiche(request, pk)
        try:
            if self.decision == "reprendre":
                version = fiche_adaptation.reprendre(request.user, fiche.pk)
                messages.success(request, "Changements repris : la nouvelle version suit le circuit de visas du bord.")
                return redirect(f"{reverse('fiche-detail', args=[fiche.pk])}?v={version.numero}")
            fiche_adaptation.garder(request.user, fiche.pk)
            messages.success(request, "Votre adaptation est conservée ; la décision est tracée.")
        except ErreurCircuit as erreur:
            messages.error(request, str(erreur))
        return redirect("fiche-detail", pk=fiche.pk)


class FicheCommentaireView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fiche = _fiche(request, pk)
        corps = sans_nul(request.POST.get("body")).strip()
        if corps:
            ajouter_commentaire(fiche, request.user, corps)
            messages.success(request, "Commentaire ajouté.")
        else:
            messages.error(request, "Le commentaire ne peut pas être vide.")
        return redirect("fiche-detail", pk=fiche.pk)
