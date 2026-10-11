"""Règles métier des postes du bord : droits, affectation et tableau d'effectifs (signalement, jamais de blocage)."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog
from annonces.services import chaine, cible_permise, cibles_autorisees, resoudre_cible
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import RoleLevel, user_role_level
from training.models import TrainingCourse, TrainingRecord

from .models import AffectationPoste, Poste

User = get_user_model()


def peut_gerer(user):
    return (
        not equipage_a_terre_lecture_seule(user)
        and user_role_level(user) >= niveau_requis_pour(user, "poste_gestion")
        and bool(cibles_autorisees(user))
    )


def _noeud(poste):
    for modele in ("section", "sector", "service"):
        if getattr(poste, f"{modele}_id"):
            return f"{modele}:{getattr(poste, f'{modele}_id')}"
    return f"ship:{poste.ship_id}"


def peut_gerer_poste(user, poste):
    """Le poste doit être dans le périmètre de saisie de `user`."""
    return peut_gerer(user) and cible_permise(user, _noeud(poste))


def postes_visibles(user):
    """Postes que `user` tient, et ceux de son périmètre s'il est chef (CHEF_SECTION et au-dessus)."""
    filtre = Q(affectations__user=user)
    if user_role_level(user) >= RoleLevel.CHEF_SECTION:
        ship = chaine(user)[0]
        cles = [c for c, _ in cibles_autorisees(user)]
        for modele in ("ship", "service", "sector", "section"):
            ids = [int(c.split(":")[1]) for c in cles if c.startswith(f"{modele}:")]
            if ids and ship:
                filtre |= Q(**{f"{modele}_id__in": ids}, ship_id=ship)
    return Poste.objects.filter(filtre).distinct()


def creer_poste(user, intitule, cible, effectif=1, equipage="", formations_ids=()):
    if not peut_gerer(user):
        raise PermissionError("Vous ne pouvez pas créer de poste.")
    if not cible_permise(user, cible):
        raise PermissionError("Ce rattachement est hors de votre périmètre.")
    if not intitule.strip():
        raise ValidationError("L'intitulé est obligatoire.")
    if effectif < 1:
        raise ValidationError("L'effectif requis est d'au moins 1.")
    poste = Poste.objects.create(
        intitule=intitule.strip(), effectif=effectif, equipage=equipage.strip(), created_by=user, updated_by=user,
        **resoudre_cible(cible),
    )
    poste.formations.set(TrainingCourse.objects.filter(pk__in=formations_ids))
    AuditLog.objects.create(actor=user, action="poste_cree", details=f"poste={poste.pk}")
    return poste


def modifier_formations(user, poste, formations_ids):
    if not peut_gerer_poste(user, poste):
        raise PermissionError("Vous ne pouvez pas modifier ce poste.")
    poste.formations.set(TrainingCourse.objects.filter(pk__in=formations_ids))
    AuditLog.objects.create(actor=user, action="poste_formations", details=f"poste={poste.pk}")


def affecter(user, poste, marin):
    """Affecte un marin du bâtiment ; ses qualifications manquantes ne bloquent pas, elles sont signalées."""
    if not peut_gerer_poste(user, poste):
        raise PermissionError("Vous ne pouvez pas affecter sur ce poste.")
    if marin.profile.ship_id != poste.ship_id or not marin.is_active:
        raise ValidationError("Ce marin n'appartient pas au bâtiment du poste.")
    AffectationPoste.objects.get_or_create(poste=poste, user=marin, defaults={"affecte_par": user})
    AuditLog.objects.create(actor=user, action="poste_affectation", target_user=marin, details=f"poste={poste.pk}; affecte")


def retirer(user, poste, marin):
    if not peut_gerer_poste(user, poste):
        raise PermissionError("Vous ne pouvez pas modifier ce poste.")
    if AffectationPoste.objects.filter(poste=poste, user=marin).delete()[0]:
        AuditLog.objects.create(actor=user, action="poste_affectation", target_user=marin, details=f"poste={poste.pk}; retire")


def tableau_effectifs(user):
    """Une ligne par poste visible : titulaires, effectif pourvu et qualifications manquantes de chacun.

    Un chef voit tous les titulaires de son périmètre ; un marin ne voit que ses propres postes et son propre état."""
    chef = user_role_level(user) >= RoleLevel.CHEF_SECTION
    postes = list(postes_visibles(user).select_related("ship", "service", "sector", "section").prefetch_related(
        "formations", "affectations__user"))
    marins = {a.user_id for p in postes for a in p.affectations.all()}
    formations = {f.pk for p in postes for f in p.formations.all()}
    valides = {}
    for user_id, course_id in TrainingRecord.objects.filter(
            user_id__in=marins, course_id__in=formations, expires_at__gte=timezone.localdate()).values_list("user_id", "course_id"):
        valides.setdefault(user_id, set()).add(course_id)
    lignes = []
    for poste in postes:
        titulaires = []
        for a in poste.affectations.all():
            if not chef and a.user_id != user.pk:
                continue
            manquantes = [f for f in poste.formations.all() if f.pk not in valides.get(a.user_id, set())]
            titulaires.append({"user": a.user, "manquantes": manquantes})
        affectes = poste.affectations.count()
        lignes.append({
            "poste": poste, "titulaires": titulaires, "affectes": affectes,
            "non_pourvu": max(poste.effectif - affectes, 0), "sous_qualifies": sum(1 for t in titulaires if t["manquantes"]),
        })
    lignes.sort(key=lambda l: (-l["non_pourvu"], -l["sous_qualifies"], l["poste"].intitule))
    return lignes
