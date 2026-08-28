"""[FEAT] Rendu du plan interactif : navigation entre ponts, code couleur par
état, clic vers le matériel.

Sous-tâche 3/3 (dernière) du plan visuel du navire : la sous-tâche 1 a livré
le modèle de données (Deck/Zone), la sous-tâche 2 l'éditeur réservé aux chefs.
Cette sous-tâche livre la page de consultation, ouverte à tous les rôles.
"""
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Deck, Location, Zone
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


def _image_1x1_png():
    # PNG 1x1 minimal valide, même fixture que test_plan_navire_web.py.
    contenu = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de0000000c4944415478da6360606060000000050001a5f645400000000049454e44ae426082"
    )
    return SimpleUploadedFile("plan.png", contenu, content_type="image/png")


class ZoneEtatMaterielTests(TestCase):
    """Calcul de l'état agrégé d'une zone (Zone.etat_materiel) : le pire état
    présent parmi le matériel de son emplacement l'emporte toujours."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)
        self.emplacement = Location.objects.create(ship=self.ship, name="Local machine")
        self.pont = Deck.objects.create(ship=self.ship, name="Pont A", order=1)
        self.zone = Zone.objects.create(
            deck=self.pont, name="Local machine avant", location=self.emplacement,
            points=[{"x": 10, "y": 10}, {"x": 40, "y": 10}, {"x": 40, "y": 30}, {"x": 10, "y": 30}],
        )

    def _creer_asset(self, status="OK"):
        return Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            location=self.emplacement, status=status,
        )

    def test_zone_sans_emplacement_est_neutre(self):
        zone_brouillon = Zone.objects.create(deck=self.pont, name="Brouillon", points=self.zone.points)
        self.assertEqual(zone_brouillon.etat_materiel, Zone.ETAT_NEUTRE)

    def test_zone_avec_emplacement_sans_materiel_est_neutre(self):
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_NEUTRE)

    def test_zone_avec_materiel_ok_est_verte(self):
        self._creer_asset(status="OK")
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_OK)

    def test_zone_avec_un_seul_element_hors_service_est_rouge(self):
        # Le pire état l'emporte : un matériel OK et un matériel hors service
        # dans la même zone doivent quand même colorer toute la zone en rouge.
        self._creer_asset(status="OK")
        self._creer_asset(status="OUT_OF_SERVICE")
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_DANGER)

    def test_zone_avec_materiel_defectueux_est_rouge(self):
        self._creer_asset(status="FAULTY")
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_DANGER)

    def test_zone_avec_controle_en_retard_est_orange(self):
        asset = self._creer_asset(status="OK")
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle annuel", every_n_days=365)
        MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.now().date(), status="OVERDUE",
        )
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_ATTENTION)

    def test_zone_avec_ticket_correctif_ouvert_est_orange(self):
        # Asset.status n'est jamais remis à jour automatiquement à l'ouverture
        # d'un ticket correctif : un matériel resté "OK" avec un ticket en
        # cours doit quand même déclencher l'alerte (sinon faux sentiment de
        # sécurité sur le plan).
        asset = self._creer_asset(status="OK")
        CorrectiveTicket.objects.create(asset=asset, description="Fuite constatée", status="REPORTED")
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_ATTENTION)

    def test_zone_avec_ticket_correctif_en_reparation_est_orange(self):
        asset = self._creer_asset(status="OK")
        CorrectiveTicket.objects.create(asset=asset, description="Réparation en cours", status="IN_REPAIR")
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_ATTENTION)

    def test_zone_avec_ticket_correctif_ferme_ou_annule_reste_ok(self):
        asset = self._creer_asset(status="OK")
        CorrectiveTicket.objects.create(asset=asset, description="Panne résolue", status="CLOSED")
        CorrectiveTicket.objects.create(asset=asset, description="Signalement annulé", status="CANCELLED")
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_OK)

    def test_danger_l_emporte_sur_le_controle_en_retard(self):
        # Un matériel en retard de contrôle ET un autre hors service dans la
        # même zone : le pire état (DANGER) doit l'emporter sur ATTENTION.
        asset_en_retard = self._creer_asset(status="OK")
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset_en_retard, name="Contrôle", every_n_days=365)
        MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset_en_retard, scheduled_for=timezone.now().date(), status="OVERDUE",
        )
        self._creer_asset(status="OUT_OF_SERVICE")
        self.assertEqual(self.zone.etat_materiel, Zone.ETAT_DANGER)


class PlanNavireConsultationAccesTests(TestCase):
    """La page de consultation est ouverte à tous les rôles (contrairement à
    l'éditeur, réservé CHEF_SERVICE+), mais reste bornée au navire de
    l'utilisateur."""

    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A", code="NAV-A")
        self.ship_b = Ship.objects.create(name="Navire B", code="NAV-B")
        self.pont_a = Deck.objects.create(ship=self.ship_a, name="Pont A", order=1)
        self.pont_b = Deck.objects.create(ship=self.ship_b, name="Pont B", order=1)

        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship_a}
        )

    def test_equipier_peut_consulter_le_plan_de_son_navire(self):
        self.client.login(username="equipier", password="pass")
        r = self.client.get(f"/assets/plan-navire/{self.pont_a.id}/")
        self.assertEqual(r.status_code, 200)

    def test_equipier_ne_peut_pas_consulter_le_plan_dun_autre_navire(self):
        self.client.login(username="equipier", password="pass")
        r = self.client.get(f"/assets/plan-navire/{self.pont_b.id}/")
        self.assertEqual(r.status_code, 403)

    def test_point_dentree_redirige_vers_le_premier_pont_par_ordre(self):
        Deck.objects.create(ship=self.ship_a, name="Pont B", order=2)
        pont_zero = Deck.objects.create(ship=self.ship_a, name="Pont zéro", order=0)
        self.client.login(username="equipier", password="pass")
        r = self.client.get("/assets/plan-navire/")
        self.assertRedirects(r, f"/assets/plan-navire/{pont_zero.id}/")

    def test_navire_sans_pont_configure_affiche_un_message_clair(self):
        ship_c = Ship.objects.create(name="Navire C", code="NAV-C")
        equipier_c = User.objects.create_user(username="equipier_c", password="pass")
        UserProfile.objects.update_or_create(
            user=equipier_c, defaults={"role": "EQUIPIER", "ship": ship_c}
        )
        self.client.login(username="equipier_c", password="pass")
        r = self.client.get("/assets/plan-navire/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Aucun pont n'est encore configuré")


