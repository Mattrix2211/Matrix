"""Monde fictif commun et exécution des accès pour la preuve d'application des autorisations (lot L29).

Aucun secret : comptes et données inventés, mot de passe de test unique, aucune donnée réelle.
"""
import json
from dataclasses import dataclass, field
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import Client, TestCase
from django.utils import timezone

from absences.models import Absence
from accounts.models import ResponsableSpecialite, SpecialityChoice, TypeAbsence, UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from matrix.core.equipage import decider_releve, proposer_releve
from org.models import ParametresPassation, Sector, Section, Service, Ship, SynthesePassation
from taches.models import Tache

User = get_user_model()
MOT_DE_PASSE_TEST = "pass"
REFUS_CODES = {401, 403, 404, 405}
MARQUEUR_S2 = "TACHE-PARTAGEE-SECTION-2"


def _marin(nom, role, navire, equipage="", service=None, secteur=None, section=None, fonction_coma="", **drapeaux):
    user = User.objects.create_user(username=nom, password=MOT_DE_PASSE_TEST, **drapeaux)
    UserProfile.objects.update_or_create(user=user, defaults={
        "role": role, "ship": navire, "service": service, "sector": secteur, "section": section,
        "equipage": equipage, "fonction_coma": fonction_coma,
    })
    return User.objects.get(pk=user.pk)


