"""Vues du plan visuel du navire (assets/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py ») :
configuration des ponts (Deck) et positionnement précis du matériel dessus
(PlanNavireListView/PlanNavireDeckView, réservées CHEF_SERVICE+), ainsi que
la consultation en lecture seule ouverte à tous les rôles
(PlanNavireVueView/PlanNavireVueDeckView).

Refactor pur : reproduit exactement le comportement d'origine, aucun import
depuis assets/web_views.py n'est nécessaire (aucune dépendance croisée)."""
import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import View

from matrix.core.roles import user_role_level
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.scopes import is_master_admin, ship_id_for_user
from matrix.core.validators import message_erreur_fichier, valider_photo
from org.models import Ship

from .models import Asset, Deck


def _peut_configurer_plan_navire(user):
    """Seuls les CHEF_SERVICE et rôles supérieurs (par défaut, seuil
    configurable par navire : matrix/core/role_thresholds.py,
    "plan_navire_configuration") peuvent configurer les ponts et zones du
    plan visuel du navire : une action de configuration structurante, pas
    une simple consultation."""
    return user_role_level(user) >= niveau_requis_pour(user, "plan_navire_configuration")


def _valider_coordonnee_pourcent(valeur):
    """Décode et valide une coordonnée (x ou y) postée par l'éditeur de plan
    (épingle de matériel) : un nombre en pourcentage (0-100) de la largeur/
    hauteur de l'image du pont. Renvoie None si le format est invalide (ex:
    manipulation du formulaire), plutôt que de lever une exception —
    l'appelant affiche alors un message d'erreur simple et ne modifie pas la
    position existante."""
    try:
        nombre = float(valeur)
    except (TypeError, ValueError):
        return None
    if not (0 <= nombre <= 100):
        return None
    return round(nombre, 2)


def _navire_selectionne(request):
    """Détermine le navire à configurer pour le plan visuel (ponts/zones).

    Un utilisateur rattaché à un navire précis (ship_id_for_user) ne peut
    configurer que celui-ci. Un utilisateur à accès flotte entière
    (is_master_admin, cf. matrix/core/scopes.py) choisit le navire via le
    sélecteur ?navire=, même principe que le sélecteur de navire de
    SettingsView (matrix/views.py). Renvoie (navire, liste_des_navires ou None
    si l'utilisateur n'a pas de sélecteur à afficher)."""
    if is_master_admin(request.user):
        navires = list(Ship.objects.order_by('name'))
        navire_id = request.GET.get('navire') or request.POST.get('navire_id')
        navire = None
        if navire_id:
            navire = next((n for n in navires if str(n.pk) == str(navire_id)), None)
        if navire is None:
            navire = navires[0] if navires else None
        return navire, navires
    navire_id = ship_id_for_user(request.user)
    navire = Ship.objects.filter(pk=navire_id).first() if navire_id else None
    return navire, None


