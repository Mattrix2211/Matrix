"""Fuite de périmètre (IDOR) sur OccurrenceExecuteView (interface web).

Avant correction, la vue récupérait l'occurrence par un simple .get(pk=pk),
sans filtrer par périmètre hiérarchique : un marin connaissant l'identifiant
d'une occurrence d'un autre navire pouvait consulter (GET) et exécuter (POST)
sa checklist, alors même qu'aucun lien n'y menait depuis les vues déjà
scopées (tableau de pilotage, calendrier). Cf. tâche [SEC] IDOR cross-navire
sur 4 vues web.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from threads.models import Message


class ScopeLeakOccurrenceExecuteViewTests(TestCase):
    def setUp(self):
        from org.models import Sector, Service, Ship

        # Navire A (celui de l'utilisateur connecté)
        self.ship_a = Ship.objects.create(name="Navire A web occ", code="NA-WOCC")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A web occ")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A web occ")
        self.asset_type_a = AssetType.objects.create(name="TypeA web occ", category="Cat", sector=self.sector_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )
        self.plan_a = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_a, name="Plan A", every_n_days=30)
        self.occ_a = MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )

        # Navire B (hors périmètre de l'utilisateur connecté)
        self.ship_b = Ship.objects.create(name="Navire B web occ", code="NB-WOCC")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B web occ")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B web occ")
        self.asset_type_b = AssetType.objects.create(name="TypeB web occ", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )
        self.plan_b = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_b, name="Plan B", every_n_days=30)
        self.occ_b = MaintenanceOccurrence.objects.create(
            plan=self.plan_b, asset=self.asset_b, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )

        # Chef de secteur du navire A uniquement — au-dessus de CHEF_SECTION,
        # donc pas bloqué par le contrôle d'assignation (assignees), pour
        # isoler strictement le contrôle de périmètre testé ici.
        self.chef_a = User.objects.create_user(username="chef_occ_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_a, defaults={"role": "CHEF_SERVICE", "sector": self.sector_a}
        )
        self.client.login(username="chef_occ_a", password="pass")

    def test_get_occurrence_dun_autre_navire_refusee(self):
        url = reverse("occurrence-execute", args=[self.occ_b.id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

    def test_post_occurrence_dun_autre_navire_refusee(self):
        url = reverse("occurrence-execute", args=[self.occ_b.id])
        r = self.client.post(url, {"conformity": "CONFORME"})
        self.assertEqual(r.status_code, 400)
        self.occ_b.refresh_from_db()
        self.assertEqual(self.occ_b.status, "ASSIGNED")

    def test_get_occurrence_de_son_propre_navire_autorisee(self):
        url = reverse("occurrence-execute", args=[self.occ_a.id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)


class ScopeLeakOccurrenceCommentCreateViewTests(TestCase):
    """OccurrenceCommentCreateView.post() récupérait l'occurrence par un
    simple .get(pk=pk), sans le filtre de périmètre déjà appliqué par
    OccurrenceExecuteView : un chef de secteur (ou rôle supérieur) du navire A
    pouvait poster un commentaire sur une occurrence du navire B en devinant
    son identifiant."""

    def setUp(self):
        from org.models import Sector, Service, Ship

        # Navire A (celui de l'utilisateur connecté)
        self.ship_a = Ship.objects.create(name="Navire A web occ com", code="NA-WOC")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A web occ com")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A web occ com")
        self.asset_type_a = AssetType.objects.create(name="TypeA web occ com", category="Cat", sector=self.sector_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )
        self.plan_a = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_a, name="Plan A com", every_n_days=30)
        self.occ_a = MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )

        # Navire B (hors périmètre de l'utilisateur connecté)
        self.ship_b = Ship.objects.create(name="Navire B web occ com", code="NB-WOC")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B web occ com")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B web occ com")
        self.asset_type_b = AssetType.objects.create(name="TypeB web occ com", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )
        self.plan_b = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_b, name="Plan B com", every_n_days=30)
        self.occ_b = MaintenanceOccurrence.objects.create(
            plan=self.plan_b, asset=self.asset_b, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )

        # Chef de secteur du navire A uniquement — au-dessus de CHEF_SECTION,
        # donc pas bloqué par le contrôle d'assignation, pour isoler
        # strictement le contrôle de périmètre testé ici.
        self.chef_a = User.objects.create_user(username="chef_occ_com_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_a, defaults={"role": "CHEF_SERVICE", "sector": self.sector_a}
        )
        self.client.login(username="chef_occ_com_a", password="pass")

    def test_commentaire_sur_occurrence_dun_autre_navire_refuse(self):
        url = reverse("occurrence-comment-create", args=[self.occ_b.id])
        r = self.client.post(url, {"body": "Je m'incruste depuis un autre navire"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Message.objects.filter(body="Je m'incruste depuis un autre navire").exists())

    def test_commentaire_sur_occurrence_de_son_propre_navire_autorise(self):
        url = reverse("occurrence-comment-create", args=[self.occ_a.id])
        r = self.client.post(url, {"body": "Suivi normal"}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Message.objects.filter(body="Suivi normal").exists())
