"""Tests de la recherche globale (/search/) — faille de sécurité corrigée :
la vue était accessible sans authentification et sans filtre de périmètre.

Vérifie que la recherche est réservée aux utilisateurs connectés et que
chaque résultat (matériel, ticket, personne, anomalie, ronde, échange de
service) est restreint au périmètre de l'utilisateur — via
scope_filters_for_user pour les types "historiques", et via les fonctions de
périmètre propres à chaque app pour les types ajoutés le 22/09/2026
(anomalies_visibles, modeles_visibles/rondes_visibles, peut_valider_echange) :
aucun nouveau système de scope n'est créé, l'existant est réutilisé partout.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ServiceFunctionChoice, UserProfile
from assets.models import Asset, AssetDocument, AssetType, Installation
from logistics.models import Anomalie, CorrectiveTicket
from org.models import Sector, Section, Service, Ship
from quarts.models import ChefDeListe, CreneauServiceGarde, EchangeService, ServiceGarde
from rondes.models import Ronde, RondeModele
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

        # Anomalie : un équipier sans section ne voit (hors chef) que SES
        # propres signalements (logistics.anomalie_views.anomalies_visibles)
        # — pas de notion de navire ici, contrairement aux types ci-dessus.
        self.anomalie_dans_perimetre = Anomalie.objects.create(
            titre="Anomalie CIBLE A", created_by=self.marin, updated_by=self.marin,
        )
        self.anomalie_hors_perimetre = Anomalie.objects.create(
            titre="Anomalie CIBLE B", created_by=self.autre_marin, updated_by=self.autre_marin,
        )

        # Ronde : modèle et occurrence rattachés directement au niveau navire
        # (rondes.services.perimetre_couvrant_q couvre le navire du marin).
        self.ronde_modele_dans_perimetre = RondeModele(nom="Ronde CIBLE A", created_by=self.marin)
        self.ronde_modele_dans_perimetre.rattacher(ship=self.navire_a)
        self.ronde_modele_dans_perimetre.save()
        self.ronde_modele_hors_perimetre = RondeModele(nom="Ronde CIBLE B", created_by=self.autre_marin)
        self.ronde_modele_hors_perimetre.rattacher(ship=self.navire_b)
        self.ronde_modele_hors_perimetre.save()

        self.ronde_dans_perimetre = Ronde.objects.create(
            nom="Ronde CIBLE A", ship=self.navire_a, date_prevue=timezone.localdate(),
        )
        self.ronde_hors_perimetre = Ronde.objects.create(
            nom="Ronde CIBLE B", ship=self.navire_b, date_prevue=timezone.localdate(),
        )

        # Échange de service : visible uniquement du demandeur, de la cible ou
        # du chef de liste habilité (quarts.echanges.peut_valider_echange) —
        # ni le navire ni le rôle générique n'entrent en jeu.
        self.demandeur_echange = User.objects.create_user(username="svc_demandeur_cible", password="pass")
        UserProfile.objects.filter(user=self.demandeur_echange).update(role="EQUIPIER", sector=self.secteur_a)
        self.cible_echange = User.objects.create_user(username="svc_cible_cible", password="pass")
        UserProfile.objects.filter(user=self.cible_echange).update(role="EQUIPIER", sector=self.secteur_a)
        self.chef_liste_echange = User.objects.create_user(username="svc_chef_cible", password="pass")
        UserProfile.objects.filter(user=self.chef_liste_echange).update(role="EQUIPIER", sector=self.secteur_a)
        ChefDeListe.objects.create(user=self.chef_liste_echange, sector=self.secteur_a)

        garde = ServiceGarde.objects.create(
            sector=self.secteur_a, fonction=ServiceFunctionChoice.objects.create(name="Permanence CIBLE"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=30),
            statut=ServiceGarde.STATUT_PUBLIEE, created_by=self.chef_liste_echange,
        )
        debut = timezone.now() + timedelta(days=5)
        creneau_demandeur = CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Quart CIBLE", debut=debut, fin=debut + timedelta(hours=24),
            marin=self.demandeur_echange,
        )
        creneau_cible = CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Quart CIBLE", debut=debut + timedelta(days=1),
            fin=debut + timedelta(days=1, hours=24), marin=self.cible_echange,
        )
        self.echange = EchangeService.objects.create(
            creneau_demandeur=creneau_demandeur, creneau_cible=creneau_cible,
            libelle_creneau_demandeur="« Quart CIBLE » du tour A", libelle_creneau_cible="« Quart CIBLE » du tour B",
            demandeur=self.demandeur_echange, cible=self.cible_echange,
        )

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

    def test_recherche_ne_renvoie_que_les_anomalies_du_perimetre(self):
        self.client.login(username="marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertEqual(response.status_code, 200)
        anomalies = list(response.context["anomalies"])
        self.assertIn(self.anomalie_dans_perimetre, anomalies)
        self.assertNotIn(self.anomalie_hors_perimetre, anomalies)

    def test_recherche_anomalies_inversee_pour_lautre_marin(self):
        self.client.login(username="autre_marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        anomalies = list(response.context["anomalies"])
        self.assertIn(self.anomalie_hors_perimetre, anomalies)
        self.assertNotIn(self.anomalie_dans_perimetre, anomalies)

    def test_recherche_ne_renvoie_que_les_modeles_de_ronde_du_perimetre(self):
        self.client.login(username="marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertEqual(response.status_code, 200)
        modeles = list(response.context["ronde_modeles"])
        self.assertIn(self.ronde_modele_dans_perimetre, modeles)
        self.assertNotIn(self.ronde_modele_hors_perimetre, modeles)

    def test_recherche_ne_renvoie_que_les_rondes_du_perimetre(self):
        self.client.login(username="marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertEqual(response.status_code, 200)
        rondes = list(response.context["rondes"])
        self.assertIn(self.ronde_dans_perimetre, rondes)
        self.assertNotIn(self.ronde_hors_perimetre, rondes)

    def test_recherche_rondes_inversee_pour_lautre_marin(self):
        self.client.login(username="autre_marin_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        modeles = list(response.context["ronde_modeles"])
        rondes = list(response.context["rondes"])
        self.assertIn(self.ronde_modele_hors_perimetre, modeles)
        self.assertNotIn(self.ronde_modele_dans_perimetre, modeles)
        self.assertIn(self.ronde_hors_perimetre, rondes)
        self.assertNotIn(self.ronde_dans_perimetre, rondes)

    def test_recherche_echange_visible_par_le_demandeur_et_la_cible(self):
        for identifiant in ("svc_demandeur_cible", "svc_cible_cible"):
            self.client.login(username=identifiant, password="pass")
            response = self.client.get(self.url, {"q": "CIBLE"})
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.echange, list(response.context["echanges"]))

    def test_recherche_echange_visible_par_le_chef_de_liste_habilite(self):
        self.client.login(username="svc_chef_cible", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertIn(self.echange, list(response.context["echanges"]))

    def test_recherche_echange_invisible_pour_un_marin_non_concerne(self):
        # Même s'il est dans le même secteur que la garde, un marin qui n'est
        # ni demandeur, ni cible, ni chef de liste ne doit pas voir l'échange
        # (contrairement aux autres types, aucun scope géographique ne
        # s'applique ici — seule la relation directe à l'échange compte).
        marin_du_secteur = User.objects.create_user(username="marin_secteur_a_intrus", password="pass")
        UserProfile.objects.filter(user=marin_du_secteur).update(role="EQUIPIER", sector=self.secteur_a)
        self.client.login(username="marin_secteur_a_intrus", password="pass")
        response = self.client.get(self.url, {"q": "CIBLE"})
        self.assertNotIn(self.echange, list(response.context["echanges"]))
