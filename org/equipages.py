"""Double équipage (FREMM, PSP, BSAM) : deux équipages alternent sur un même
bâtiment (page Notion « Organigramme et rôles » §9 et §11).

Règle de partage : installations, matériel, fiches, historique, relevés, stock
et plan du navire appartiennent au BÂTIMENT ; les personnes (et, dans les
tranches suivantes, l'organisation (org/miroir.py), les quarts, les assignations et les
notifications) dépendent de l'ÉQUIPAGE. L'équipage à terre garde l'accès en
LECTURE SEULE : `est_en_lecture_seule()` est le point d'entrée unique, appliqué
par le middleware `LectureSeuleEquipageMiddleware` et par `RolePermission`.

Un navire dont `double_equipage` est faux se comporte exactement comme avant :
aucun équipage, aucune restriction. Toute modification est tracée (AuditLog)."""
import re
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.roles import user_role_level
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.scopes import is_master_admin, ship_id_for_user

from . import miroir, passation
from .models import Equipage, Ship

User = get_user_model()

# Seules ces classes de bâtiments fonctionnent en double équipage (décision du
# 23/09/2026). Comparaison sur mot entier, sans tenir compte de la casse.
CLASSES_DOUBLE_EQUIPAGE = ("FREMM", "PSP", "BSAM")
NOMS_EQUIPAGES_PAR_DEFAUT = ("Bleu", "Rouge")

ACTIONS = (
    "activer_double_equipage",
    "desactiver_double_equipage",
    "renommer_equipage",
    "affecter_equipage_marin",
    "planifier_releve",
    "annuler_releve",
    "dupliquer_organisation",
)


# Écritures restant permises à l'équipage à terre (espace personnel sans effet
# sur le bâtiment) : (méthode, motif de chemin). Connexion, déconnexion et
# compte (mot de passe) sont toujours permis.
ECRITURES_AUTORISEES = (
    ("POST", re.compile(r"^/api/notifications/notifications/mark_all_read/$")),
    ("PATCH", re.compile(r"^/api/notifications/notifications/\d+/$")),
    ("POST", re.compile(r"^/api/notifications/push/(subscribe|unsubscribe)/$")),
    ("POST", re.compile(r"^/(login|logout)/$")),
    ("POST", re.compile(r"^/accounts/")),
)


def ecriture_autorisee_a_terre(methode, chemin):
    """Vrai si cette requête d'écriture reste permise à l'équipage à terre."""
    return any(m == methode and motif.match(chemin) for m, motif in ECRITURES_AUTORISEES)


def peut_gerer_equipages(user):
    """Seuil configurable « equipage_gestion », sur le navire de l'appelant."""
    return user_role_level(user) >= niveau_requis_pour(user, "equipage_gestion")


def navire_eligible(ship):
    """Vrai si la classe du bâtiment autorise le double équipage."""
    mots = re.findall(r"[A-Za-z0-9]+", (ship.classe_navire or "").upper())
    return any(classe in mots for classe in CLASSES_DOUBLE_EQUIPAGE)


def equipage_a_bord(ship, jour=None):
    """Équipage réellement à bord à la date donnée (aujourd'hui par défaut),
    en tenant compte d'une relève planifiée arrivée à échéance. None pour un
    navire à équipage unique."""
    if not ship.double_equipage:
        return None
    jour = jour or timezone.localdate()
    if ship.equipage_releve_id and ship.date_releve and ship.date_releve <= jour:
        return ship.equipage_releve
    return ship.equipage_a_bord


def est_en_lecture_seule(user, jour=None):
    """Vrai si l'utilisateur appartient à l'équipage à terre d'un bâtiment à
    double équipage : il consulte, sans rien modifier. Jamais vrai pour un
    administrateur général, pour un marin sans équipage, ni sur un bâtiment à
    équipage unique (comportement strictement inchangé)."""
    if not getattr(user, "is_authenticated", False) or is_master_admin(user):
        return False
    profile = getattr(user, "profile", None)
    if profile is None or not profile.equipage_id or profile.role == "ADMIN_NAVIRE":
        # L'administrateur d'unité gère la plateforme, pas le fonctionnement
        # métier d'un équipage : c'est le plan de secours pour corriger la relève.
        return False
    equipage = profile.equipage
    if equipage.ship_id != profile.navire_id_effectif:
        return False
    ship = equipage.ship
    if not ship.double_equipage:
        return False
    a_bord = equipage_a_bord(ship, jour)
    return a_bord is not None and a_bord.pk != profile.equipage_id


def _marins_du_navire(ship):
    """Utilisateurs rattachés à ce navire, à n'importe quel niveau."""
    return User.objects.filter(
        Q(profile__ship=ship) | Q(profile__service__ship=ship)
        | Q(profile__sector__service__ship=ship) | Q(profile__section__sector__service__ship=ship)
    ).distinct()