class MondeFictif(TestCase):
    """Un bâtiment à double équipage (B à bord après relève, A à terre), un second bâtiment, deux services rattachés à
    deux commandants adjoints, deux sections d'un même secteur, une synthèse de passation et des données sensibles."""

    @classmethod
    def setUpTestData(cls):
        ParametresPassation.objects.create(active=True)
        n = cls.navire = Ship.objects.create(name="Bretagne", code="BRE", double_equipage=True, equipage_a_bord="A")
        cls.autre_navire = Ship.objects.create(name="Normandie", code="NOR")
        s1 = cls.service1 = Service.objects.create(ship=n, name="Propulsion", commandant_adjoint="COMANAV")
        s2 = cls.service2 = Service.objects.create(ship=n, name="Sécurité", commandant_adjoint="COMAEQ")
        sec1 = cls.secteur1 = Sector.objects.create(service=s1, name="Moteurs")
        sec2 = cls.secteur2 = Sector.objects.create(service=s2, name="Incendie")
        cls.section1 = Section.objects.create(sector=sec1, name="Section 1")
        cls.section2 = Section.objects.create(sector=sec1, name="Section 2")
        service_nor = Service.objects.create(ship=cls.autre_navire, name="Propulsion")
        u = {
            "cdt_a": _marin("cdt_a", "COMMANDANT", n, "A"),
            "cdt_b": _marin("cdt_b", "COMMANDANT", n, "B"),
            "second_b": _marin("second_b", "COMMANDANT_EN_SECOND", n, "B"),
            "admin_navire": _marin("admin_navire", "ADMIN_NAVIRE", n, "B"),
            "master_admin": _marin("master_admin", "MASTER_ADMIN", None, is_superuser=True, is_staff=True),
            "staff_sans_droit": _marin("staff_sans_droit", "EQUIPIER", n, "B", s1, sec1, cls.section1, is_staff=True),
            "comanav_b": _marin("comanav_b", "ETAT_MAJOR", n, "B", fonction_coma="COMANAV"),
            "comaeq_b": _marin("comaeq_b", "ETAT_MAJOR", n, "B", fonction_coma="COMAEQ"),
            "chef_service_b": _marin("chef_service_b", "CHEF_SERVICE", n, "B", s1),
            "chef_service_sec": _marin("chef_service_sec", "CHEF_SERVICE", n, "B", s2),
            "chef_secteur_b": _marin("chef_secteur_b", "CHEF_SECTEUR", n, "B", s1, sec1),
            "chef_section_b1": _marin("chef_section_b1", "CHEF_SECTION", n, "B", s1, sec1, cls.section1),
            "chef_section_b2": _marin("chef_section_b2", "CHEF_SECTION", n, "B", s1, sec1, cls.section2),
            "equipier_b1": _marin("equipier_b1", "EQUIPIER", n, "B", s1, sec1, cls.section1),
            "equipier_b2": _marin("equipier_b2", "EQUIPIER", n, "B", s1, sec1, cls.section2),
            "equipier_sec": _marin("equipier_sec", "EQUIPIER", n, "B", s2, sec2),
            "equipier_sec2": _marin("equipier_sec2", "EQUIPIER", n, "B", s2, sec2),
            "chef_secteur_a": _marin("chef_secteur_a", "CHEF_SECTEUR", n, "A", s1, sec1),
            "equipier_a": _marin("equipier_a", "EQUIPIER", n, "A", s1, sec1, cls.section1),
            "equipier_abe": _marin("equipier_abe", "EQUIPIER", cls.autre_navire, "", service_nor),
            "cdt_abe": _marin("cdt_abe", "COMMANDANT", cls.autre_navire, ""),
            "admin_abe": _marin("admin_abe", "ADMIN_NAVIRE", cls.autre_navire, ""),
            "soutien_terre": _marin("soutien_terre", "CHEF_SERVICE", None),
        }
        ResponsableSpecialite.objects.create(user=u["soutien_terre"], specialite=SpecialityChoice.objects.create(name="Mécanique"))
        for nom, user in u.items():
            setattr(cls, nom, user)
        type_actif = AssetType.objects.create(name="Pompe", category="Incendie", sector=sec2)
        cls.materiel_sec = Asset.objects.create(asset_type=type_actif, ship=n, service=s2, sector=sec2)
        cls.ticket_sec = CorrectiveTicket.objects.create(asset=cls.materiel_sec, description="Fuite secteur Incendie", severity=3)
        cls.tache_privee = Tache.objects.create(titre="TACHE-PRIVEE-SECTION-2", assigne=u["equipier_b2"], created_by=u["chef_section_b2"],
                                                statut="A_FAIRE", partagee=False)
        cls.tache_partagee_s2 = Tache.objects.create(titre=MARQUEUR_S2, assigne=u["equipier_b2"], created_by=u["chef_section_b2"],
                                                     statut="BLOQUEE", motif_blocage="Pièce", partagee=True)
        cls.tache_service2 = Tache.objects.create(titre="TACHE-SERVICE-SECURITE", assigne=u["equipier_sec"], created_by=u["chef_service_sec"],
                                                  statut="A_FAIRE", partagee=True)
        cls.tache_a = Tache.objects.create(titre="TACHE-EQUIPAGE-A", assigne=u["equipier_a"], created_by=u["equipier_a"], statut="A_FAIRE")
        cls.tache_b1 = Tache.objects.create(titre="TACHE-EQUIPIER-B1", assigne=u["equipier_b1"], created_by=u["equipier_b1"], statut="A_FAIRE")
        type_absence = TypeAbsence.objects.order_by("pk").first() or TypeAbsence.objects.create(name="Permission")
        aujourdhui = timezone.localdate()
        Absence.objects.create(marin=u["equipier_b2"], type_absence=type_absence, date_debut=aujourdhui,
                               date_fin=aujourdhui + timedelta(days=3), motif="MOTIF-FICTIF")
        proposition, erreur = proposer_releve(u["cdt_a"], n, "B", timezone.now())
        assert erreur == "", erreur
        assert decider_releve(u["cdt_b"], proposition, True) == ""
        n.refresh_from_db()
        cls.synthese = SynthesePassation.objects.get()

    def client_de(self, nom):
        client = Client()
        if nom is not None:
            client.force_login(User.objects.get(username=nom))
        return client


