"""Chef du responsable de spécialité : helpers de résolution et actions de
l'écran de gestion (onglet « Utilisateurs » des Réglages). Prérequis du circuit
de publication des fiches matériel flotte (page Notion « Organigramme et
rôles ») : le chef visé est celui DU responsable de la spécialité concernée.
Toute modification est tracée dans l'AuditLog unifié."""
from django.contrib import messages
from django.contrib.auth import get_user_model

from matrix.core.saisie import entier_ou_none

from .models import AuditLog, ChefResponsableSpecialite, ResponsableSpecialite

User = get_user_model()

ACTIONS = ("definir_chef_responsable", "retirer_chef_responsable")


def chefs_du_responsable(responsable):
    """Chefs qui encadrent ce responsable de spécialité (liste éventuellement
    vide : un responsable sans chef est toléré, cf. responsables_sans_chef)."""
    return User.objects.filter(encadrement_responsables_specialite__responsables=responsable).distinct()


def qui_vise(specialite):
    """Utilisateurs habilités à viser une fiche de la spécialité : les chefs des
    responsables de CETTE spécialité, et eux seuls. Vide si aucun responsable
    n'a de chef (le circuit de publication devra alors le signaler)."""
    return User.objects.filter(
        encadrement_responsables_specialite__responsables__specialite=specialite
    ).distinct()


def peut_viser(user, specialite):
    return qui_vise(specialite).filter(pk=user.pk).exists()


def responsables_sans_chef():
    """Responsables de spécialité qu'aucun chef n'encadre (à signaler)."""
    return ResponsableSpecialite.objects.filter(chefs__isnull=True).select_related("specialite", "user")


def chefs_qui_encadreraient_tous(exclus_pk=None):
    """Chefs qui encadreraient TOUS les responsables restants une fois le
    responsable `exclus_pk` retiré, alors qu'il en reste plus d'un (règle : un
    chef encadre plusieurs responsables mais pas tous)."""
    restants = set(ResponsableSpecialite.objects.exclude(pk=exclus_pk).values_list("pk", flat=True))
    if len(restants) <= 1:
        return []
    return [
        c for c in ChefResponsableSpecialite.objects.select_related("user")
        if restants <= set(c.responsables.values_list("pk", flat=True))
    ]


def contexte_ecran():
    """Données de l'écran : chefs, leurs responsables, et avertissements."""
    responsables = list(ResponsableSpecialite.objects.select_related("specialite", "user").order_by(
        "specialite__name", "user__last_name", "user__first_name"))
    chefs = list(ChefResponsableSpecialite.objects.select_related("user").prefetch_related(
        "responsables__specialite", "responsables__user").order_by("user__last_name", "user__first_name"))
    alertes = [
        f"{r.user.get_full_name() or r.user.username} (responsable « {r.specialite.name} ») n'a pas de chef : "
        "aucun visa possible avant publication d'une fiche de cette spécialité."
        for r in responsables_sans_chef()
    ]
    # Données déjà existantes uniquement : la saisie de ce cas est désormais refusée.
    alertes += [
        f"{c.user.get_full_name() or c.user.username} encadre tous les responsables de spécialité : "
        "un chef doit n'en encadrer qu'une partie. Modifiez sa sélection."
        for c in chefs_qui_encadreraient_tous()
    ]
    return {"chefs_responsables": chefs, "responsables_pour_chefs": responsables, "alertes_chefs": alertes}


def traiter_action(request, action):
    """Exécute une action de l'écran (déjà autorisée par la vue)."""
    if action == "definir_chef_responsable":
        marin = User.objects.filter(pk=entier_ou_none(request.POST.get("user_id")) or 0).first()
        ids = [i for i in map(entier_ou_none, request.POST.getlist("responsable_ids")) if i is not None]
        if marin is None:
            messages.error(request, "Marin introuvable.")
            return
        responsables = ResponsableSpecialite.objects.filter(pk__in=ids)
        if not responsables:
            messages.error(request, "Choisissez au moins un responsable de spécialité à encadrer.")
            return
        if responsables.filter(user=marin).exists():
            messages.error(request, "Un responsable de spécialité ne peut pas être son propre chef.")
            return
        if ResponsableSpecialite.objects.count() > 1 and responsables.count() == ResponsableSpecialite.objects.count():
            messages.error(
                request,
                "Un chef ne peut pas encadrer tous les responsables de spécialité : "
                "décochez-en au moins un. Rien n'a été enregistré.",
            )
            return
        chef, _ = ChefResponsableSpecialite.objects.get_or_create(user=marin)
        ancien = sorted(str(r.pk) for r in chef.responsables.all())
        chef.responsables.set(responsables)
        AuditLog.objects.create(
            actor=request.user, action=action, target_user=marin,
            details=f"responsables {','.join(ancien) or 'aucun'} -> {','.join(sorted(str(r.pk) for r in responsables))}",
        )
        messages.success(request, f"{marin.get_full_name() or marin.username} encadre {len(responsables)} responsable(s).")
    elif action == "retirer_chef_responsable":
        chef = ChefResponsableSpecialite.objects.filter(pk=request.POST.get("pk") or 0).first()
        if chef is None:
            messages.error(request, "Chef introuvable.")
            return
        AuditLog.objects.create(actor=request.user, action=action, target_user=chef.user, details=f"pk={chef.pk}")
        chef.delete()
        messages.success(request, "Chef de responsable(s) retiré.")
