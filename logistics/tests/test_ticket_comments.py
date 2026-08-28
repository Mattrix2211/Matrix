"""Commentaires transverses de suivi sur un ticket correctif (fiche détail
web) : affichage des messages système et libres, ajout d'un commentaire par
un utilisateur de son périmètre, refus pour un utilisateur hors périmètre.
"""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship
from threads.models import Message, Thread
from threads.utils import ajouter_commentaire


class TicketCommentsTests(TestCase):
    def setUp(self):
        # Navire A : le ticket et l'utilisateur dans le périmètre
        self.navire = Ship.objects.create(name="Navire commentaires", code="NC")
        self.service = Service.objects.create(ship=self.navire, name="Service NC")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur NC")
        self.asset_type = AssetType.objects.create(name="Pompe", category="Méca", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite constatée")

        self.marin_du_bord = User.objects.create_user(username="marin_nc", password="pass")
        UserProfile.objects.filter(user=self.marin_du_bord).update(role="EQUIPIER", sector=self.secteur)

        # Navire B : utilisateur hors périmètre
        self.autre_navire = Ship.objects.create(name="Navire B commentaires", code="NCB")
        self.autre_service = Service.objects.create(ship=self.autre_navire, name="Service B")
        self.autre_secteur = Sector.objects.create(service=self.autre_service, name="Secteur B")
        self.marin_hors_perimetre = User.objects.create_user(username="marin_hp", password="pass")
        UserProfile.objects.filter(user=self.marin_hors_perimetre).update(role="EQUIPIER", sector=self.autre_secteur)

        self.url_detail = reverse("ticket-detail", args=[self.ticket.id])
        self.url_commentaire = reverse("ticket-comment-create", args=[self.ticket.id])

    def test_la_fiche_affiche_les_messages_systeme_et_utilisateur(self):
        thread, _ = Thread.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(self.ticket), object_id=str(self.ticket.pk)
        )
        Message.objects.create(thread=thread, author=None, body="Statut: REPORTED → DIAGNOSED", is_system=True)
        ajouter_commentaire(self.ticket, self.marin_du_bord, "Pièce commandée")
        self.client.login(username="marin_nc", password="pass")

        response = self.client.get(self.url_detail)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pièce commandée")
        self.assertContains(response, "Message système")
        self.assertContains(response, "marin_nc")

    def test_distinction_visuelle_systeme_vs_utilisateur(self):
        thread, _ = Thread.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(self.ticket), object_id=str(self.ticket.pk)
        )
        Message.objects.create(thread=thread, author=None, body="Statut: REPORTED → DIAGNOSED", is_system=True)
        Message.objects.create(thread=thread, author=self.marin_du_bord, body="RAS, suivi en cours", is_system=False)

        self.client.login(username="marin_nc", password="pass")
        response = self.client.get(self.url_detail)

        contenu = response.content.decode()
        # Le message système porte le badge dédié, pas le message utilisateur.
        self.assertIn("Message système", contenu)
        position_systeme = contenu.index("Statut: REPORTED")
        position_badge_systeme = contenu.rindex("Message système", 0, position_systeme)
        self.assertGreater(position_systeme, position_badge_systeme)
        self.assertIn("RAS, suivi en cours", contenu)

    def test_un_utilisateur_du_perimetre_peut_ajouter_un_commentaire(self):
        self.client.login(username="marin_nc", password="pass")

        response = self.client.post(self.url_commentaire, {"body": "Contrôle effectué, RAS."}, follow=True)

        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(body="Contrôle effectué, RAS.")
        self.assertEqual(message.author, self.marin_du_bord)
        self.assertFalse(message.is_system)
        self.assertContains(response, "Contrôle effectué, RAS.")

    def test_le_commentaire_vide_est_refuse(self):
        self.client.login(username="marin_nc", password="pass")

        self.client.post(self.url_commentaire, {"body": "   "}, follow=True)

        self.assertFalse(Message.objects.filter(thread__object_id=str(self.ticket.pk)).exists())

    def test_lecture_refusee_pour_un_utilisateur_hors_perimetre(self):
        self.client.login(username="marin_hp", password="pass")

        response = self.client.get(self.url_detail)

        self.assertIn(response.status_code, (400, 403, 404))

    def test_ecriture_refusee_pour_un_utilisateur_hors_perimetre(self):
        self.client.login(username="marin_hp", password="pass")

        response = self.client.post(self.url_commentaire, {"body": "Je m'incruste"})

        self.assertIn(response.status_code, (400, 403, 404))
        self.assertFalse(Message.objects.filter(body="Je m'incruste").exists())
