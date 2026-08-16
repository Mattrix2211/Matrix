from django.contrib.auth.models import User
from django.test import TestCase
from accounts.models import Roles, UserProfile
from logistics.models import StockPiece
from notifications.models import Notification
from notifications.tasks import notify_low_stock
from org.models import Sector, Section, Service, Ship


class NotifyLowStockTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Ship A", code="A")
        self.service = Service.objects.create(ship=self.ship, name="Tech")
        self.sector = Sector.objects.create(service=self.service, name="Elec")
        self.section = Section.objects.create(sector=self.sector, name="Atelier")

        self.chef_service = User.objects.create_user(username="chef_service", password="pass")
        UserProfile.objects.filter(user=self.chef_service).update(
            role=Roles.CHEF_SERVICE, service=self.service
        )

        self.chef_secteur = User.objects.create_user(username="chef_secteur", password="pass")
        UserProfile.objects.filter(user=self.chef_secteur).update(
            role=Roles.CHEF_SECTEUR, sector=self.sector
        )

        self.chef_section = User.objects.create_user(username="chef_section", password="pass")
        UserProfile.objects.filter(user=self.chef_section).update(
            role=Roles.CHEF_SECTION, section=self.section
        )

    def test_notification_creee_si_piece_sous_le_seuil(self):
        piece = StockPiece.objects.create(
            reference="REF-001",
            designation="Joint torique",
            quantite=1,
            quantite_minimale=5,
            ship=self.ship,
            service=self.service,
            sector=self.sector,
            section=self.section,
        )

        notify_low_stock()

        for user in (self.chef_service, self.chef_secteur, self.chef_section):
            self.assertTrue(
                Notification.objects.filter(user=user, verb__icontains=piece.reference).exists(),
                f"Notification attendue pour {user.username}",
            )

    def test_aucune_notification_si_quantite_suffisante(self):
        StockPiece.objects.create(
            reference="REF-002",
            designation="Roulement",
            quantite=10,
            quantite_minimale=2,
            ship=self.ship,
            service=self.service,
            sector=self.sector,
            section=self.section,
        )

        notify_low_stock()

        self.assertFalse(Notification.objects.filter(verb__icontains="REF-002").exists())

    def test_pas_de_doublon_si_tache_relancee(self):
        piece = StockPiece.objects.create(
            reference="REF-003",
            designation="Filtre",
            quantite=0,
            quantite_minimale=3,
            ship=self.ship,
            service=self.service,
            sector=self.sector,
        )

        notify_low_stock()
        notify_low_stock()

        self.assertEqual(
            Notification.objects.filter(user=self.chef_service, verb__icontains="REF-003").count(), 1
        )

    def test_notification_resolue_puis_recreee_apres_reapprovisionnement(self):
        # Scénario refusé par le Tech Lead : sous le seuil -> notification active créée
        # -> réapprovisionnement -> la notification doit être résolue (is_read=True,
        # même pattern que "marquer comme lue") -> re-rupture -> une nouvelle
        # notification active doit être créée.
        piece = StockPiece.objects.create(
            reference="REF-005",
            designation="Vanne",
            quantite=1,
            quantite_minimale=5,
            ship=self.ship,
            service=self.service,
            sector=self.sector,
            section=self.section,
        )

        notify_low_stock()
        self.assertTrue(
            Notification.objects.filter(
                user=self.chef_service, verb__icontains="REF-005", is_read=False
            ).exists(),
            "Notification active attendue lors de la rupture initiale",
        )

        # Réapprovisionnement : la quantité repasse au-dessus du seuil.
        StockPiece.objects.filter(pk=piece.pk).update(quantite=20)
        notify_low_stock()
        self.assertFalse(
            Notification.objects.filter(
                user=self.chef_service, verb__icontains="REF-005", is_read=False
            ).exists(),
            "La notification doit être résolue (is_read=True) quand la pièce repasse au-dessus du seuil",
        )

        # Re-rupture : le stock redescend sous le seuil.
        StockPiece.objects.filter(pk=piece.pk).update(quantite=0)
        notify_low_stock()
        self.assertTrue(
            Notification.objects.filter(
                user=self.chef_service, verb__icontains="REF-005", is_read=False
            ).exists(),
            "Une nouvelle notification active doit être créée après une nouvelle rupture",
        )

    def test_chef_section_non_notifie_si_piece_sans_section(self):
        # Une pièce sans section rattachée ne doit pas notifier un chef de section,
        # même s'il gère la section "Atelier" par ailleurs.
        StockPiece.objects.create(
            reference="REF-004",
            designation="Câble",
            quantite=0,
            quantite_minimale=1,
            ship=self.ship,
            service=self.service,
            sector=self.sector,
        )

        notify_low_stock()

        self.assertFalse(
            Notification.objects.filter(user=self.chef_section, verb__icontains="REF-004").exists()
        )