class PlanNavireConsultationRenduTests(TestCase):
    """Rendu de la page : navigation par onglets, overlay coloré, lien vers
    le matériel filtré par emplacement."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)
        self.emplacement = Location.objects.create(ship=self.ship, name="Local machine")
        self.pont = Deck.objects.create(ship=self.ship, name="Pont A", order=1, image=_image_1x1_png())
        self.zone = Zone.objects.create(
            deck=self.pont, name="Local machine avant", location=self.emplacement,
            points=[{"x": 10, "y": 10}, {"x": 40, "y": 10}, {"x": 40, "y": 30}, {"x": 10, "y": 30}],
        )
        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship}
        )
        self.client.login(username="equipier", password="pass")

    def test_page_affiche_les_onglets_et_la_zone(self):
        Deck.objects.create(ship=self.ship, name="Pont B", order=2)
        r = self.client.get(f"/assets/plan-navire/{self.pont.id}/")
        self.assertContains(r, "Pont A")
        self.assertContains(r, "Pont B")
        self.assertContains(r, "Local machine avant")

    def test_clic_sur_une_zone_pointe_vers_la_liste_filtree_par_emplacement(self):
        r = self.client.get(f"/assets/plan-navire/{self.pont.id}/")
        self.assertContains(r, f"/assets/?location={self.emplacement.id}")

    def test_liste_du_materiel_filtree_par_emplacement_ne_montre_que_la_zone(self):
        asset_dans_la_zone = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            location=self.emplacement,
        )
        autre_emplacement = Location.objects.create(ship=self.ship, name="Passerelle")
        Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            location=autre_emplacement,
        )
        r = self.client.get(f"/assets/?location={self.emplacement.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(r.context["assets"]), [asset_dans_la_zone])
