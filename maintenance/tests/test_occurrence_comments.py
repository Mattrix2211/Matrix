"""Commentaires transverses de suivi sur une occurrence de maintenance (fiche
d'exécution web) : affichage des messages système et libres, ajout d'un
commentaire par un utilisateur autorisé (assigné ou chef de section+), refus
pour un utilisateur ni assigné ni chef.
"""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship
from threads.models import Message, Thread
from threads.utils import ajouter_commentaire


class OccurrenceCommentsTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire occ. commentaires", code="NOC")
        self.service = Service.objects.create(ship=self.navire, name="Service NOC")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur NOC")
        self.asset_type = AssetType.objects.create(name="Groupe électrogène", category="Élec", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Plan NOC", every_n_days=30)
        self.occurrence = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=timezone.now().date(), status="PLANNED",
        )

        self.assigne = User.objects.create_user(username="assigne_noc", password="pass")
        self.occurrence.assignees.add(self.assigne)

        self.chef = User.objects.create_user(username="chef_noc", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.tiers = User.objects.create_user(username="tiers_noc", password="pass")

        self.url_detail = reverse("occurrence-execute", args=[self.occurrence.id])
        self.url_commentaire = reverse("occurrence-comment-create", args=[self.occurrence.id])

    def test_la_fiche_affiche_les_messages_systeme_et_utilisateur(self):
        thread, _ = Thread.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(self.occurrence), object_id=str(self.occurrence.pk)
        )
        Message.objects.create(thread=thread, author=None, body="Exécution: CONFORME", is_system=True)
        ajouter_commentaire(self.occurrence, self.assigne, "Pièce à surveiller au prochain passage")

        self.client.login(username="assigne_noc", password="pass")
        response = self.client.get(self.url_detail)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pièce à surveiller au prochain passage")
        self.assertContains(response, "Message système")
        self.assertContains(response, "assigne_noc")

    def test_distinction_visuelle_systeme_vs_utilisateur(self):
        thread, _ = Thread.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(self.occurrence), object_id=str(self.occurrence.pk)
        )
        Message.objects.create(thread=thread, author=None, body="Exécution: CONFORME", is_system=True)
        Message.objects.create(thread=thread, author=self.assigne, body="RAS ce mois-ci", is_system=False)

        self.client.login(username="assigne_noc", password="pass")
        contenu = self.client.get(self.url_detail).content.decode()

        position_systeme = contenu.index("Exécution: CONFORME")
        position_badge_systeme = contenu.rindex("Message système", 0, position_systeme)
        self.assertGreater(position_systeme, position_badge_systeme)
        self.assertIn("RAS ce mois-ci", contenu)

    def test_lassigne_peut_ajouter_un_commentaire(self):
        self.client.login(username="assigne_noc", password="pass")

        response = self.client.post(self.url_commentaire, {"body": "Attention, fuite légère"}, follow=True)

        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(body="Attention, fuite légère")
        self.assertEqual(message.author, self.assigne)
        self.assertFalse(message.is_system)

    def test_le_chef_de_section_peut_ajouter_un_commentaire_sans_etre_assigne(self):
        self.client.login(username="chef_noc", password="pass")

        self.client.post(self.url_commentaire, {"body": "Suivi rapproché demandé"}, follow=True)

        self.assertTrue(Message.objects.filter(body="Suivi rapproché demandé", author=self.chef).exists())

    def test_lecture_refusee_pour_un_tiers_non_assigne(self):
        self.client.login(username="tiers_noc", password="pass")

        response = self.client.get(self.url_detail)

        self.assertEqual(response.status_code, 403)

    def test_ecriture_refusee_pour_un_tiers_non_assigne(self):
        self.client.login(username="tiers_noc", password="pass")

        response = self.client.post(self.url_commentaire, {"body": "Je m'incruste"})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Message.objects.filter(body="Je m'incruste").exists())
