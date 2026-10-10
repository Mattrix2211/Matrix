"""Liens directs des notifications : objet visible seulement si le marin peut l'ouvrir."""
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from assets.models import Asset, AssetType
from logistics.models import Anomalie, CorrectiveTicket
from notifications.liens import liens_accessibles
from notifications.models import Notification, NotificationLevel
from notifications.services import compter_non_lues
from org.models import Sector, Service, Ship
from rondes.models import Ronde, RondeModele


class LiensDirectsTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire L", code="NVL")
        service = Service.objects.create(ship=self.navire, name="Service L")
        self.secteur = Sector.objects.create(service=service, name="Secteur L")
        autre = Sector.objects.create(service=service, name="Autre secteur L")
        self.marin = self._marin("marin_l", self.secteur)
        self.voisin = self._marin("voisin_l", autre)
        type_asset = AssetType.objects.create(name="Pompe", category="MCO", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=type_asset, internal_id="POMPE-L", ship=self.navire, service=service, sector=self.secteur)
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite")

    def _marin(self, nom, secteur):
        user = User.objects.create_user(username=nom, password="pass")
        profil = user.profile
        profil.role, profil.sector, profil.service, profil.ship = "CHEF_SECTEUR", secteur, secteur.service, self.navire
        profil.save()
        return user

    def lien(self, user, cible=None, **champs):
        notification = Notification.objects.create(user=user, verb="Information", target=cible, **champs)
        notification = Notification.objects.select_related("content_type").get(pk=notification.pk)
        return liens_accessibles(SimpleNamespace(user=user), [notification]).get(notification.pk)

    def test_ticket_visible_du_perimetre_seulement(self):
        self.assertEqual(self.lien(self.marin, self.ticket), reverse("ticket-detail", args=[self.ticket.pk]))
        self.assertIsNone(self.lien(self.voisin, self.ticket))

    def test_anomalie_et_ronde(self):
        anomalie = Anomalie.objects.create(titre="Odeur", description="x", created_by=self.marin, ship=self.navire)
        self.assertEqual(self.lien(self.marin, anomalie), reverse("anomalie-detail", args=[anomalie.pk]))
        modele = RondeModele.objects.create(nom="Ronde L", ship=self.navire, sector=self.secteur)
        ronde = Ronde.objects.create(modele=modele, nom="Ronde L", ship=self.navire, sector=self.secteur, date_prevue="2026-10-10")
        self.assertEqual(self.lien(self.marin, ronde), reverse("ronde-detail", args=[ronde.pk]))

    def test_chemin_interne_seulement(self):
        self.assertEqual(self.lien(self.marin, url="/quarts/"), "/quarts/")
        for chemin in ("https://exemple.test/", "//exemple.test/", "javascript:alert(1)", "/\\evil"):
            self.assertIsNone(self.lien(self.marin, url=chemin), chemin)

    def test_niveaux_renommes_et_compteur_unique(self):
        self.assertEqual(dict(NotificationLevel.choices)["warning"], "Important")
        self.assertEqual(dict(NotificationLevel.choices)["danger"], "Urgent")
        Notification.objects.create(user=self.marin, verb="a")
        Notification.objects.create(user=self.marin, verb="b", is_read=True)
        self.assertEqual(compter_non_lues(self.marin), 1)
