"""Vues web transverses de Matrix : recherche globale et déconnexion.

Les Réglages (SettingsView) vivent dans matrix/settings_views.py ; ils sont
réexportés ici pour que `from .views import SettingsView` (matrix/urls.py)
continue de fonctionner."""
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from assets.models import Asset, AssetDocument, Installation
from logistics.models import CorrectiveTicket
from logistics.anomalie_views import anomalies_visibles
from django.contrib.auth.models import User
from training.models import TrainingCourse
from rondes.services import modeles_visibles, rondes_visibles
from quarts.models import EchangeService
from quarts.echanges import peut_valider_echange
from matrix.core.scopes import scope_filters_for_user
from .settings_views import SettingsView  # noqa: F401 — façade de réexport

@login_required
def global_search(request):
    # Recherche globale réservée aux utilisateurs connectés, restreinte à leur
    # périmètre (navire/service/secteur/section) via scope_filters_for_user —
    # pas de nouveau système de scope. Le matériel et les installations portent
    # directement les champs de périmètre ; les tickets, les documents et les
    # personnes n'en ont pas, on traduit donc le périmètre via la relation vers
    # le matériel (asset) ou le profil (profile).
    #
    # Couverture §37 cahier des charges (recherche universelle) — 9 types sur
    # les 9 listés à l'origine (matériel mobile, installations, tickets
    # correctifs, personnes, formations, documents, anomalies), plus deux
    # types livrés depuis (modèles de ronde/rondes, échanges de service) hors
    # de l'énumération initiale mais tout aussi cherchables au quotidien.
    # Volontairement hors périmètre de cette itération (cf. commentaire
    # Notion de la tâche) : tâches (aucun modèle "Tâche" unique n'existe — un
    # marin suit ses échéances via son espace personnel, pas via un objet
    # cherchable dédié), événements de calendrier et discussions — pour
    # éviter la sur-ingénierie et prioriser les types les plus utiles au
    # quotidien en premier.
    q = request.GET.get('q', '').strip()
    perimetre = scope_filters_for_user(request.user)
    perimetre_tickets = Q()
    for cle, valeur in perimetre.items():
        perimetre_tickets |= Q(**{f"asset__{cle}": valeur}) | Q(**{f"installation__{cle}": valeur})
    perimetre_documents = {f"asset__{cle}": valeur for cle, valeur in perimetre.items()}
    perimetre_users = {f"profile__{cle}": valeur for cle, valeur in perimetre.items()}
    assets = tickets = users = installations = formations = documents = []
    anomalies = ronde_modeles = rondes = echanges = []
    if q:
        assets = Asset.objects.filter(**perimetre).filter(
            Q(internal_id__icontains=q) | Q(serial_number__icontains=q)
        )[:20]
        tickets = CorrectiveTicket.objects.filter(perimetre_tickets).filter(
            Q(description__icontains=q) | Q(id__icontains=q)
        )[:20]
        users = User.objects.filter(**perimetre_users).filter(
            Q(username__icontains=q) | Q(email__icontains=q)
        )[:20]
        installations = Installation.objects.select_related('ship', 'service', 'sector').filter(**perimetre).filter(
            Q(designation__icontains=q) | Q(reference__icontains=q)
        )[:20]
        # Formation : fiche UNIQUE et globale (pas de rattachement navire, cf.
        # TrainingCourse et TrainingCourseListView) — même filtre "catalogue
        # actif" que la liste des formations, aucun périmètre supplémentaire à
        # appliquer puisque le référentiel est déjà commun à toute la flotte.
        formations = TrainingCourse.objects.filter(statut_validation="ACTIVE").filter(
            Q(title__icontains=q) | Q(category__icontains=q)
        )[:20]
        documents = AssetDocument.objects.select_related('asset').filter(**perimetre_documents).filter(
            Q(name__icontains=q)
        )[:20]
        # Anomalies : périmètre propre à l'app logistics (pas
        # scope_filters_for_user) — un équipier voit ses signalements +ceux de
        # sa section, un chef voit tout son périmètre + les siens — même
        # fonction que la liste des anomalies (AnomalieListView).
        anomalies = anomalies_visibles(request.user).filter(
            Q(titre__icontains=q) | Q(description__icontains=q) | Q(localisation__icontains=q)
        )[:20]
        # Rondes : périmètre "couvrant" propre à l'app rondes (un chef de
        # secteur/service/navire voit aussi ce qui est en dessous de lui) —
        # mêmes fonctions que RondesIndexView/ModeleListView.
        ronde_modeles = modeles_visibles(request.user).filter(
            Q(nom__icontains=q) | Q(description__icontains=q)
        )[:20]
        rondes = rondes_visibles(request.user).filter(Q(nom__icontains=q))[:20]
        # Échanges de service : aucun périmètre géographique simple — visible
        # seulement du demandeur, de la cible, ou du chef de liste habilité à
        # trancher (même règle que _echanges_visibles, quarts/echanges_views.py).
        # Filtrage en Python après un premier filtre texte en base, faute de
        # traduire cette règle en un Q() unique.
        candidats_echanges = EchangeService.objects.select_related(
            'demandeur', 'cible', 'creneau_demandeur__service_garde', 'creneau_cible__service_garde',
        ).filter(
            Q(libelle_creneau_demandeur__icontains=q) | Q(libelle_creneau_cible__icontains=q) | Q(motif__icontains=q)
        )
        echanges = [
            e for e in candidats_echanges
            if request.user.pk in (e.demandeur_id, e.cible_id) or peut_valider_echange(request.user, e)
        ][:20]
    return render(request, 'search.html', {
        "q": q, "assets": assets, "tickets": tickets, "users": users,
        "installations": installations, "formations": formations, "documents": documents,
        "anomalies": anomalies, "ronde_modeles": ronde_modeles, "rondes": rondes, "echanges": echanges,
    })



def logout_then_login(request):
    # Déconnexion simple puis redirection immédiate vers la page de connexion
    logout(request)
    return redirect('/login/')

