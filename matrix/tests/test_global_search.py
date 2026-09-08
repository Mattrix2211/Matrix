"""Tests de la recherche globale (/search/) — faille de sécurité corrigée :
la vue était accessible sans authentification et sans filtre de périmètre.

Vérifie que la recherche est réservée aux utilisateurs connectés et que
chaque résultat (matériel, ticket, personne) est restreint au périmètre de
l'utilisateur via scope_filters_for_user (pas de nouveau système de scope).
"""
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetDocument, AssetType, Installation
from logistics.models import CorrectiveTicket
from org.models import Sector, Section, Service, Ship
from training.models import TrainingCourse


class GlobalSearchViewTests(TestCase):
    def setUp(self):
        # Périmètre A : le navire dont dépend l'utilisateur testé
        self.navire_a = Ship.objects.create(name="Navire A", code="NAVA")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.section_a = Section.objects.create(sector=self.secteur_a, name="Section A")
        self.type_asset_a = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.secteur_a)

        # Périmètre B : un autre navire, hors périmètre de l'utilisateur testé
        self.navire_b = Ship.objects.create(name="Navire B", code="NAVB")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.type_asset_b = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.secteur_b)

        self.asset_dans_perimetre = Asset.objects.create(
            asset_type=self.type_asset_a, internal_id="MAT-CIBLE-001", serial_number="SN-001",
            ship=self.navire_a, service=self.service_a, sector=self.secteur_a, section=self.section_a,
        )
        self.asset_hors_perimetre = Asset.objects.create(
            asset_type=self.type_asset_b, internal_id="MAT-CIBLE-002", serial_number="SN-002",
            ship=self.navire_b, service=self.service_b, sector=self.secteur_b,
        )

        self.ticket_dans_perimetre = CorrectiveTicket.objects.create(
            asset=self.asset_dans_perimetre, description="Fuite CIBLE sur pompe",
        )
        self.ticket_hors_perimetre = CorrectiveTicket.objects.create(
            asset=self.asset_hors_perimetre, description="Fuite CIBLE sur vanne",
        )

        self.installation_dans_perimetre = Installation.objects.create(
            designation="Pompe CIBLE A",
            ship=self.navire_a, service=self.service_a, sector=self.secteur_a, section=self.section_a,
        )
        self.installation_hors_perimetre = Installation.objects.create(
            designation="Pompe CIBLE B",
            ship=self.navire_b, service=self.service_b, sector=self.secteur_b,
        )

        self.document_dans_perimetre = AssetDocument.objects.create(
            asset=self.asset_dans_perimetre, name="Notice CIBLE A",
            file=SimpleUploadedFile("notice_a.pdf", b"contenu"),
        )
        self.document_hors_perimetre = AssetDocument.objects.create(
            asset=self.asset_hors_perimetre, name="Notice CIBLE B",
            file=SimpleUploadedFile("notice_b.pdf", b"contenu"),
        )

        # Formation : fiche globale (aucun rattachement navire), donc sans
        # notion de fuite de périmètre — seul le statut de validation du
        # catalogue (cf. TrainingCourseListView) filtre les résultats.
        self.formation_active = TrainingCourse.objects.create(
            title="Secourisme CIBLE", statut_validation="ACTIVE",
        )
        self.formation_en_attente = TrainingCourse.objects.create(
            title="Formation CIBLE en attente", statut_validation="WAITING_VALIDATION",
        )

        self.marin = User.objects.create_user(username="marin_cible", email="marin.cible@navy.fr", password="pass")
        UserProfile.objects.filter(user=self.marin).update(role="EQUIPIER", ship=self.navire_a)

        self.autre_marin = User.objects.create_user(
            username="autre_marin_cible", email="autre.cible@navy.fr", password="pass",
        )
        UserProfile.objects.filter(user=self.autre_marin).update(role="EQUIPIER", ship=self.navire_b)

        self.url = reverse("global-search")

    def test_recherche_non_authentifiee_est_rejetee(self):
        response = self.client.get(self.url, {"q": "CIBLE"})
        # LoginRequiredMixin/login_required redirige vers la page de connexion
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_recherche_ne_renvoie_que_le_materiel_du_perimetre(self):
        self.client.login(username="marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertEqual(response.status_code, 200)
        assets = list(response.context["assets"])
        self.assertIn(self.asset_dans_perimetre, assets)
        self.assertNotIn(self.asset_hors_perimetre, assets)

    def test_recherche_ne_renvoie_que_les_tickets_du_perimetre(self):
        self.client.login(username="marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertEqual(response.status_code, 200)
        tickets = list(response.context["tickets"])
        self.assertIn(self.ticket_dans_perimetre, tickets)
        self.assertNotIn(self.ticket_hors_perimetre, tickets)

    def test_recherche_ne_renvoie_que_les_personnes_du_perimetre(self):
        self.client.login(username="marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "cible"})
        self.assertEqual(response.status_code, 200)
        users = list(response.context["users"])
        self.assertIn(self.marin, users)
        self.assertNotIn(self.autre_marin, users)

    def test_recherche_ne_renvoie_que_les_installations_du_perimetre(self):
        self.client.login(username="marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertEqual(response.status_code, 200)
        installations = list(response.context["installations"])
        self.assertIn(self.installation_dans_perimetre, installations)
        self.assertNotIn(self.installation_hors_perimetre, installations)

    def test_recherche_ne_renvoie_que_les_documents_du_perimetre(self):
        self.client.login(username="marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertEqual(response.status_code, 200)
        documents = list(response.context["documents"])
        self.assertIn(self.document_dans_perimetre, documents)
        self.assertNotIn(self.document_hors_perimetre, documents)

    def test_recherche_formations_catalogue_actif_visible_quel_que_soit_le_navire(self):
        # Les formations sont un référentiel global partagé par toute la
        # flotte (aucun rattachement navire) : la formation active doit être
        # visible pour les deux marins, quel que soit leur navire.
        for identifiant in ("marin_cible", "autre_marin_cible"):
            self.client.login(username=identifiant, password="pass")
            response = self.client.get(self.url, {"q": "CIBLE"})
            formations = list(response.context["formations"])
            self.assertIn(self.formation_active, formations)
            # En attente de validation (Circuit C) : invisible du catalogue,
            # comme pour la liste des formations (TrainingCourseListView).
            self.assertNotIn(self.formation_en_attente, formations)

    def test_autre_navire_ne_voit_pas_le_perimetre_a(self):
        self.client.login(username="autre_marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertEqual(response.status_code, 200)
        assets = list(response.context["assets"])
        tickets = list(response.context["tickets"])
        installations = list(response.context["installations"])
        documents = list(response.context["documents"])
        self.assertNotIn(self.asset_dans_perimetre, assets)
        self.assertNotIn(self.ticket_dans_perimetre, tickets)
        self.assertNotIn(self.installation_dans_perimetre, installations)
        self.assertNotIn(self.document_dans_perimetre, documents)
        self.assertIn(self.asset_hors_perimetre, assets)
        self.assertIn(self.ticket_hors_perimetre, tickets)
        self.assertIn(self.installation_hors_perimetre, installations)
        self.assertIn(self.document_hors_perimetre, documents)
