"""Interface web des tâches : liste, fiche avec fil contextuel, actions de suivi."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View

from annonces.models import Annonce
from annonces.services import peut_consulter as annonce_consultable
from threads.utils import commentaires_de

from .models import Tache
from .services import (
    ajouter_element,
    ajouter_participant,
    attribuer_a_unite,
    avancement_equipe,
    basculer_element,
    creer_tache,
    demarrer,
    interlocuteurs_possibles,
    joindre_fichier,
    marins_assignables,
    modifier_tache,
    partager,
    peut_consulter,
    peut_editer_checklist,
    peut_gerer,
    peut_joindre,
    peut_modifier,
    peut_supprimer_piece,
    rendre_compte,
    reprendre,
    repondre,
    signaler_blocage,
    supprimer_element,
    supprimer_piece,
    taches_visibles,
    unites_assignables,
)

User = get_user_model()

LIMITE_TERMINEES = 10  # nombre de tâches terminées listées sur la page


def _erreurs(request, exc):
    if isinstance(exc, PermissionError):
        messages.error(request, str(exc))
    else:
        for liste in getattr(exc, "message_dict", {"": exc.messages}).values():
            for erreur in liste:
                messages.error(request, erreur)


def _entier(valeur):
    """Identifiant numérique d'un formulaire ; 404 si la valeur est invalide."""
    if not (valeur and valeur.isascii() and valeur.isdigit()):
        raise Http404
    return int(valeur)


def _tache_visible(request, pk, verrou=False):
    taches = Tache.objects.select_related("assigne", "created_by")
    if verrou:  # évite qu'une action concurrente rouvre une tâche tout juste terminée
        taches = taches.select_for_update(of=("self",))
    tache = get_object_or_404(taches, pk=pk)
    if not peut_consulter(request.user, tache):
        raise Http404
    return tache


def _annonce_source(request, pk):
    """Annonce d'origine d'une tâche : consultable par l'utilisateur, qui doit pouvoir attribuer."""
    annonce = Annonce.objects.filter(pk=pk).first() if str(pk).isascii() and str(pk).isdigit() else None
    if annonce is None or not annonce_consultable(request.user, annonce) or not marins_assignables(request.user).exists():
        return None
    return annonce


class TachesIndexView(LoginRequiredMixin, View):
    def get(self, request):
        source = _annonce_source(request, request.GET.get("annonce", ""))
        taches = list(taches_visibles(request.user).select_related("assigne").prefetch_related("elements_checklist"))
        ouvertes = [t for t in taches if t.ouverte]
        return render(request, "taches/index.html", {
            "mes_taches": [t for t in ouvertes if t.assigne_id == request.user.pk],
            "suivies": [t for t in ouvertes if t.assigne_id != request.user.pk],
            "terminees": sorted((t for t in taches if not t.ouverte), key=lambda t: t.terminee_le or t.updated_at, reverse=True)[:LIMITE_TERMINEES],
            "marins": marins_assignables(request.user),
            "unites": unites_assignables(request.user),
            "avancement": avancement_equipe(request.user),
            "aujourdhui": timezone.localdate(),
            "annonce_source": source,
        })

    def post(self, request):
        # Sans marin désigné, la tâche est celle de l'utilisateur lui-même.
        assigne = User.objects.filter(pk=request.POST["assigne"]).first() if request.POST.get("assigne") else request.user
        saisie = request.POST.get("echeance", "").strip()
        echeance = parse_date(saisie) if saisie else None
        if assigne is None or (saisie and echeance is None) or not request.POST.get("titre", "").strip():
            messages.error(request, "Le titre et le marin sont obligatoires, l'échéance doit être une date valide.")
            return redirect("taches-index")
        source = None
        if request.POST.get("annonce"):
            source = _annonce_source(request, request.POST["annonce"])
            if source is None:
                messages.error(request, "Annonce d'origine introuvable ou non accessible.")
                return redirect("taches-index")
        elements = request.POST.get("checklist", "").splitlines()
        priorite = request.POST.get("priorite", Tache.PRIORITE_NORMALE)
        try:
            if request.POST.get("unite"):
                _, taches = attribuer_a_unite(
                    request.user, request.POST["unite"], request.POST["titre"], echeance, request.POST.get("description", ""),
                    priorite=priorite, elements=elements,
                )
                messages.success(request, f"{len(taches)} tâche(s) individuelle(s) attribuée(s).")
                return redirect("taches-index")
            tache = creer_tache(
                request.user, assigne, request.POST["titre"], echeance, request.POST.get("description", ""),
                priorite=priorite, partagee=request.POST.get("partagee") == "on", annonce=source, elements=elements,
            )
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
            return redirect("taches-index")
        messages.success(request, "Tâche créée." if tache.personnelle else "Tâche attribuée.")
        return redirect("tache-detail", pk=tache.pk)


class TacheDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        tache = _tache_visible(request, pk)
        gerer = peut_gerer(request.user, tache)
        return render(request, "taches/detail.html", {
            "tache": tache,
            "elements": tache.elements_checklist.all(),
            "pieces": [(p, peut_supprimer_piece(request.user, p)) for p in tache.pieces_jointes.select_related("created_by", "tache")],
            "peut_editer_checklist": peut_editer_checklist(request.user, tache),
            "peut_joindre": peut_joindre(request.user, tache),
            "annonce_source": tache.annonce if tache.annonce_id and annonce_consultable(request.user, tache.annonce) else None,
            "commentaires": commentaires_de(tache),
            "participants": tache.participants.all(),
            "est_assigne": request.user.pk == tache.assigne_id,
            "peut_gerer": gerer,
            "interlocuteurs": interlocuteurs_possibles(tache) if gerer else [],
            "peut_modifier": peut_modifier(request.user, tache),
            "marins": marins_assignables(request.user) if gerer else [],
            "en_retard": tache.en_retard_au(timezone.localdate()),
        })


class TacheActionView(LoginRequiredMixin, View):
    """Actions de suivi : démarrer, bloquer, rendre compte, lever le blocage, modifier, partager, ajouter un interlocuteur."""

    @transaction.atomic
    def post(self, request, pk):
        tache = _tache_visible(request, pk, verrou=True)
        action = request.POST.get("action")
        try:
            if action == "demarrer":
                demarrer(tache, request.user)
            elif action == "bloquer":
                signaler_blocage(tache, request.user, request.POST.get("motif", ""))
            elif action == "rendre_compte":
                rendre_compte(tache, request.user, request.POST.get("compte_rendu", ""))
            elif action == "reprendre":
                reprendre(tache, request.user)
            elif action == "modifier":
                nouveau = User.objects.filter(pk=request.POST.get("assigne")).first()
                saisie = request.POST.get("echeance", "").strip()
                echeance = parse_date(saisie) if saisie else None
                if nouveau is None or (saisie and echeance is None):
                    raise ValidationError("Indiquez un marin et une échéance valide (ou aucune).")
                modifier_tache(request.user, tache, nouveau, echeance, request.POST.get("priorite", ""))
                messages.success(request, "Tâche modifiée.")
            elif action in ("partager", "ne_plus_partager"):
                partager(tache, request.user, action == "partager")
                messages.success(request, "Partage mis à jour.")
            elif action == "checklist_ajouter":
                ajouter_element(tache, request.user, request.POST.get("texte", ""))
            elif action == "checklist_basculer":
                basculer_element(tache, request.user, _entier(request.POST.get("element")))
            elif action == "checklist_supprimer":
                supprimer_element(tache, request.user, _entier(request.POST.get("element")))
            elif action == "joindre":
                joindre_fichier(tache, request.user, request.FILES.get("fichier"))
                messages.success(request, "Fichier joint.")
            elif action == "piece_supprimer":
                supprimer_piece(tache, request.user, _entier(request.POST.get("piece")))
                messages.success(request, "Fichier supprimé.")
            elif action == "interlocuteur":
                cible = User.objects.filter(pk=request.POST.get("interlocuteur")).first()
                if cible is None:
                    raise ValidationError("Interlocuteur introuvable.")
                ajouter_participant(tache, request.user, cible)
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("tache-detail", pk=tache.pk)


class TachePieceJointeView(LoginRequiredMixin, View):
    """Téléchargement d'une pièce jointe : réservé à ceux qui peuvent consulter la tâche."""

    def get(self, request, pk, piece_pk):
        tache = _tache_visible(request, pk)
        piece = get_object_or_404(tache.pieces_jointes, pk=piece_pk)
        try:
            reponse = FileResponse(piece.fichier.open("rb"), as_attachment=True, filename=piece.nom)
        except FileNotFoundError:
            raise Http404("Fichier introuvable.")
        reponse["X-Content-Type-Options"] = "nosniff"  # jamais d'affichage en ligne
        return reponse


class TacheCommentaireView(LoginRequiredMixin, View):
    """Réponse dans le fil : ouverte aux interlocuteurs, même à terre (cf. middleware)."""

    def post(self, request, pk):
        tache = _tache_visible(request, pk)
        try:
            repondre(tache, request.user, request.POST.get("body", ""))
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("tache-detail", pk=tache.pk)
