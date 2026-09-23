from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from notifications.models import Notification, NotificationLevel
from org.models import Sector, Service, Ship


class TicketCreateViewTests(TestCase):
    """Signalement rapide d'une anomalie depuis la fiche d'un matériel mobile
    (bouton « Signaler une anomalie » du scan QR ou de la fiche équipement).
    """

    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A", code="NA")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.sector_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )

        self.ship_b = Ship.objects.create(name="Navire B", code="NB")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )

        self.marin = User.objects.create_user(username="marin_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship_a}
        )
        self.client.login(username="marin_a", password="pass")

    def test_signalement_cree_un_ticket_et_redirige_vers_le_detail(self):
        response = self.client.post(
            f"/logistics/tickets/creer/{self.asset_a.id}/",
            {"description": "Fuite constatée", "severity": "4"},
        )
        ticket = CorrectiveTicket.objects.get(asset=self.asset_a)
        self.assertRedirects(response, f"/logistics/tickets/{ticket.id}/")
        self.assertEqual(ticket.description, "Fuite constatée")
        self.assertEqual(ticket.severity, 4)
        self.assertEqual(ticket.status, "REPORTED")
        self.assertIn(self.marin, ticket.assignees.all())

    def test_signalement_sans_description_est_refuse(self):
        self.client.post(f"/logistics/tickets/creer/{self.asset_a.id}/", {"description": "  "})
        self.assertFalse(CorrectiveTicket.objects.filter(asset=self.asset_a).exists())

    def test_signalement_sur_materiel_hors_perimetre_rejete(self):
        response = self.client.post(
            f"/logistics/tickets/creer/{self.asset_b.id}/", {"description": "Anomalie"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CorrectiveTicket.objects.filter(asset=self.asset_b).exists())


class TicketCreateViewNotificationTests(TestCase):
    """Le signalement d'une anomalie doit informer réellement les chefs du
    périmètre concerné (tâche Notion « Élargir les notifications au-delà du
    seul niveau DANGER »), pas seulement apparaître dans la liste des tickets."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Notif", code="NN")
        self.service = Service.objects.create(ship=self.ship, name="Service Notif")
        self.sector = Sector.objects.create(service=self.service, name="Secteur Notif")
        self.asset_type = AssetType.objects.create(name="Pompe", category="Méca", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
        )

        self.equipier = User.objects.create_user(username="equipier_notif", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship}
        )

        self.chef_secteur = User.objects.create_user(username="chef_secteur_notif", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector}
        )

        self.client.login(username="equipier_notif", password="pass")

    def test_chef_du_perimetre_est_notifie_a_la_creation(self):
        self.client.post(
            f"/logistics/tickets/creer/{self.asset.id}/",
            {"description": "Fuite hydraulique", "severity": "3"},
        )
        notif = Notification.objects.get(user=self.chef_secteur)
        self.assertEqual(notif.level, NotificationLevel.WARNING)
        self.assertIn("Fuite hydraulique", notif.verb)

    def test_severite_faible_notifie_en_info(self):
        self.client.post(
            f"/logistics/tickets/creer/{self.asset.id}/",
            {"description": "Rayure cosmétique", "severity": "1"},
        )
        notif = Notification.objects.get(user=self.chef_secteur)
        self.assertEqual(notif.level, NotificationLevel.INFO)

    def test_severite_elevee_notifie_en_danger_avec_push_reserve(self):
        self.client.post(
            f"/logistics/tickets/creer/{self.asset.id}/",
            {"description": "Panne majeure", "severity": "5"},
        )
        notif = Notification.objects.get(user=self.chef_secteur)
        self.assertEqual(notif.level, NotificationLevel.DANGER)

    def test_le_signaleur_lui_meme_nest_pas_notifie_en_double(self):
        # Le signaleur (equipier_notif) est déjà auto-assigné au ticket : il
        # sait ce qu'il vient de faire, pas besoin de le lui notifier.
        self.client.post(
            f"/logistics/tickets/creer/{self.asset.id}/",
            {"description": "Fuite", "severity": "3"},
        )
        self.assertFalse(Notification.objects.filter(user=self.equipier).exists())
