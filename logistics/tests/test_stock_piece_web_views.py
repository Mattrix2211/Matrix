"""Tests de la vue web du stock de pièces (T14).

Vérifie le scope par périmètre (scope_filters_for_user, T12), le seuil de rôle
pour l'écriture (CHEF_SECTION, même seuil que les autres actions d'écriture du
module logistics), et la création/modification via la vue liste.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from org.models import Sector, Section, Service, Ship
from logistics.models import StockPiece


class StockPieceListViewTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T14", code="T14")
        self.service = Service.objects.create(ship=self.navire, name="Service T14")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur T14")
        self.autre_secteur = Sector.objects.create(service=self.service, name="Autre secteur")
        self.section = Section.objects.create(sector=self.secteur, name="Section T14")

        self.piece_dans_perimetre = StockPiece.objects.create(
            reference="REF-001", designation="Joint torique", quantite=1, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.piece_hors_perimetre = StockPiece.objects.create(
            reference="REF-002", designation="Roulement", quantite=10, quantite_minimale=2,
            ship=self.navire, service=self.service, sector=self.autre_secteur,
        )
        self.piece_conforme = StockPiece.objects.create(
            reference="REF-006", designation="Écrou", quantite=20, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.piece_critique = StockPiece.objects.create(
            reference="REF-007", designation="Fusible", quantite=0, quantite_minimale=3,
            ship=self.navire, service=self.service, sector=self.secteur,
        )

        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.filter(user=self.equipier).update(role="EQUIPIER", sector=self.secteur)

        self.chef = User.objects.create_user(username="chef", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur)

        self.url = reverse("stock-piece-list")

    def test_utilisateur_non_authentifie_redirige_vers_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_liste_scopee_sur_le_perimetre_de_lutilisateur(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        pieces = list(response.context["pieces"])
        self.assertIn(self.piece_dans_perimetre, pieces)
        self.assertNotIn(self.piece_hors_perimetre, pieces)

    def test_equipier_peut_lire_mais_pas_ecrire(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["peut_gerer"])

        response = self.client.post(self.url, {
            "action": "create_piece", "reference": "REF-003", "designation": "Filtre",
            "quantite": "3", "quantite_minimale": "1", "sector_id": self.secteur.id,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(StockPiece.objects.filter(reference="REF-003").exists())

    def test_chef_section_peut_creer_une_piece(self):
        self.client.login(username="chef", password="pass")
        response = self.client.post(self.url, {
            "action": "create_piece", "reference": "REF-003", "designation": "Filtre",
            "quantite": "3", "quantite_minimale": "1", "emplacement": "Magasin",
            "sector_id": self.secteur.id, "section_id": self.section.id,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        piece = StockPiece.objects.get(reference="REF-003")
        self.assertEqual(piece.quantite, 3)
        self.assertEqual(piece.ship, self.navire)
        self.assertEqual(piece.service, self.service)
        self.assertEqual(piece.sector, self.secteur)
        self.assertEqual(piece.section, self.section)

    def test_chef_section_peut_modifier_une_piece(self):
        self.client.login(username="chef", password="pass")
        response = self.client.post(self.url, {
            "action": "edit_piece", "pk": self.piece_dans_perimetre.pk,
            "reference": "REF-001", "designation": "Joint torique", "quantite": "8",
            "quantite_minimale": "5", "sector_id": self.secteur.id,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.piece_dans_perimetre.refresh_from_db()
        self.assertEqual(self.piece_dans_perimetre.quantite, 8)

    def test_creation_sans_secteur_est_refusee(self):
        self.client.login(username="chef", password="pass")
        response = self.client.post(self.url, {
            "action": "create_piece", "reference": "REF-004", "designation": "Sans secteur",
            "quantite": "1", "quantite_minimale": "1",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StockPiece.objects.filter(reference="REF-004").exists())

    def test_badges_visuels_selon_le_niveau_de_stock(self):
        # Pièce sous le seuil mais non nulle -> badge "bas" (--amber) ; pièce à zéro
        # -> badge "critique" (--red) ; pièce au-dessus du seuil -> badge "conforme"
        # (--green-tech, classe dédiée .badge-conforme du design system, T14).
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url)
        contenu = response.content.decode()
        self.assertIn('badge text-bg-warning">Stock bas', contenu)
        self.assertIn('badge text-bg-danger">Stock critique', contenu)
        self.assertIn('badge badge-conforme">Conforme', contenu)

    def test_section_dun_autre_secteur_est_ignoree(self):
        # La section appartient à self.secteur ; on tente de créer avec autre_secteur,
        # la section incohérente doit être ignorée plutôt que de créer une hiérarchie fausse.
        self.client.login(username="chef", password="pass")
        self.client.post(self.url, {
            "action": "create_piece", "reference": "REF-005", "designation": "Test hiérarchie",
            "quantite": "1", "quantite_minimale": "1",
            "sector_id": self.autre_secteur.id, "section_id": self.section.id,
        })
        piece = StockPiece.objects.get(reference="REF-005")
        self.assertIsNone(piece.section)
        self.assertEqual(piece.sector, self.autre_secteur)
