"""Périmètre de consultation des synthèses de passation (ARB-02, AC-03).

La synthèse est un instantané du bâtiment : chaque ligne y porte sa « portée » (unité d'organisation et marins concernés) et une
clé stable. À la lecture, le serveur ne rend que les lignes que l'utilisateur est autorisé à voir : celles de son périmètre de
responsabilité, celles qui le concernent, et celles qui lui ont été explicitement partagées (lecture seule). Totaux, groupes,
compteurs et pages imprimables sont recalculés à partir des seules lignes visibles : rien n'est masqué par l'interface.

Périmètres (ARB-02) : marin = ce qui le concerne ; chef de section = sa section ; chef de secteur = son secteur ; chef de service =
son service ; commandant adjoint = ses services de rattachement ; commandant en second et commandant = tout le bâtiment.
Administrateur technique et administrateur général : aucun droit supplémentaire du seul fait de leur statut. L'équipage n'est pas un
critère : l'équipage à terre garde la consultation de son périmètre, sans limite de durée.
"""
from dataclasses import dataclass

from accounts.models import Roles
from annonces.services import chaine
from matrix.core.roles import NIVEAU_VISION_COMMANDEMENT, user_role_level
from org.models import PartagePassation, Service

VERSION_CONTENU = 2


@dataclass(frozen=True)
class Couverture:
    """Ce qu'un utilisateur lit dans la synthèse d'un bâtiment, hors partages."""
    navire_id: int
    utilisateur_id: int
    batiment: bool = False
    services: frozenset = frozenset()
    secteurs: frozenset = frozenset()
    sections: frozenset = frozenset()


def couverture(user):
    """Périmètre de consultation de `user`, ou None sans bâtiment (administrateur général seul, personnel à terre)."""
    profil = getattr(user, "profile", None)
    navire_id = profil.navire_id_effectif if profil else None
    if not navire_id or not user.is_authenticated:
        return None
    if user_role_level(user) >= NIVEAU_VISION_COMMANDEMENT:
        return Couverture(navire_id, user.pk, batiment=True)
    _, service, secteur, section = chaine(user)
    services, secteurs, sections = set(), set(), set()
    if profil.role == Roles.CHEF_SECTION and section:
        sections.add(section)
    elif profil.role == Roles.CHEF_SECTEUR and secteur:
        secteurs.add(secteur)
    elif profil.role == Roles.CHEF_SERVICE and service:
        services.add(service)
    elif profil.role == Roles.ETAT_MAJOR and profil.fonction_coma:
        services.update(Service.objects.filter(ship_id=navire_id, commandant_adjoint=profil.fonction_coma).values_list("pk", flat=True))
    return Couverture(navire_id, user.pk, False, frozenset(services), frozenset(secteurs), frozenset(sections))


def portee(*, ship=None, service=None, sector=None, section=None, marins=()):
    """Portée d'une ligne : unité d'organisation résolue en remontant la hiérarchie, et marins concernés."""
    if section is not None:
        sector = sector or section.sector
    if sector is not None:
        service = service or sector.service
    return {
        "service": service.pk if service else None,
        "secteur": sector.pk if sector else None,
        "section": section.pk if section else None,
        "marins": sorted({m for m in marins if m}),
    }


def portee_du_marin(marin):
    """Portée d'une ligne qui concerne un marin : son unité (résolue jusqu'au bâtiment) et lui-même."""
    _, service, secteur, section = chaine(marin)
    return {"service": service, "secteur": secteur, "section": section, "marins": [marin.pk]}


def dans_la_couverture(couv, ligne_portee):
    if couv.batiment:
        return True
    if couv.utilisateur_id in ligne_portee.get("marins", ()):
        return True
    return bool(
        (ligne_portee.get("section") in couv.sections)
        or (ligne_portee.get("secteur") in couv.secteurs)
        or (ligne_portee.get("service") in couv.services)
    )


def _destinataire_q(user):
    """Cibles de partage qui désignent `user` à l'instant de la lecture (affectation, fonction et équipage actuels)."""
    from django.db.models import Q

    profil = user.profile
    _, service, secteur, section = chaine(user)
    q = Q(type_destinataire="MARIN", marin=user)
    if section:
        q |= Q(type_destinataire="SECTION", section_id=section)
    if secteur:
        q |= Q(type_destinataire="SECTEUR", sector_id=secteur)
    if service:
        q |= Q(type_destinataire="SERVICE", service_id=service)
    fonctions = []
    if profil.role == Roles.ETAT_MAJOR and profil.fonction_coma:
        fonctions.append(f"coma:{profil.fonction_coma}")
    if profil.fonction_service:
        fonctions.append(f"service:{profil.fonction_service}")
    if fonctions:
        q |= Q(type_destinataire="FONCTION", fonction__in=fonctions)
    return q


def cles_partagees_a(user, synthese):
    """Clés des lignes de `synthese` partagées avec `user` (partages actifs seulement ; jamais hors du bâtiment)."""
    profil = getattr(user, "profile", None)
    if profil is None or profil.navire_id_effectif != synthese.ship_id:
        return frozenset()
    return frozenset(
        synthese.partages.filter(revoque_le__isnull=True).filter(_destinataire_q(user)).values_list("cle_ligne", flat=True)
    )


