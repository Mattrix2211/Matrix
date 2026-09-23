from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.models import AuditLog
from org.models import Sector
from assets.models import Asset, Installation
from matrix.core.mixins import build_scope_q
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user
from matrix.core.validators import valider_photo, message_erreur_fichier
from notifications.models import Notification
from threads.utils import ajouter_commentaire, commentaires_de

from .models import (
    Anomalie, AnomalieStatutLog, CorrectiveTicket, TicketStatusLog,
    destinataires_anomalie, niveau_alerte_ticket, perimetre_du_profil,
)


def _est_chef(user):
    return user_role_level(user) >= RoleLevel.CHEF_SECTION


def _section_id_du_profil(user):
    profil = getattr(user, "profile", None)
    return profil.section_id if profil else None


def anomalies_visibles(user):
    """Anomalies que l'utilisateur a le droit de voir : pour un équipier, ses
    signalements et ceux de sa section ; pour un chef de section et au-dessus,
    ses signalements + tout son périmètre (build_scope_q sur les champs de
    périmètre de l'anomalie). Un utilisateur sans périmètre défini
    (administrateur général) voit tout, comme scope_filters_for_user() le
    prévoit."""
    if not _est_chef(user):
        filtre = Q(created_by=user)
        section_id = _section_id_du_profil(user)
        if section_id:
            filtre |= Q(section_id=section_id)
        return Anomalie.objects.filter(filtre)
    if not scope_filters_for_user(user):
        return Anomalie.objects.all()
    return Anomalie.objects.filter(Q(created_by=user) | build_scope_q(user, ""))


def _secteurs_selectionnables(user):
    """Secteurs proposables comme « secteur concerné » : ceux du navire du
    déclarant (un marin peut signaler un problème hors de son propre secteur) ;
    tous les secteurs pour un utilisateur sans navire (administrateur général)."""
    ship, _, _, _ = perimetre_du_profil(getattr(user, "profile", None))
    secteurs = Sector.objects.select_related("service")
    if ship:
        secteurs = secteurs.filter(service__ship=ship)
    return secteurs.order_by("service__name", "name")


def _equipements_du_perimetre(user):
    filtres = scope_filters_for_user(user)
    installations = Installation.objects.filter(**filtres) if filtres else Installation.objects.all()
    materiels = Asset.objects.filter(**filtres) if filtres else Asset.objects.all()
    return installations, materiels


def _anomalie_visible_ou_404(user, pk):
    return get_object_or_404(
        anomalies_visibles(user).select_related("installation", "asset", "ticket", "created_by"), pk=pk,
    )


class AnomalieListView(LoginRequiredMixin, View):
    """Liste des anomalies avec compteurs par statut (cartes cliquables + barre
    de répartition). Par défaut « Mes signalements » ; on peut basculer sur
    « Tout le périmètre » (chefs) ou « Ma section » (équipiers)."""
    template_name = 'logistics/anomalie_list.html'

    def get(self, request):
        peut_perimetre = _est_chef(request.user) or bool(_section_id_du_profil(request.user))
        vue = request.GET.get('vue', 'mes')
        if vue != 'perimetre' or not peut_perimetre:
            vue = 'mes'
        base = anomalies_visibles(request.user)
        if vue == 'mes':
            base = base.filter(created_by=request.user)

        comptes = {ligne['statut']: ligne['n'] for ligne in base.values('statut').annotate(n=Count('pk'))}
        total = sum(comptes.values())
        etapes = [
            {
                'code': code, 'libelle': libelle, 'nombre': comptes.get(code, 0),
                'pct': round(comptes.get(code, 0) / total * 100) if total else 0,
            }
            for code, libelle in Anomalie.STATUTS
        ]
        statut = request.GET.get('statut')
        if statut in dict(Anomalie.STATUTS):
            base = base.filter(statut=statut)
        else:
            statut = ''
        return render(request, self.template_name, {
            'anomalies': base.select_related('installation', 'asset'), 'etapes': etapes,
            'total': total, 'vue': vue, 'statut': statut, 'peut_voir_perimetre': peut_perimetre,
            'libelle_perimetre': 'Tout le périmètre' if _est_chef(request.user) else 'Ma section',
        })