def contexte_page(ship):
    """Données de la page « Équipages », pour le navire donné (ou None)."""
    if ship is None:
        return {"eq_ship": None}
    contexte = {"eq_ship": ship, "eq_eligible": navire_eligible(ship)}
    if not ship.double_equipage:
        return contexte
    a_bord = equipage_a_bord(ship)
    marins = list(
        _marins_du_navire(ship).filter(is_active=True)
        .select_related("profile", "profile__equipage")
        .order_by("last_name", "first_name", "username")
    )
    releve = ship.equipage_releve if ship.equipage_releve_id and ship.equipage_releve_id != getattr(a_bord, "pk", None) else None
    contexte.update({
        "eq_equipages": [
            {
                "equipage": e,
                "a_bord": a_bord is not None and e.pk == a_bord.pk,
                "nb_marins": sum(1 for m in marins if m.profile.equipage_id == e.pk),
                "nb_services": e.services.count(),
            }
            for e in ship.equipages.all()
        ],
        "eq_a_bord": a_bord,
        "eq_releve_planifiee": releve,
        "eq_marins": marins,
        "eq_sans_equipage": sum(1 for m in marins if m.profile.equipage_id is None),
        "eq_historique": AuditLog.objects.filter(
            action__in=("equipage_releve", "equipage_releve_planifiee"),
            details__startswith=f"navire={ship.name};",
        ).select_related("actor").order_by("-created_at")[:10],
        "eq_aujourdhui": timezone.localdate(),
        "eq_passations": ship.syntheses_passation.select_related("equipage_montant", "equipage_descendant")[:5],
    })
    return contexte


def _navire_cible(request):
    if is_master_admin(request.user):
        return Ship.objects.filter(pk=request.POST.get("ship_id")).first()
    return Ship.objects.filter(pk=ship_id_for_user(request.user)).first()


def _tracer(request, action, ship, detail):
    AuditLog.objects.create(actor=request.user, action=action, details=f"navire={ship.name}; {detail}")


def traiter_action(request, action):
    """Exécute une action de la page (déjà autorisée par la vue), limitée au
    navire de l'appelant (ou au navire choisi par un administrateur général)."""
    ship = _navire_cible(request)
    if ship is None:
        messages.error(request, "Aucune unité sélectionnée.")
        return
    if action == "activer_double_equipage":
        _activer(request, ship)
        return
    if not ship.double_equipage:
        messages.error(request, "Le double équipage n'est pas activé sur cette unité.")
        return
    if action == "desactiver_double_equipage":
        ship.double_equipage = False
        ship.save(update_fields=["double_equipage", "updated_at"])
        _tracer(request, action, ship, "équipages et rattachements conservés")
        messages.success(request, "Double équipage désactivé : plus aucune restriction de lecture seule.")
    elif action == "renommer_equipage":
        _renommer(request, ship)
    elif action == "affecter_equipage_marin":
        _affecter(request, ship)
    elif action == "planifier_releve":
        _planifier_releve(request, ship)
    elif action == "annuler_releve":
        _annuler_releve(request, ship)
    elif action == "dupliquer_organisation":
        miroir.dupliquer_vers_l_autre_equipage(request, ship)


def _activer(request, ship):
    if not navire_eligible(ship):
        messages.error(
            request, "Le double équipage ne concerne que les FREMM, PSP et BSAM : renseignez la classe du bâtiment."
        )
        return
    if ship.double_equipage:
        messages.warning(request, "Le double équipage est déjà activé.")
        return
    for nom in NOMS_EQUIPAGES_PAR_DEFAUT:
        Equipage.objects.get_or_create(ship=ship, nom=nom)
    ship.double_equipage = True
    if ship.equipage_a_bord_id is None:
        ship.equipage_a_bord = ship.equipages.order_by("nom").first()
    ship.save(update_fields=["double_equipage", "equipage_a_bord", "updated_at"])
    miroir.rattacher_organisation_existante(ship, ship.equipage_a_bord)
    _tracer(request, "activer_double_equipage", ship, f"equipage_a_bord={ship.equipage_a_bord.nom}")
    messages.success(request, f"Double équipage activé sur {ship.name}.")


def _equipage_du_navire(ship, pk):
    return ship.equipages.filter(pk=pk).first() if pk and str(pk).isdigit() else None


def _renommer(request, ship):
    equipage = _equipage_du_navire(ship, request.POST.get("pk"))
    nom = (request.POST.get("nom") or "").strip()[:50]
    if equipage is None or not nom:
        messages.error(request, "Équipage introuvable ou nom vide.")
    elif ship.equipages.filter(nom=nom).exclude(pk=equipage.pk).exists():
        messages.error(request, "Ce nom est déjà utilisé par l'autre équipage.")
    else:
        ancien, equipage.nom = equipage.nom, nom
        equipage.save(update_fields=["nom", "updated_at"])
        _tracer(request, "renommer_equipage", ship, f"{ancien} -> {nom}")
        messages.success(request, f"Équipage renommé en « {nom} ».")


