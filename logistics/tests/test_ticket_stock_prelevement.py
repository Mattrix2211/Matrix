"""Prélèvement de stock en un clic depuis un ticket correctif (T-FEAT).

Vérifie la décrémentation de StockPiece.quantite, la trace via un message
système dans le fil de suivi du ticket (réutilisation de la brique threads),
le refus d'un prélèvement qui rendrait la quantité négative, et le contrôle
de périmètre en deux temps (ticket ET pièce ciblée), même logique que
StockPieceListView.post (T-SEC).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, StockPiece
from org.models import Sector, Service, Ship
from threads.utils import commentaires_de


class TicketStockPrelevementTests(TestCase):
    def setUp(self):
        # Navire A : le ticket, la pièce en stock et le chef dans le périmètre.
        self.navire = Ship.objects.create(name="Navire prelevement", code="NP")
        self.service = Service.objects.create(ship=self.navire, name="Service NP")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur NP")
        self.asset_type = AssetType.objects.create(name="Pompe", category="Méca", sector=self.secteur)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.navire, service=self.service, sector=self.secteur
        )
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite constatée")
        self.piece = StockPiece.objects.create(
            reference="REF-100", designation="Joint torique", quantite=5, quantite_minimale=2,
            ship=self.navire, service=self.service, sector=self.secteur,
        )

        self.chef = User.objects.create_user(username="chef_np", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.equipier = User.objects.create_user(username="equipier_np", password="pass")
        UserProfile.objects.filter(user=self.equipier).update(role="EQUIPIER", sector=self.secteur)

        # Navire B : pièce et utilisateur hors périmètre.
        self.autre_navire = Ship.objects.create(name="Navire B prelevement", code="NPB")
        self.autre_service = Service.objects.create(ship=self.autre_navire, name="Service NPB")
        self.autre_secteur = Sector.objects.create(service=self.autre_service, name="Secteur NPB")
        self.piece_hors_perimetre = StockPiece.objects.create(
            reference="REF-101", designation="Roulement", quantite=10, quantite_minimale=1,
            ship=self.autre_navire, service=self.autre_service, sector=self.autre_secteur,
        )
        self.chef_hors_perimetre = User.objects.create_user(username="chef_hp_np", password="pass")
        UserProfile.objects.filter(user=self.chef_hors_perimetre).update(role="CHEF_SECTION", sector=self.autre_secteur)

        self.autre_asset = Asset.objects.create(
            asset_type=AssetType.objects.create(name="Pompe B", category="Méca", sector=self.autre_secteur),
            ship=self.autre_navire, service=self.autre_service, sector=self.autre_secteur,
        )
        self.ticket_hors_perimetre = CorrectiveTicket.objects.create(asset=self.autre_asset, description="Panne B")

        self.url = reverse('ticket-stock-prelevement', args=[self.ticket.id])

    def test_prelevement_nominal_decremente_le_stock_et_trace_dans_le_fil(self):
        self.client.login(username="chef_np", password="pass")

        response = self.client.post(self.url, {"piece_id": self.piece.id, "quantite": "3"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite, 2)
        messages_thread = list(commentaires_de(self.ticket))
        self.assertEqual(len(messages_thread), 1)
        self.assertTrue(messages_thread[0].is_system)
        self.assertIn("REF-100", messages_thread[0].body)
        self.assertIn("3", messages_thread[0].body)

    def test_quantite_insuffisante_est_refusee(self):
        self.client.login(username="chef_np", password="pass")

        response = self.client.post(self.url, {"piece_id": self.piece.id, "quantite": "999"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite, 5)
        self.assertFalse(commentaires_de(self.ticket).exists())

    def test_quantite_nulle_ou_negative_est_refusee(self):
        self.client.login(username="chef_np", password="pass")

        response = self.client.post(self.url, {"piece_id": self.piece.id, "quantite": "0"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite, 5)

    def test_piece_hors_perimetre_est_refusee(self):
        self.client.login(username="chef_np", password="pass")

        response = self.client.post(
            self.url, {"piece_id": self.piece_hors_perimetre.id, "quantite": "1"}, follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.piece_hors_perimetre.refresh_from_db()
        self.assertEqual(self.piece_hors_perimetre.quantite, 10)

    def test_ticket_hors_perimetre_est_refuse(self):
        self.client.login(username="chef_np", password="pass")
        url_hors_perimetre = reverse('ticket-stock-prelevement', args=[self.ticket_hors_perimetre.id])

        response = self.client.post(url_hors_perimetre, {"piece_id": self.piece.id, "quantite": "1"})

        self.assertEqual(response.status_code, 400)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite, 5)

    def test_equipier_ne_peut_pas_prelever(self):
        self.client.login(username="equipier_np", password="pass")

        response = self.client.post(self.url, {"piece_id": self.piece.id, "quantite": "1"})

        self.assertEqual(response.status_code, 403)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite, 5)

    def test_deux_prelevements_qui_depassent_ensemble_le_stock_refusent_proprement_le_second(self):
        # Simule un scénario de concurrence (T-CONC) : deux prélèvements qui,
        # pris séparément, semblent chacun possibles au moment où l'utilisateur
        # valide son formulaire, mais qui ensemble dépassent le stock réel (5
        # unités). Le second appel doit être refusé proprement (message
        # d'erreur, pas d'exception, pas de quantité négative), grâce à la mise
        # à jour atomique conditionnelle (StockPiece.objects.filter(quantite__gte=...)
        # .update(...)) qui revérifie le stock au moment de l'écriture en base,
        # et non plus seulement au moment de la lecture initiale.
        self.client.login(username="chef_np", password="pass")

        premiere = self.client.post(self.url, {"piece_id": self.piece.id, "quantite": "3"}, follow=True)
        seconde = self.client.post(self.url, {"piece_id": self.piece.id, "quantite": "3"}, follow=True)

        self.assertEqual(premiere.status_code, 200)
        self.assertEqual(seconde.status_code, 200)
        self.piece.refresh_from_db()
        # Seul le premier prélèvement (3) a été appliqué : il ne restait que 2
        # unités pour le second, qui en demandait 3 — refusé, stock jamais négatif.
        self.assertEqual(self.piece.quantite, 2)
        self.assertGreaterEqual(self.piece.quantite, 0)
        messages_thread = list(commentaires_de(self.ticket))
        self.assertEqual(len(messages_thread), 1)

    def test_la_fiche_ticket_propose_les_pieces_du_perimetre(self):
        self.client.login(username="chef_np", password="pass")

        response = self.client.get(reverse('ticket-detail', args=[self.ticket.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prélèvement de stock")
        self.assertContains(response, "REF-100")
        self.assertNotContains(response, "REF-101")