class AnomalieCreateView(LoginRequiredMixin, View):
    """Signalement rapide : titre + gravité suffisent, tout le reste est
    optionnel. Ouvert à tout marin connecté. L'équipement peut être pré-rempli
    depuis sa fiche (?asset=<id> ou ?installation=<id>)."""
    template_name = 'logistics/anomalie_form.html'

    def _contexte(self, request, valeurs=None):
        installations, materiels = _equipements_du_perimetre(request.user)
        secteur_du_profil = perimetre_du_profil(getattr(request.user, 'profile', None))[2]
        return {
            'installations': installations.order_by('designation'),
            'materiels': materiels,
            'secteurs': _secteurs_selectionnables(request.user),
            'valeurs': valeurs or {
                'secteur': str(secteur_du_profil.pk) if secteur_du_profil else '',
                'installation': request.GET.get('installation', ''),
                'asset': request.GET.get('asset', ''),
                'gravite': '3',
            },
        }

    def _erreur(self, request, message):
        messages.error(request, message)
        return render(request, self.template_name, self._contexte(request, request.POST), status=400)

    def get(self, request):
        return render(request, self.template_name, self._contexte(request))

    def post(self, request):
        donnees = request.POST
        titre = donnees.get('titre', '').strip()
        if not titre:
            return self._erreur(request, "Merci de donner un titre à l'anomalie.")
        try:
            gravite = min(max(int(donnees.get('gravite') or 3), 1), 5)
        except ValueError:
            gravite = 3

        id_installation, id_materiel = donnees.get('installation', ''), donnees.get('asset', '')
        if id_installation and id_materiel:
            return self._erreur(request, "Choisissez une installation OU un matériel, pas les deux.")
        installations, materiels = _equipements_du_perimetre(request.user)
        installation = materiel = None
        try:
            if id_installation:
                installation = installations.get(pk=id_installation)
            if id_materiel:
                materiel = materiels.get(pk=id_materiel)
        except (Installation.DoesNotExist, Asset.DoesNotExist, ValueError, ValidationError):
            return self._erreur(request, "Équipement introuvable ou hors de votre périmètre.")

        secteur = None
        if donnees.get('secteur'):
            try:
                secteur = _secteurs_selectionnables(request.user).get(pk=donnees['secteur'])
            except (Sector.DoesNotExist, ValueError):
                return self._erreur(request, "Secteur introuvable ou hors de votre unité.")

        photo = request.FILES.get('photo')
        erreur_photo = message_erreur_fichier(photo, valider_photo)
        if erreur_photo:
            return self._erreur(request, erreur_photo)

        anomalie = Anomalie(
            titre=titre, description=donnees.get('description', '').strip(), gravite=gravite,
            localisation=donnees.get('localisation', '').strip(),
            installation=installation, asset=materiel, photo=photo,
            created_by=request.user, updated_by=request.user,
        )
        anomalie.rattacher_a(getattr(request.user, 'profile', None), secteur)
        with transaction.atomic():
            anomalie.save()
            AnomalieStatutLog.objects.create(
                anomalie=anomalie, ancien_statut='SIGNALEE', nouveau_statut='SIGNALEE', user=request.user,
                note="Signalement initial",
            )
            AuditLog.objects.create(
                actor=request.user, action='create_anomalie', details=f'anomalie={anomalie.pk}; titre={titre}',
            )
        niveau = niveau_alerte_ticket(gravite)
        for profil in destinataires_anomalie(anomalie):
            if profil.user_id != request.user.id:
                Notification.objects.create(
                    user=profil.user, level=niveau, verb=f"Anomalie signalée : {titre}",
                )
        messages.success(request, "Anomalie signalée. Merci !")
        return redirect('anomalie-detail', pk=anomalie.pk)


class AnomalieDetailView(LoginRequiredMixin, View):
    template_name = 'logistics/anomalie_detail.html'

    def get(self, request, pk):
        anomalie = _anomalie_visible_ou_404(request.user, pk)
        return render(request, self.template_name, {
            'anomalie': anomalie,
            'statuts': Anomalie.STATUTS,
            'peut_traiter': _est_chef(request.user),
            'historique': anomalie.status_logs.select_related('user'),
            'commentaires': commentaires_de(anomalie),
        })


