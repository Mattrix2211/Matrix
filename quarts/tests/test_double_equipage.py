"""Double équipage, tranche 4 : les quarts, listes de service, échanges
restent propres à chaque équipage ; un navire à
équipage unique se comporte exactement comme avant."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import ServiceFunctionChoice, UserProfile
from org.models import Sector, Service, Ship
from quarts.echanges import analyser_echange
from quarts.web_views import _peut_lire_liste  # noqa: F401  (ordre d'import circulaire)
from quarts.listes_views import _listes_visibles
from quarts.models import (
    ChefDeListe,
    CreneauServiceGarde,
    EchangeService,
    ServiceGarde,
    marins_du_perimetre,
    peut_gerer_liste,
    peut_publier_liste,
    utilisateur_autorise_pour_perimetre,
)
from quarts.services import compteurs_equite_perimetre

User = get_user_model()


def marin(nom, role, ship, equipage="", sector=None):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(
        user=user, defaults={"role": role, "ship": ship, "sector": sector, "equipage": equipage}
    )
    return User.objects.get(pk=user.pk)


class DoubleEquipageBase(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="FREMM Test", code="FT", classe_navire="FREMM", double_equipage=True)
        self.bleu, self.rouge = "A", "B"
        self.ship.equipage_a_bord = self.bleu
        self.ship.save()
        # Organisation commune aux deux équipages : seuls les marins portent l'équipage.
        self.service_bleu = self.service_rouge = Service.objects.create(ship=self.ship, name="Pont")
        self.secteur_bleu = self.secteur_rouge = Sector.objects.create(service=self.service_bleu, name="Manœuvre")
        self.a_bleu = marin("a_bleu", "EQUIPIER", self.ship, self.bleu, self.secteur_bleu)
        self.b_bleu = marin("b_bleu", "EQUIPIER", self.ship, self.bleu, self.secteur_bleu)
        self.a_rouge = marin("a_rouge", "EQUIPIER", self.ship, self.rouge, self.secteur_rouge)
        self.cdt_bleu = marin("cdt_bleu", "COMMANDANT", self.ship, self.bleu)
        self.cdt_rouge = marin("cdt_rouge", "COMMANDANT", self.ship, self.rouge)
        self.fonction = ServiceFunctionChoice.objects.create(name="Permanence")
        self.aujourdhui = timezone.localdate()

    def garde(self, createur, **perimetre):
        return ServiceGarde.objects.create(
            fonction=self.fonction, date_debut=self.aujourdhui, date_fin=self.aujourdhui + timedelta(days=30),
            statut=ServiceGarde.STATUT_PUBLIEE, created_by=createur, **perimetre,
        )

    def creneau(self, garde, marin_affecte, jours=5):
        debut = timezone.now() + timedelta(days=jours)
        return CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Officier de quart", debut=debut, fin=debut + timedelta(hours=24),
            marin=marin_affecte,
        )


class ListesParEquipageTests(DoubleEquipageBase):
    def test_liste_de_l_unite_ne_couvre_que_l_equipage_de_son_createur(self):
        liste = self.garde(self.cdt_bleu, ship=self.ship)
        marins = set(User.objects.filter(marins_du_perimetre(liste)))
        self.assertEqual(marins, {self.a_bleu, self.b_bleu, self.cdt_bleu})

    def test_liste_de_service_ne_couvre_jamais_l_autre_equipage(self):
        # Donnée incohérente volontaire : un marin du Rouge rattaché au secteur du Bleu.
        intrus = marin("intrus", "EQUIPIER", self.ship, self.rouge, self.secteur_bleu)
        liste = self.garde(self.cdt_bleu, sector=self.secteur_bleu)
        marins = set(User.objects.filter(marins_du_perimetre(liste)))
        self.assertEqual(marins, {self.a_bleu, self.b_bleu})
        self.assertNotIn(intrus, marins)

    def test_equite_sans_melange(self):
        liste = self.garde(self.cdt_bleu, ship=self.ship)
        marins = {ligne["marin"] for ligne in compteurs_equite_perimetre(liste)}
        self.assertNotIn(self.a_rouge, marins)
        self.assertIn(self.a_bleu, marins)

    def test_chef_de_l_autre_equipage_ne_gere_ni_ne_publie(self):
        liste = self.garde(self.cdt_bleu, sector=self.secteur_bleu)
        self.assertTrue(peut_gerer_liste(self.cdt_bleu, liste))
        self.assertTrue(peut_publier_liste(self.cdt_bleu, liste))
        self.assertFalse(peut_gerer_liste(self.cdt_rouge, liste))
        self.assertFalse(peut_publier_liste(self.cdt_rouge, liste))

    def test_liste_de_l_unite_reservee_a_l_equipage_du_createur(self):
        liste = self.garde(self.cdt_bleu, ship=self.ship)
        self.assertFalse(peut_gerer_liste(self.cdt_rouge, liste))

    def test_listes_visibles_bornees_a_l_equipage(self):
        unite_bleu = self.garde(self.cdt_bleu, ship=self.ship)
        unite_rouge = self.garde(self.cdt_rouge, ship=self.ship)
        self.assertEqual(set(_listes_visibles(ServiceGarde, self.cdt_bleu)), {unite_bleu})
        self.assertEqual(set(_listes_visibles(ServiceGarde, self.cdt_rouge)), {unite_rouge})
        # Un chef de liste désigné ne voit que la liste de son périmètre (et de son équipage).
        chef = marin("chef_bleu", "CHEF_SECTEUR", self.ship, self.bleu, self.secteur_bleu)
        ChefDeListe.objects.create(user=chef, sector=self.secteur_bleu)
        liste_service = self.garde(self.cdt_bleu, sector=self.secteur_bleu)
        self.assertEqual(set(_listes_visibles(ServiceGarde, chef)), {liste_service})

    def test_designation_de_chef_de_liste_limitee_a_l_equipage(self):
        self.client.force_login(self.cdt_bleu)
        reponse = self.client.post("/quarts/reglages/", {
            "action": "designer", "perimetre": f"sector:{self.secteur_bleu.pk}", "user_id": self.a_rouge.pk,
        })
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(ChefDeListe.objects.filter(user=self.a_rouge).exists())
        self.client.post("/quarts/reglages/", {
            "action": "designer", "perimetre": f"sector:{self.secteur_bleu.pk}", "user_id": self.a_bleu.pk,
        })
        self.assertTrue(ChefDeListe.objects.filter(user=self.a_bleu).exists())


class EchangesParEquipageTests(DoubleEquipageBase):
    def test_echange_entre_equipages_impossible(self):
        liste = self.garde(self.cdt_bleu, ship=self.ship)
        c1, c2 = self.creneau(liste, self.a_bleu), self.creneau(liste, self.a_rouge, jours=6)
        echange = EchangeService(
            creneau_demandeur=c1, creneau_cible=c2, demandeur=self.a_bleu, cible=self.a_rouge,
        )
        problemes = analyser_echange(echange)
        self.assertTrue(any("même équipage" in p for p in problemes))

    def test_echange_dans_un_meme_equipage_possible(self):
        liste = self.garde(self.cdt_bleu, ship=self.ship)
        c1, c2 = self.creneau(liste, self.a_bleu), self.creneau(liste, self.b_bleu, jours=6)
        echange = EchangeService(
            creneau_demandeur=c1, creneau_cible=c2, demandeur=self.a_bleu, cible=self.b_bleu,
        )
        self.assertEqual(analyser_echange(echange), [])


class EquipageUniqueInchangeTests(TestCase):
    def test_navire_a_equipage_unique_sans_restriction(self):
        ship = Ship.objects.create(name="Frégate", code="FR")
        service = Service.objects.create(ship=ship, name="Pont")
        secteur = Sector.objects.create(service=service, name="Manœuvre")
        chef = marin("chef", "COMMANDANT", ship)
        m1 = marin("m1", "EQUIPIER", ship, sector=secteur)
        liste = ServiceGarde.objects.create(
            fonction=ServiceFunctionChoice.objects.create(name="Permanence"), ship=ship, created_by=chef,
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=3),
        )
        self.assertIn(m1, User.objects.filter(marins_du_perimetre(liste)))
        self.assertTrue(peut_gerer_liste(chef, liste))
        self.assertIn(liste, _listes_visibles(ServiceGarde, chef))


class EquipageATerreLectureSeuleTests(DoubleEquipageBase):
    """L'équipage à terre (ici Rouge, Bleu étant à bord) ne modifie rien."""

    def test_equipage_a_terre_ne_peut_pas_designer_de_chef_de_liste(self):
        self.client.force_login(self.cdt_rouge)
        reponse = self.client.post(
            "/quarts/reglages/", {"action": "ajouter", "user_id": self.a_rouge.pk}, follow=False
        )
        self.assertIn(reponse.status_code, (302, 403))
        self.assertFalse(ChefDeListe.objects.filter(user=self.a_rouge).exists())

    def test_equipage_a_bord_reste_operationnel(self):
        self.client.force_login(self.cdt_bleu)
        reponse = self.client.get("/quarts/reglages/")
        self.assertEqual(reponse.status_code, 200)