def _peut_se_verrouiller(user):
    """Faux pour l'administrateur d'unité et l'administrateur général, jamais
    mis en lecture seule (voir est_en_lecture_seule)."""
    return not is_master_admin(user) and user.profile.role != "ADMIN_NAVIRE"


def _affecter(request, ship):
    user_id = request.POST.get("user_id") or ""
    cible = _marins_du_navire(ship).filter(pk=user_id).first() if user_id.isdigit() else None
    equipage_id = request.POST.get("equipage_id") or ""
    equipage = _equipage_du_navire(ship, equipage_id) if equipage_id else None
    if cible is None or (equipage_id and equipage is None):
        messages.error(request, "Marin ou équipage introuvable sur cette unité.")
        return
    if cible == request.user and equipage is not None and equipage != equipage_a_bord(ship) and _peut_se_verrouiller(cible):
        messages.error(
            request, "Vous ne pouvez pas vous affecter à l'équipage à terre : vous perdriez vos droits d'écriture."
        )
        return
    profil = cible.profile
    ancien = profil.equipage.nom if profil.equipage else "aucun"
    profil.equipage = equipage
    profil.save(update_fields=["equipage", "updated_at"])
    AuditLog.objects.create(
        actor=request.user, target_user=cible, action="affecter_equipage_marin",
        details=f"navire={ship.name}; {ancien} -> {equipage.nom if equipage else 'aucun'}",
    )
    messages.success(request, f"{cible.get_full_name() or cible.username} : équipage mis à jour.")


def _planifier_releve(request, ship):
    equipage = _equipage_du_navire(ship, request.POST.get("equipage_id"))
    try:
        jour = date.fromisoformat(request.POST.get("date") or timezone.localdate().isoformat())
    except ValueError:
        messages.error(request, "Date de relève invalide.")
        return
    if equipage is None:
        messages.error(request, "Équipage introuvable sur cette unité.")
        return
    ancien = equipage_a_bord(ship)
    if ancien == equipage and jour <= timezone.localdate():
        messages.warning(request, f"L'équipage {equipage.nom} est déjà à bord.")
        return
    nom_ancien = ancien.nom if ancien else "aucun"
    propre = request.user.profile.equipage
    se_verrouille = propre is not None and propre != equipage and _peut_se_verrouiller(request.user)
    if jour <= timezone.localdate() and se_verrouille:
        messages.error(
            request, "Cette relève mettrait votre propre équipage à terre : vous perdriez vos droits d'écriture. "
            "Demandez-la à un membre de l'équipage montant ou à l'administrateur d'unité.",
        )
        return
    if jour > timezone.localdate() and se_verrouille:
        messages.warning(request, f"Attention : à partir du {jour:%d/%m/%Y}, votre équipage sera à terre (lecture seule).")
    if jour <= timezone.localdate():
        # Relève immédiate : l'équipage montant devient l'équipage à bord.
        ship.equipage_a_bord, ship.equipage_releve, ship.date_releve = equipage, None, jour
        action = "equipage_releve"
        message = (
            f"Relève effectuée : l'équipage {equipage.nom} est à bord, "
            f"l'équipage {nom_ancien} passe à terre (lecture seule)."
        )
    else:
        # On fige d'abord l'équipage réellement à bord (une relève précédente
        # arrivée à échéance n'a pas été « consolidée » dans equipage_a_bord).
        ship.equipage_a_bord = ancien
        ship.equipage_releve, ship.date_releve = equipage, jour
        action = "equipage_releve_planifiee"
        message = f"Relève planifiée au {jour:%d/%m/%Y} : l'équipage {equipage.nom} montera à bord."
    with transaction.atomic():
        # Bascule, trace et synthèse de passation : tout ou rien.
        ship.save(update_fields=["equipage_a_bord", "equipage_releve", "date_releve", "updated_at"])
        _tracer(request, action, ship, f"{nom_ancien} -> {equipage.nom} au {jour.isoformat()}")
        if action == "equipage_releve":
            passation.generer_synthese(ship, equipage, ancien, jour)
    if action == "equipage_releve":
        message += " Synthèse de passation envoyée à l'équipage montant."
    messages.success(request, message)


def _annuler_releve(request, ship):
    a_bord = equipage_a_bord(ship)
    if ship.equipage_releve_id and ship.equipage_releve_id != getattr(a_bord, "pk", None):
        _tracer(request, "equipage_releve_planifiee", ship, f"annulation de la relève vers {ship.equipage_releve.nom}")
        ship.equipage_releve = None
        ship.date_releve = None
        ship.save(update_fields=["equipage_releve", "date_releve", "updated_at"])
        messages.success(request, "Relève planifiée annulée.")
    else:
        messages.warning(request, "Aucune relève planifiée.")
