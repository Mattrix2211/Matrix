"""Double équipage : l'équipage à terre voit « Aujourd'hui » en lecture seule."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from matrix.core.equipage import equipage_a_terre_lecture_seule
from org.models import Sector, Service, Ship


class EquipageATerreTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(
            name="FREMM test", code="FR-EQ", double_equipage=True, equipage_a_bord="A",
        )
        service = Service.objects.create(ship=self.navire, name="Énergie")
        secteur = Sector.objects.create(service=service, name="Propulsion")
        self.bord = self._marin("bord", "A", service)
        self.terre = self._marin("terre", "B", service)
        type_ = AssetType.objects.create(name="Pompe", category="Incendie", sector=secteur)
        asset = Asset.objects.create(asset_type=type_, ship=self.navire, service=service, sector=secteur)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle", every_n_days=30)
        self.occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.localdate() + timedelta(days=1), status="ASSIGNED",
        )
        self.occ.assignees.add(self.bord, self.terre)

    def _marin(self, nom, equipage, service):
        user = User.objects.create_user(username=nom, password="pass")
        profil = user.profile
        profil.ship, profil.service, profil.equipage = self.navire, service, equipage
        profil.save()
        return user

    def test_helper(self):
        self.assertTrue(equipage_a_terre_lecture_seule(self.terre, self.navire))
        self.assertFalse(equipage_a_terre_lecture_seule(self.bord, self.navire))

    def test_helper_sans_effet_hors_double_equipage_ou_sans_equipage(self):
        self.navire.double_equipage = False
        self.assertFalse(equipage_a_terre_lecture_seule(self.terre, self.navire))
        self.navire.double_equipage = True
        self.terre.profile.equipage = ""
        self.assertFalse(equipage_a_terre_lecture_seule(self.terre, self.navire))

    def test_rotation_inverse_les_roles(self):
        self.navire.equipage_a_bord = "B"
        self.navire.save()
        self.assertFalse(equipage_a_terre_lecture_seule(User.objects.get(pk=self.terre.pk), self.navire))
        self.assertTrue(equipage_a_terre_lecture_seule(User.objects.get(pk=self.bord.pk), self.navire))

    def test_page_equipage_a_terre_bandeau_et_actions_masquees(self):
        self.client.login(username="terre", password="pass")
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Lecture seule")
        self.assertContains(r, "Équipage B à terre")
        self.assertNotContains(r, reverse("occurrence-execute", args=[self.occ.pk]))

    def test_page_equipage_a_bord_inchangee(self):
        self.client.login(username="bord", password="pass")
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "Lecture seule")
        self.assertContains(r, reverse("occurrence-execute", args=[self.occ.pk]))

    def test_ecritures_refusees_a_l_equipage_a_terre(self):
        self.client.login(username="terre", password="pass")
        for nom, donnees in (
            ("occurrence-execute", {"conformity": "CONFORME"}),
            ("occurrence-comment-create", {"body": "ok"}),
            ("occurrence-self-assign", {}),
        ):
            with self.subTest(nom):
                r = self.client.post(reverse(nom, args=[self.occ.pk]), donnees)
                self.assertEqual(r.status_code, 403)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "ASSIGNED")

    def test_ecriture_equipage_a_bord_non_bloquee(self):
        self.client.login(username="bord", password="pass")
        r = self.client.post(reverse("occurrence-comment-create", args=[self.occ.pk]), {"body": "ok"})
        self.assertNotEqual(r.status_code, 403)