class AnomalieTransitionView(LoginRequiredMixin, View):
    """Changement de statut, réservé aux chefs (CHEF_SECTION et au-dessus) dont
    le périmètre couvre l'anomalie. Notifie le déclarant."""

    def post(self, request, pk):
        if not _est_chef(request.user):
            raise PermissionDenied
        anomalie = _anomalie_visible_ou_404(request.user, pk)
        nouveau = request.POST.get('statut')
        if nouveau not in dict(Anomalie.STATUTS):
            return HttpResponseBadRequest('Statut invalide')
        ancien = anomalie.statut
        if nouveau != ancien:
            anomalie.statut = nouveau
            anomalie.updated_by = request.user
            with transaction.atomic():
                anomalie.save(update_fields=['statut', 'updated_by', 'updated_at'])
                AnomalieStatutLog.objects.create(
                    anomalie=anomalie, ancien_statut=ancien, nouveau_statut=nouveau, user=request.user,
                    note=request.POST.get('note', '').strip(),
                )
                AuditLog.objects.create(
                    actor=request.user, action='anomalie_status_change',
                    details=f'anomalie={anomalie.pk}; {ancien} -> {nouveau}',
                )
            if anomalie.created_by_id and anomalie.created_by_id != request.user.id:
                Notification.objects.create(
                    user=anomalie.created_by,
                    verb=f"Votre anomalie « {anomalie.titre} » est passée au statut : {anomalie.get_statut_display()}",
                )
            messages.success(request, f"Statut mis à jour : {anomalie.get_statut_display()}.")
        return redirect('anomalie-detail', pk=anomalie.pk)


class AnomalieConvertirView(LoginRequiredMixin, View):
    """Convertit l'anomalie en ticket correctif — possible uniquement si un
    équipement (matériel ou installation) est identifié et si elle n'a pas
    déjà été convertie."""

    def post(self, request, pk):
        if not _est_chef(request.user):
            raise PermissionDenied
        anomalie = _anomalie_visible_ou_404(request.user, pk)
        if anomalie.ticket_id:
            messages.info(request, "Cette anomalie a déjà été convertie en ticket correctif.")
            return redirect('ticket-detail', pk=anomalie.ticket_id)
        if not anomalie.equipement_lie:
            messages.error(request, "Conversion impossible : aucun équipement n'est rattaché à cette anomalie.")
            return redirect('anomalie-detail', pk=anomalie.pk)
        description = anomalie.titre + (f"\n{anomalie.description}" if anomalie.description else "")
        with transaction.atomic():
            ticket = CorrectiveTicket.objects.create(
                asset=anomalie.asset, installation=anomalie.installation, description=description, severity=anomalie.gravite,
                created_by=request.user, updated_by=request.user,
            )
            TicketStatusLog.objects.create(
                ticket=ticket, old_status='REPORTED', new_status='REPORTED', user=request.user,
                note=f"Créé depuis l'anomalie « {anomalie.titre} »",
            )
            ancien = anomalie.statut
            anomalie.ticket = ticket
            anomalie.updated_by = request.user
            champs = ['ticket', 'updated_by', 'updated_at']
            if ancien == 'SIGNALEE':
                anomalie.statut = 'PRISE_EN_COMPTE'
                champs.append('statut')
            anomalie.save(update_fields=champs)
            AnomalieStatutLog.objects.create(
                anomalie=anomalie, ancien_statut=ancien, nouveau_statut=anomalie.statut, user=request.user,
                note="Convertie en ticket correctif",
            )
            AuditLog.objects.create(
                actor=request.user, action='anomalie_convertie_ticket',
                details=f'anomalie={anomalie.pk}; ticket={ticket.pk}',
            )
        messages.success(request, "Anomalie convertie en ticket correctif.")
        return redirect('ticket-detail', pk=ticket.pk)


class AnomalieCommentView(LoginRequiredMixin, View):
    """Commentaire de suivi (fil `threads`), ouvert à quiconque peut voir l'anomalie."""

    def post(self, request, pk):
        anomalie = _anomalie_visible_ou_404(request.user, pk)
        corps = request.POST.get('body', '').strip()
        if corps:
            ajouter_commentaire(anomalie, request.user, corps)
            messages.success(request, "Commentaire ajouté.")
        else:
            messages.error(request, "Le commentaire ne peut pas être vide.")
        return redirect('anomalie-detail', pk=anomalie.pk)
