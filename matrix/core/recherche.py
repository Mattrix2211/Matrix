"""Recherche globale par catégorie (docs/UX.md §21).

Chaque catégorie réutilise le périmètre de ses vues de liste et de détail
(``scope_filters_for_user``, ``build_scope_q``, ``anomalies_visibles``) : aucun
résultat ne mène à un objet que l'utilisateur ne peut pas ouvrir. Les
catégories d'un module désactivé pour le bâtiment ne sont pas interrogées.
``icontains`` échappe lui-même ``%`` et ``_`` : aucun SQL brut.
"""
import re
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
from matrix.core.roles import NIVEAU_VISION_COMMANDEMENT, user_role_level
from matrix.core.scopes import is_master_admin, perimetre_navire_q
from training.models import TrainingCourse

MIN_CARACTERES = 2
MAX_CARACTERES = 80
PAR_CATEGORIE = 5
_NUL_ET_LARGEUR_NULLE = re.compile(r"[\x00\u200b-\u200f\u2060\ufeff]")
_CONTROLES = re.compile(r"[\x01-\x1f\x7f-\x9f]")


def normaliser(brut):
    """Terme nettoyé et borné ; chaîne vide s'il est trop court pour chercher."""
    # NUL ferait échouer PostgreSQL et la largeur nulle fausserait la longueur : on les retire ;
    # les autres contrôles (tabulation, saut de ligne) séparent des mots.
    terme = " ".join(_CONTROLES.sub(" ", _NUL_ET_LARGEUR_NULLE.sub("", brut or "")).split())[:MAX_CARACTERES].strip()
    return terme if len(terme) >= MIN_CARACTERES else ""


def _ou(terme, *champs):
    filtre = Q()
    for champ in champs:
        filtre |= Q(**{f"{champ}__icontains": terme})
    return filtre


def installations(user, terme):
    return (
        Installation.objects.filter(build_scope_q(user, ""))
        .filter(_ou(terme, "designation", "reference", "local"))
        .select_related("sector").order_by("designation")
    )


def materiels(user, terme):
    return (
        Asset.objects.filter(build_scope_q(user, ""))
        .filter(_ou(terme, "designation", "internal_id", "serial_number", "nno", "reference", "local"))
        .select_related("asset_type").order_by("internal_id", "designation")
    )


def tickets(user, terme):
    # Même filtre que la fiche détail d'un ticket.
    # L'identifiant (UUID) n'est jamais affiché : on ne cherche que la description.
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


def marins(user, terme, avec_identifiants=False):
    # Tout marin cherche dans son navire ; sans navire rattaché, aucun résultat
    # (jamais toute la flotte), sauf maître ou superutilisateur. La recherche rapide
    # ne cherche jamais l'identifiant de connexion (il ne s'affiche pas et servirait
    # d'oracle) ; la page complète, qui affiche identifiant et e-mail, les cherche.
    champs = ("first_name", "last_name", "username", "email") if avec_identifiants else ("first_name", "last_name")
    qs = get_user_model().objects.select_related("profile").filter(
        _ou(terme, *champs), is_active=True,
    ).order_by("last_name", "username")
    if not is_master_admin(user):
        qs = qs.filter(perimetre_navire_q(user, "profile__"))
    return qs


def _sous_titre(*morceaux):
    return " · ".join(str(m) for m in morceaux if m)


def _ligne_installation(i, user):
    return i.designation, _sous_titre(i.sector.name, i.reference), reverse("installation-detail", args=[i.pk])


def _ligne_materiel(a, user):
    libelle = a.designation or a.internal_id or a.serial_number or a.asset_type.name
    return libelle, _sous_titre(a.asset_type.name, a.get_status_display(), a.local), reverse("asset-detail", args=[a.pk])


def _ligne_ticket(t, user):
    cible = t.asset or t.installation
    libelle = t.description if len(t.description) <= 70 else t.description[:69] + "…"
    return libelle, _sous_titre(cible, t.get_status_display()), reverse("ticket-detail", args=[t.pk])


def _ligne_anomalie(a, user):
    return a.titre, _sous_titre(a.localisation, a.get_statut_display()), reverse("anomalie-detail", args=[a.pk])


def _ligne_formation(f, user):
    return f.title, f.category, reverse("formation-list")


def _ligne_marin(u, user):
    profil = getattr(u, "profile", None)
    # Pas de fiche marin : le résultat n'est un lien que pour qui peut ouvrir l'annuaire.
    url = reverse("user-directory") + "?" + urlencode({"q": u.username}) if _commandant_ou_plus(user) else ""
    return (
        u.get_full_name() or (u.username if _commandant_ou_plus(user) else "Marin sans nom"),
        _sous_titre(
            getattr(profil, "grade", ""),
            profil.get_role_display() if profil and profil.role else "",
            getattr(profil, "fonction_service", ""),
        ),
        url,
    )


def _commandant_ou_plus(user):
    return user_role_level(user) >= NIVEAU_VISION_COMMANDEMENT


@dataclass(frozen=True)
class Categorie:
    cle: str
    libelle: str
    icone: str  # concept de matrix/core/icones.py
    requete: Callable
    ligne: Callable
    module: Optional[str] = None  # clé de REGISTRE_MODULES ; None = toujours disponible
    liste: Optional[str] = None  # écran de liste acceptant ?q= (lien « Tout voir »)


CATEGORIES = [
    Categorie("installations", "Installations", "installation", installations, _ligne_installation,
              module="assets", liste="installation-list"),
    Categorie("materiels", "Matériels", "materiel", materiels, _ligne_materiel,
              module="assets", liste="asset-list"),
    Categorie("tickets", "Tickets correctifs", "ticket", tickets, _ligne_ticket, module="logistics"),
    Categorie("anomalies", "Anomalies", "anomalie", anomalies, _ligne_anomalie, module="logistics"),
    Categorie("formations", "Formations", "formation", formations, _ligne_formation, module="training"),
    Categorie("marins", "Marins", "annuaire", marins, _ligne_marin),
]


def rechercher(user, terme):
    """Catégories non vides sous la forme ``{"cle", "libelle", "icone", "resultats",
    "url_liste"}`` ; une requête limitée par catégorie. Terme déjà normalisé."""
    groupes = []
    for cat in CATEGORIES:
        if cat.module and not module_actif_pour_user(cat.module, user):
            continue
        trouves = list(cat.requete(user, terme)[:PAR_CATEGORIE + 1])
        if not trouves:
            continue
        groupes.append({
            "cle": cat.cle, "libelle": cat.libelle, "icone": cat.icone,
            "resultats": [
                {"libelle": libelle, "sous_titre": sous_titre, "url": url}
                for libelle, sous_titre, url in (cat.ligne(obj, user) for obj in trouves[:PAR_CATEGORIE])
            ],
            # « Tout voir » seulement s'il reste des résultats et que l'écran de liste filtre sur ?q=.
            "url_liste": (
                reverse(cat.liste) + "?" + urlencode({"q": terme})
                if cat.liste and len(trouves) > PAR_CATEGORIE else ""
            ),
        })
    return groupes