class PlanNavireListView(LoginRequiredMixin, View):
    """Configuration des ponts d'un navire (Deck) : création, renommage,
    réordonnancement, suppression, et accès à l'éditeur de zones de chaque
    pont (voir PlanNavireDeckView ci-dessous).

    Réservée aux CHEF_SERVICE et rôles supérieurs (_peut_configurer_plan_navire),
    restreinte au navire de l'utilisateur — voir _navire_selectionne."""

    template_name = 'assets/plan_navire_list.html'

    def dispatch(self, request, *args, **kwargs):
        if not _peut_configurer_plan_navire(request.user):
            raise PermissionDenied("Réservé aux chefs de service et aux rôles supérieurs.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        navire, navires = _navire_selectionne(request)
        contexte = {
            'navire': navire,
            'navires': navires,
            'multi_navires': navires is not None,
        }
        if navire is not None:
            contexte['ponts'] = Deck.objects.filter(ship=navire).order_by('order', 'name')
        return render(request, self.template_name, contexte)

    def post(self, request):
        navire, _navires = _navire_selectionne(request)
        if navire is None:
            messages.error(request, "Aucune unité sélectionnée : impossible de configurer un pont.")
            return redirect('plan-navire-list')

        action = request.POST.get('action')
        if action == 'create_deck':
            nom = request.POST.get('name', '').strip()
            if not nom:
                messages.error(request, "Le nom du pont est obligatoire.")
            else:
                ordre_max = Deck.objects.filter(ship=navire).aggregate(m=Max('order'))['m'] or 0
                Deck.objects.create(ship=navire, name=nom, order=ordre_max + 1)
                messages.success(request, "Pont créé.")
        elif action == 'rename_deck':
            pont = Deck.objects.filter(pk=request.POST.get('pk'), ship=navire).first()
            nom = request.POST.get('name', '').strip()
            if pont and nom:
                pont.name = nom
                pont.save(update_fields=['name'])
                messages.success(request, "Pont renommé.")
        elif action == 'delete_deck':
            supprimes, _detail = Deck.objects.filter(pk=request.POST.get('pk'), ship=navire).delete()
            if supprimes:
                messages.success(request, "Pont supprimé.")
        elif action in ('move_up', 'move_down'):
            pont = Deck.objects.filter(pk=request.POST.get('pk'), ship=navire).first()
            if pont:
                ponts = list(Deck.objects.filter(ship=navire).order_by('order', 'name'))
                idx = next((i for i, p in enumerate(ponts) if p.pk == pont.pk), None)
                cible = idx - 1 if action == 'move_up' else idx + 1
                if idx is not None and 0 <= cible < len(ponts):
                    autre = ponts[cible]
                    pont.order, autre.order = autre.order, pont.order
                    Deck.objects.bulk_update([pont, autre], ['order'])

        suffixe = f"?navire={navire.id}" if is_master_admin(request.user) else ""
        return redirect(f"{reverse('plan-navire-list')}{suffixe}")


def _pont_dans_perimetre(request, pk):
    """Renvoie le pont demandé si son navire correspond au périmètre de
    l'utilisateur (ou si celui-ci a un accès flotte entière), sinon lève un
    refus d'accès. Factorisé ici pour être partagé par l'éditeur du plan
    (PlanNavireDeckView, réservé CHEF_SERVICE+) et sa page de consultation
    (PlanNavireVueDeckView, ouverte à tous les rôles) : le contrôle de
    périmètre est identique, seul le seuil de rôle diffère entre les deux."""
    pont = get_object_or_404(Deck.objects.select_related('ship'), pk=pk)
    if not is_master_admin(request.user) and ship_id_for_user(request.user) != pont.ship_id:
        raise PermissionDenied("Ce pont n'appartient pas à votre unité.")
    return pont


class PlanNavireDeckView(LoginRequiredMixin, View):
    """Éditeur du plan d'un pont : téléversement de l'image de fond, et
    positionnement précis du matériel dessus par épingle (clic sur le plan,
    coordonnées en pourcentage — voir le script de assets/plan_navire_deck.html,
    en JS natif sans dépendance externe). Remplace l'ancien système de zones
    rectangulaires groupant plusieurs matériels par Emplacement (modèle Zone,
    supprimé) : chaque épingle représente désormais un seul matériel (Asset),
    positionné via Asset.plan_deck/position_x/position_y.

    Portée volontairement limitée au matériel mobile (Asset), comme l'était
    déjà l'ancien système de zones (Zone.etat_materiel ne traitait pas non
    plus les installations fixes) : ce n'est pas un oubli mais une reprise à
    l'identique du périmètre existant.

    Même seuil et même contrôle de périmètre que PlanNavireListView."""

    template_name = 'assets/plan_navire_deck.html'

    def dispatch(self, request, *args, **kwargs):
        if not _peut_configurer_plan_navire(request.user):
            raise PermissionDenied("Réservé aux chefs de service et aux rôles supérieurs.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        pont = _pont_dans_perimetre(request, pk)
        ponts_navire = list(Deck.objects.filter(ship=pont.ship).order_by('order', 'name'))
        idx = next((i for i, p in enumerate(ponts_navire) if p.pk == pont.pk), 0)
        materiels_navire = list(
            Asset.objects.filter(ship=pont.ship).select_related('asset_type', 'plan_deck').order_by('asset_type__name')
        )
        positionnes = [a for a in materiels_navire if a.plan_deck_id == pont.pk]

        def _libelle_option(a):
            if a.plan_deck_id == pont.pk:
                return f"{a} — déjà positionné ici"
            if a.plan_deck_id:
                return f"{a} — actuellement sur {a.plan_deck.name}"
            return str(a)

        contexte = {
            'pont': pont,
            'positionnes': positionnes,
            'materiels': materiels_navire,
            'materiels_options': [{'id': str(a.id), 'label': _libelle_option(a)} for a in materiels_navire],
            'pins_json': json.dumps([
                {'id': str(a.id), 'label': str(a), 'x': a.position_x, 'y': a.position_y}
                for a in positionnes if a.position_x is not None and a.position_y is not None
            ]),
            'pont_precedent': ponts_navire[idx - 1] if idx > 0 else None,
            'pont_suivant': ponts_navire[idx + 1] if idx < len(ponts_navire) - 1 else None,
        }
        return render(request, self.template_name, contexte)

    def post(self, request, pk):
        pont = _pont_dans_perimetre(request, pk)
        action = request.POST.get('action')

        if action == 'upload_image':
            image = request.FILES.get('image')
            erreur_image = message_erreur_fichier(image, valider_photo)
            if erreur_image:
                messages.error(request, erreur_image)
            elif image:
                pont.image = image
                pont.save(update_fields=['image'])
                messages.success(request, "Image du plan mise à jour.")
            else:
                messages.error(request, "Aucune image sélectionnée.")
        elif action == 'place_pin':
            self._positionner_materiel(request, pont)
        elif action == 'remove_pin':
            materiel = Asset.objects.filter(pk=request.POST.get('asset_id'), ship=pont.ship, plan_deck=pont).first()
            if materiel:
                materiel.plan_deck = None
                materiel.position_x = None
                materiel.position_y = None
                materiel.save(update_fields=['plan_deck', 'position_x', 'position_y'])
                messages.success(request, "Matériel retiré du plan.")

        return redirect('plan-navire-deck', pk=pont.pk)

    def _positionner_materiel(self, request, pont):
        materiel = Asset.objects.filter(pk=request.POST.get('asset_id'), ship=pont.ship).first()
        if materiel is None:
            messages.error(request, "Matériel introuvable ou hors de votre unité.")
            return
        x = _valider_coordonnee_pourcent(request.POST.get('x'))
        y = _valider_coordonnee_pourcent(request.POST.get('y'))
        if x is None or y is None:
            messages.error(request, "Position invalide : cliquez à nouveau sur le plan.")
            return
        materiel.plan_deck = pont
        materiel.position_x = x
        materiel.position_y = y
        materiel.save(update_fields=['plan_deck', 'position_x', 'position_y'])
        messages.success(request, f"« {materiel} » positionné sur le plan.")


class PlanNavireVueView(LoginRequiredMixin, View):
    """Point d'entrée de la consultation du plan visuel du navire (rendu final
    de la sous-tâche 3/3), ouverte à tous les rôles — contrairement à
    PlanNavireListView (réservée CHEF_SERVICE+), voir la distinction des deux
    entrées de navigation dans base.html. Redirige vers le premier pont du
    navire de l'utilisateur (dans l'ordre Deck.order), ou affiche un message
    clair si aucun pont n'est encore configuré plutôt qu'une page cassée."""

    template_name = 'assets/plan_navire_vue.html'

    def get(self, request):
        navire, navires = _navire_selectionne(request)
        if navire is None:
            return render(request, self.template_name, {
                'navire': None, 'navires': navires, 'multi_navires': navires is not None,
            })
        premier_pont = Deck.objects.filter(ship=navire).order_by('order', 'name').first()
        if premier_pont is None:
            return render(request, self.template_name, {
                'navire': navire, 'navires': navires, 'multi_navires': navires is not None,
                'aucun_pont': True,
            })
        suffixe = f"?navire={navire.id}" if is_master_admin(request.user) else ""
        return redirect(f"{reverse('plan-navire-vue-deck', kwargs={'pk': premier_pont.pk})}{suffixe}")


class PlanNavireVueDeckView(LoginRequiredMixin, View):
    """Consultation en lecture seule du plan d'un pont : navigation par
    onglets entre les ponts du navire (dans l'ordre Deck.order), épingles de
    matériel affichées en overlay avec un code couleur selon l'état de CE
    matériel (cf. Asset.etat_plan), et clic sur une épingle pour ouvrir
    directement sa fiche (AssetDetailView) — remplace l'ancien clic sur une
    zone qui ouvrait une liste de matériel groupé par emplacement.

    Ouverte à tous les rôles (contrairement à PlanNavireDeckView) : seul le
    contrôle de périmètre (navire de l'utilisateur) est conservé, via la même
    fonction _pont_dans_perimetre que l'éditeur."""

    template_name = 'assets/plan_navire_vue.html'

    def get(self, request, pk):
        pont = _pont_dans_perimetre(request, pk)
        ponts_navire = list(Deck.objects.filter(ship=pont.ship).order_by('order', 'name'))
        materiels = list(
            Asset.objects.filter(plan_deck=pont, position_x__isnull=False, position_y__isnull=False)
            .select_related('asset_type').order_by('asset_type__name')
        )
        epingles = [
            {
                'materiel': materiel,
                'etat': materiel.etat_plan,
                'url_materiel': reverse('asset-detail', kwargs={'pk': materiel.pk}),
            }
            for materiel in materiels
        ]
        contexte = {
            'navire': pont.ship,
            'pont': pont,
            'ponts': ponts_navire,
            'epingles': epingles,
            'multi_navires': is_master_admin(request.user),
        }
        return render(request, self.template_name, contexte)
