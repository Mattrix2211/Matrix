"""Recherche globale par catégorie (docs/UX.md §21).

Chaque catégorie réutilise le périmètre de ses vues de liste et de détail
(``scope_filters_for_user``, ``build_scope_q``, ``anomalies_visibles``) : aucun
résultat ne mène à un objet que l'utilisateur ne peut pas ouvrir. Les
catégories d'un module désactivé pour le bâtiment ne sont pas interrogées.
``icontains`` échappe lui-même ``%`` et ``_`` : aucun SQL brut.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils.http import urlencode

from assets.models import Asset, Installation
from logistics.anomalie_views import anomalies_visibles
from logistics.models import CorrectiveTicket
from matrix.core.mixins import build_scope_q
from matrix.core.modules import module_actif_pour_user
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, perimetre_navire_q, scope_filters_for_user
from training.models import TrainingCourse

MIN_CARACTERES = 2
MAX_CARACTERES = 80
PAR_CATEGORIE = 5


def normaliser(brut):
    """Terme nettoyé et borné ; chaîne vide s'il est trop court pour chercher."""
    terme = (brut or "").strip()[:MAX_CARACTERES].strip()
    return terme if len(terme) >= MIN_CARACTERES else ""


def _ou(terme, *champs):
    filtre = Q()
    for champ in champs:
        filtre |= Q(**{f"{champ}__icontains": terme})
    return filtre


def installations(user, terme):
    return (
        Installation.objects.filter(**scope_filters_for_user(user))
        .filter(_ou(terme, "designation", "reference", "local"))
        .select_related("sector").order_by("designation")
    )


def materiels(user, terme):
    return (
        Asset.objects.filter(**scope_filters_for_user(user))
        .filter(_ou(terme, "designation", "internal_id", "serial_number", "nno", "reference", "local"))
        .select_related("asset_type").order_by("internal_id", "designation")
    )


def tickets(user, terme):
    # Même filtre que la fiche détail d'un ticket.
    return (
        CorrectiveTicket.objects.filter(build_scope_q(user, "asset__", "installation__"))
        .filter(description__icontains=terme)
        .select_related("asset__asset_type", "installation").order_by("-reported_at")
    )


def anomalies(user, terme):
    return anomalies_visibles(user).filter(_ou(terme, "titre", "description", "localisation")).order_by("-pk")


def formations(user, terme):
    # Catalogue commun à toute la flotte, comme la liste des formations.
    return TrainingCourse.objects.filter(statut_validation="ACTIVE").filter(
        _ou(terme, "title", "category")
    ).order_by("title")


def marins(user, terme):
    # Même règle que l'annuaire : réservé aux commandants et au-dessus, limité à leur navire.
    qs = get_user_model().objects.select_related("profile").filter(
        _ou(terme, "username", "first_name", "last_name")
    ).order_by("last_name", "username")
    if not is_master_admin(user):
        qs = qs.filter(perimetre_navire_q(user, "profile__"))
    return qs


def _sous_titre(*morceaux):
    return " · ".join(str(m) for m in morceaux if m)


def _ligne_installation(i):
    return i.designation, _sous_titre(i.sector.name, i.reference), reverse("installation-detail", args=[i.pk])


def _ligne_materiel(a):
    libelle = a.designation or a.internal_id or a.serial_number or a.asset_type.name
    return libelle, _sous_titre(a.asset_type.name, a.get_status_display(), a.local), reverse("asset-detail", args=[a.pk])


def _ligne_ticket(t):
    cible = t.asset or t.installation
    libelle = t.description if len(t.description) <= 70 else t.description[:69] + "…"
    return libelle, _sous_titre(cible, t.get_status_display()), reverse("ticket-detail", args=[t.pk])


def _ligne_anomalie(a):
    return a.titre, _sous_titre(a.localisation, a.get_statut_display()), reverse("anomalie-detail", args=[a.pk])


def _ligne_formation(f):
    return f.title, f.category, reverse("formation-list")


def _ligne_marin(u):
    profil = getattr(u, "profile", None)
    return (
        u.get_full_name() or u.username,
        _sous_titre(getattr(profil, "grade", ""), getattr(profil, "fonction_service", "")),
        reverse("user-directory") + "?" + urlencode({"q": u.username}),
    )


def _commandant_ou_plus(user):
    return user_role_level(user) >= RoleLevel.COMMANDANT


@dataclass(frozen=True)
class Categorie:
    cle: str
    libelle: str
    icone: str  # concept de matrix/core/icones.py
    requete: Callable
    ligne: Callable
    module: Optional[str] = None  # clé de REGISTRE_MODULES ; None = toujours disponible
    droit: Optional[Callable] = None
    liste: Optional[str] = None  # écran de liste acceptant ?q= (lien « Tout voir »)


CATEGORIES = [
    Categorie("installations", "Installations", "installation", installations, _ligne_installation,
              module="assets", liste="installation-list"),
    Categorie("materiels", "Matériels", "materiel", materiels, _ligne_materiel,
              module="assets", liste="asset-list"),
    Categorie("tickets", "Tickets correctifs", "ticket", tickets, _ligne_ticket, module="logistics"),
    Categorie("anomalies", "Anomalies", "anomalie", anomalies, _ligne_anomalie, module="logistics"),
    Categorie("formations", "Formations", "formation", formations, _ligne_formation, module="training"),
    Categorie("marins", "Marins", "annuaire", marins, _ligne_marin, droit=_commandant_ou_plus),
]


def rechercher(user, terme):
    """Catégories non vides sous la forme ``{"cle", "libelle", "icone", "resultats",
    "url_liste"}`` ; une requête limitée par catégorie. Terme déjà normalisé."""
    groupes = []
    for cat in CATEGORIES:
        if cat.module and not module_actif_pour_user(cat.module, user):
            continue
        if cat.droit and not cat.droit(user):
            continue
        trouves = list(cat.requete(user, terme)[:PAR_CATEGORIE + 1])
        if not trouves:
            continue
        groupes.append({
            "cle": cat.cle, "libelle": cat.libelle, "icone": cat.icone,
            "resultats": [
                {"libelle": libelle, "sous_titre": sous_titre, "url": url}
                for libelle, sous_titre, url in map(cat.ligne, trouves[:PAR_CATEGORIE])
            ],
            # « Tout voir » seulement s'il reste des résultats et que l'écran de liste filtre sur ?q=.
            "url_liste": (
                reverse(cat.liste) + "?" + urlencode({"q": terme})
                if cat.liste and len(trouves) > PAR_CATEGORIE else ""
            ),
        })
    return groupes