@dataclass(frozen=True)
class Verification:
    """Une requête réelle et le résultat attendu pour chaque profil.

    Résultats : « refus » ; « acces » ; « acces+ » (accès, `contenu` présent) ; « acces- » (accès, `contenu` absent).
    `attendu` est la cible ; `ecarts_connus` donne, pour les profils concernés, le résultat réellement observé
    aujourd'hui, que le test enregistre tel quel et qui échoue le jour où l'écart est corrigé."""
    identifiant: str
    regle: str
    methode: str
    url: object  # chaîne ou fonction (monde) -> chaîne
    attendu: dict
    donnees: object = None  # dict ou fonction (monde) -> dict
    contenu: str = ""
    effet: object = None  # fonction (monde) -> bool : l'écriture a-t-elle eu lieu ?
    ecarts_connus: dict = field(default_factory=dict)
    lot_correctif: str = ""
    codes: dict = field(default_factory=dict)  # profil -> code HTTP exact exigé (distingue un refus explicite d'un 404 d'adresse)


def _valeur(v, monde):
    return v(monde) if callable(v) else v


def observer(verification, monde, profil):
    """(résultat, code HTTP) réels d'une requête, sans effet durable : l'écriture est annulée à la fin."""
    client = monde.client_de(profil)
    url = _valeur(verification.url, monde)
    donnees = _valeur(verification.donnees, monde) or {}
    with transaction.atomic():
        if verification.methode in ("get", "post"):
            reponse = getattr(client, verification.methode)(url, donnees)
        else:
            reponse = getattr(client, verification.methode)(url, data=json.dumps(donnees), content_type="application/json")
        effet = verification.effet(monde) if verification.effet else None
        transaction.set_rollback(True)
    code = reponse.status_code
    if code in REFUS_CODES or (code in (301, 302) and "login" in reponse.get("Location", "")):
        return "refus", code
    if code >= 400:
        return f"erreur {code}", code
    if effet is False:
        return "refus", code
    if verification.contenu:
        corps = reponse.content.decode("utf-8", "replace")
        return ("acces+" if verification.contenu in corps else "acces-"), code
    return "acces", code


def comparer(verification, monde):
    """(profil, enregistré, observé) pour chaque profil dont l'observation diffère de ce qui est enregistré."""
    divergences = []
    for profil, cible in verification.attendu.items():
        obtenu, code = observer(verification, monde, profil)
        enregistre = verification.ecarts_connus.get(profil, cible)
        if obtenu != enregistre:
            divergences.append((profil, enregistre, obtenu))
        elif profil in verification.codes and code != verification.codes[profil]:
            divergences.append((profil, f"code {verification.codes[profil]}", f"code {code}"))
    return divergences


# --- Contrôles de couverture, réutilisés par le test qui prouve que le dispositif détecte un accès mal protégé ---

def points_non_couverts(points):
    """Points d'entrée qu'aucune règle du registre ne couvre."""
    from matrix.core.registre_acces import regle_de

    return [p.cle for p in points if regle_de(p) is None]


def acces_anonymes_non_refuses(points, methodes=("get", "post", "put", "patch", "delete")):
    """(méthode, adresse, code) des routes non publiques qu'un visiteur non connecté atteint réellement.

    Un refus est un 401, un 403, un 405 ou une redirection vers la connexion ; tout le reste (200, 404, erreur serveur)
    est signalé : un 404 anonyme peut cacher une recherche d'objet faite avant tout contrôle d'accès."""
    from matrix.core.registre_acces import PUBLIC, regle_de

    client = Client()
    anomalies = []
    for point in points:
        regle = regle_de(point)
        if point.url_exemple is None or (regle and regle.classe == PUBLIC):
            continue
        for methode in methodes:
            reponse = getattr(client, methode)(point.url_exemple)
            refuse = reponse.status_code in REFUS_CODES - {404} or (
                reponse.status_code in (301, 302) and "login" in reponse.get("Location", ""))
            if not refuse:
                anomalies.append((methode, point.url_exemple, reponse.status_code))
    return anomalies


def lignes_routes_ecriture(points):
    """Instantané des routes web et API capables d'écrire : nature, clé, méthodes, règle du registre."""
    from matrix.core.registre_acces import regle_de

    return sorted(
        f"{p.nature}|{p.cle}|{','.join(p.methodes) if p.methodes else '?'}|{(regle_de(p) or Regle0).identifiant}"
        for p in points if p.nature in ("web", "api") and p.ecriture_possible and not p.variante_format
    )


class Regle0:
    identifiant = "SANS-REGLE"