def _recalculer(blocs, plafond):
    """Totaux, plafond d'affichage et compteurs refaits sur les lignes restantes."""
    resultat = []
    for bloc in blocs:
        groupes = []
        for groupe in bloc["groupes"]:
            lignes = groupe["lignes"]
            groupes.append({"titre": groupe["titre"], "total": len(lignes), "lignes": lignes[:plafond],
                            "plus": max(0, len(lignes) - plafond)})
        resultat.append({"cle": bloc["cle"], "titre": bloc["titre"], "total": sum(g["total"] for g in groupes),
                         "groupes": groupes, "vide": bloc["vide"]})
    return resultat


def contenu_visible(user, synthese, plafond=30):
    """Contenu de `synthese` filtré pour `user` : {"blocs", "restreint", "ancien"}.

    `restreint` : une partie du contenu n'est pas rendue (jamais de chiffre). `ancien` : synthèse figée avant le cloisonnement
    par périmètre, dont les lignes n'ont pas de portée : seul le commandement du bâtiment la lit en entier."""
    couv = couverture(user)
    contenu = synthese.contenu or {}
    if couv is None or couv.navire_id != synthese.ship_id:
        return {"blocs": [], "restreint": True, "ancien": False}
    if couv.batiment:
        blocs = contenu.get("blocs", [])
        resultat = {"blocs": _recalculer(blocs, plafond) if contenu.get("version") == VERSION_CONTENU else blocs,
                    "restreint": False, "ancien": False}
        return _annoter(resultat, synthese, couv)
    if contenu.get("version") != VERSION_CONTENU:
        return {"blocs": [], "restreint": True, "ancien": bool(contenu.get("blocs"))}
    partagees = cles_partagees_a(user, synthese)
    blocs = []
    for bloc in contenu.get("blocs", []):
        groupes = []
        for groupe in bloc["groupes"]:
            lignes = []
            for ligne in groupe["lignes"]:
                cle = ligne.get("cle", "")
                propre = dans_la_couverture(couv, ligne.get("portee", {}))
                if propre or cle in partagees:
                    lignes.append({**ligne, "partage_recu": (not propre) and cle in partagees})
            groupes.append({**groupe, "lignes": lignes})
        blocs.append({**bloc, "groupes": groupes, "vide": "Aucune information de ce type dans votre périmètre ni partagée avec vous."})
    return _annoter({"blocs": _recalculer(blocs, plafond), "restreint": True, "ancien": False}, synthese, couv)


def _annoter(resultat, synthese, couv):
    """Pour chaque ligne rendue : peut-on la partager, et avec qui est-elle partagée (visible des seules autorités de la ligne)."""
    if synthese.contenu.get("version") != VERSION_CONTENU:
        return resultat
    par_ligne = {}
    for partage in synthese.partages.filter(revoque_le__isnull=True).select_related("marin", "service", "sector", "section"):
        par_ligne.setdefault(partage.cle_ligne, []).append(partage.libelle_destinataire())
    for bloc in resultat["blocs"]:
        for groupe in bloc["groupes"]:
            for ligne in groupe["lignes"]:
                autorite = (not ligne.get("partage_recu")) and dans_la_couverture(couv, ligne.get("portee", {}))
                ligne["peut_partager"] = bool(autorite and ligne.get("partageable", True))
                ligne["partage_avec"] = par_ligne.get(ligne.get("cle", ""), []) if autorite else []
    return resultat


def ligne_de(synthese, cle):
    """Ligne de la synthèse par sa clé (ou None) ; ne préjuge pas des droits."""
    for bloc in (synthese.contenu or {}).get("blocs", []):
        for groupe in bloc["groupes"]:
            for ligne in groupe["lignes"]:
                if ligne.get("cle") == cle:
                    return ligne
    return None


def peut_partager(user, synthese, ligne):
    """Qui peut partager : celui dont le PÉRIMÈTRE couvre la ligne (marin : ce qui le concerne ; chef : son périmètre ;
    commandement : le bâtiment), jamais du seul fait d'un partage reçu (pas de partage transitif), ni d'un statut d'administration.
    Une ligne marquée non partageable (dossier individuel soumis à ses propres habilitations) ne se partage pas."""
    couv = couverture(user)
    if couv is None or couv.navire_id != synthese.ship_id or ligne is None or not ligne.get("partageable", True):
        return False
    return synthese.contenu.get("version") == VERSION_CONTENU and dans_la_couverture(couv, ligne.get("portee", {}))


def peut_revoquer(user, partage):
    """Révocation : l'auteur du partage, ou une autorité habilitée sur la ligne (périmètre qui la couvre)."""
    if partage.revoque_le is not None:
        return False
    if partage.partage_par_id == user.pk:
        return True
    ligne = ligne_de(partage.synthese, partage.cle_ligne)
    return peut_partager(user, partage.synthese, ligne)


def partages_de_ligne(synthese, cle):
    return PartagePassation.objects.filter(synthese=synthese, cle_ligne=cle).select_related(
        "partage_par", "revoque_par", "marin", "service", "sector", "section")
