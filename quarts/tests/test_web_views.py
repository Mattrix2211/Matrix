"""Tests de l'interface web : création/affectation/publication d'une liste,
et désignation des chefs de liste."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from notifications.models import Notification
from org.models import Sector, Section, Service, Ship
from quarts.models import ChefDeListe, CreneauQuart, Quart, ServiceGarde


class CreationListeTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Web Création", code="WCR")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Pont"), name="Manœuvre"
        )

        self.cdl = User.objects.create_user(username="cdl_creation", password="pass")
        UserProfile.objects.update_or_create(user=self.cdl, defaults={"role": "EQUIPIER"})
        ChefDeListe.objects.create(user=self.cdl, sector=self.sector)

        self.equipier = User.objects.create_user(username="equipier_creation", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})

    def _payload(self, action="creer_quart"):
        return {
            "action": action,
            "perimetre": f"sector:{self.sector.pk}",
            "nom": "Semaine test",
            "date_debut": str(timezone.localdate()),
            "date_fin": str(timezone.localdate() + timedelta(days=6)),
        }

    def test_chef_de_liste_peut_creer_un_quart_sur_son_perimetre(self):
        self.client.login(username="cdl_creation", password="pass")
        r = self.client.post("/quarts/", self._payload("creer_quart"))
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(Quart.objects.filter(sector=self.sector, nom="Semaine test").exists())

    def test_chef_de_liste_peut_creer_un_service_de_garde_sur_son_perimetre(self):
        self.client.login(username="cdl_creation", password="pass")
        r = self.client.post("/quarts/", self._payload("creer_service_garde"))
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(ServiceGarde.objects.filter(sector=self.sector, nom="Semaine test").exists())

    def test_non_designe_ne_peut_pas_creer_de_liste(self):
        self.client.login(username="equipier_creation", password="pass")
        r = self.client.post("/quarts/", self._payload("creer_quart"))
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Quart.objects.filter(sector=self.sector).exists())

    def test_chef_de_liste_ne_peut_pas_creer_sur_un_autre_perimetre(self):
        autre_secteur = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Autre service"), name="Autre secteur"
        )
        self.client.login(username="cdl_creation", password="pass")
        payload = self._payload("creer_quart")
        payload["perimetre"] = f"sector:{autre_secteur.pk}"
        r = self.client.post("/quarts/", payload)
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Quart.objects.filter(sector=autre_secteur).exists())

    def test_index_liste_les_listes_du_chef_de_liste(self):
        Quart.objects.create(sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate())
        self.client.login(username="cdl_creation", password="pass")
        r = self.client.get("/quarts/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["quarts"]), 1)


class GestionCreneauxEtPublicationTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Web Gestion", code="WGE")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Machine"), name="Propulsion"
        )
        self.section = Section.objects.create(sector=self.sector, name="Turbines")

        self.cdl = User.objects.create_user(username="cdl_gestion", password="pass")
        UserProfile.objects.update_or_create(user=self.cdl, defaults={"role": "EQUIPIER"})
        ChefDeListe.objects.create(user=self.cdl, sector=self.sector)

        self.marin = User.objects.create_user(username="marin_gestion", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "section": self.section})

        self.marin_hors_perimetre = User.objects.create_user(username="marin_hors_gestion", password="pass")
        UserProfile.objects.update_or_create(user=self.marin_hors_perimetre, defaults={"role": "EQUIPIER"})

        self.quart = Quart.objects.create(
            sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
        )

    def test_chef_de_liste_peut_ajouter_un_creneau_avec_marin_du_perimetre(self):
        self.client.login(username="cdl_gestion", password="pass")
        debut = (timezone.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {
            "action": "ajouter_creneau", "poste": "Passerelle", "debut": debut, "marin": self.marin.pk,
        })
        self.assertEqual(r.status_code, 302, r.content)
        creneau = CreneauQuart.objects.get(quart=self.quart)
        self.assertEqual(creneau.marin, self.marin)
        # Durée par défaut appliquée (4h) faute de date de fin saisie.
        self.assertEqual(creneau.fin - creneau.debut, timedelta(hours=self.quart.duree_creneau_heures))

    def test_ne_peut_pas_affecter_un_marin_hors_perimetre(self):
        self.client.login(username="cdl_gestion", password="pass")
        debut = (timezone.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {
            "action": "ajouter_creneau", "poste": "Passerelle", "debut": debut, "marin": self.marin_hors_perimetre.pk,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(CreneauQuart.objects.filter(quart=self.quart).exists())

    def test_gestionnaire_non_designe_ne_peut_pas_modifier_la_liste(self):
        autre = User.objects.create_user(username="autre_gestion", password="pass")
        UserProfile.objects.update_or_create(user=autre, defaults={"role": "EQUIPIER"})
        self.client.login(username="autre_gestion", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "publier"})
        self.assertEqual(r.status_code, 400)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_BROUILLON)

    def test_publication_via_le_web_notifie_le_marin_affecte(self):
        debut = timezone.now() + timedelta(hours=3)
        CreneauQuart.objects.create(quart=self.quart, poste="Passerelle", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)
        self.client.login(username="cdl_gestion", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "publier"})
        self.assertEqual(r.status_code, 302)
        self.quart.refresh_from_db()
        self.assertEqual(self.quart.statut, Quart.STATUT_PUBLIEE)
        self.assertTrue(Notification.objects.filter(user=self.marin).exists())

    def test_marin_du_perimetre_peut_lire_une_liste_publiee(self):
        self.quart.publier(self.cdl)
        self.client.login(username="marin_gestion", password="pass")
        r = self.client.get(f"/quarts/quart/{self.quart.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["peut_gerer"])

    def test_marin_ne_peut_pas_lire_un_brouillon(self):
        self.client.login(username="marin_gestion", password="pass")
        r = self.client.get(f"/quarts/quart/{self.quart.pk}/")
        self.assertEqual(r.status_code, 400)

    def test_marin_hors_perimetre_ne_peut_pas_lire_une_liste_publiee(self):
        self.quart.publier(self.cdl)
        self.client.login(username="marin_hors_gestion", password="pass")
        r = self.client.get(f"/quarts/quart/{self.quart.pk}/")
        self.assertEqual(r.status_code, 400)


class DesignationChefDeListeTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Web Désignation", code="WDS")
        self.sector = Sector.objects.create(
            service=Service.objects.create(ship=self.ship, name="Service désignation"), name="Secteur désignation"
        )

        self.chef_service = User.objects.create_user(username="chef_service_dsg", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "sector": self.sector}
        )

        self.chef_secteur_autre_service = User.objects.create_user(username="chef_secteur_dsg_autre", password="pass")
        self.autre_service = Service.objects.create(ship=self.ship, name="Autre service désignation")
        self.autre_secteur = Sector.objects.create(service=self.autre_service, name="Autre secteur désignation")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur_autre_service, defaults={"role": "CHEF_SERVICE", "sector": self.autre_secteur}
        )

        self.candidat = User.objects.create_user(username="candidat_dsg", password="pass")
        UserProfile.objects.update_or_create(user=self.candidat, defaults={"role": "EQUIPIER"})

        self.equipier = User.objects.create_user(username="equipier_dsg", password="pass")
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})

        self.commandant = User.objects.create_user(username="commandant_dsg", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

    def test_chef_service_peut_designer_sur_son_propre_perimetre(self):
        self.client.login(username="chef_service_dsg", password="pass")
        r = self.client.post("/quarts/reglages/", {
            "action": "designer", "user_id": self.candidat.pk, "perimetre": f"sector:{self.sector.pk}",
        })
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(ChefDeListe.objects.filter(user=self.candidat, sector=self.sector).exists())

    def test_chef_service_ne_peut_pas_designer_hors_de_son_perimetre(self):
        self.client.login(username="chef_secteur_dsg_autre", password="pass")
        r = self.client.post("/quarts/reglages/", {
            "action": "designer", "user_id": self.candidat.pk, "perimetre": f"sector:{self.sector.pk}",
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(ChefDeListe.objects.filter(user=self.candidat, sector=self.sector).exists())

    def test_equipier_ne_peut_pas_acceder_a_la_page_de_designation(self):
        self.client.login(username="equipier_dsg", password="pass")
        r = self.client.get("/quarts/reglages/")
        self.assertEqual(r.status_code, 403)

    def test_commandant_peut_designer_sur_nimporte_quel_perimetre(self):
        self.client.login(username="commandant_dsg", password="pass")
        r = self.client.post("/quarts/reglages/", {
            "action": "designer", "user_id": self.candidat.pk, "perimetre": f"sector:{self.autre_secteur.pk}",
        })
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(ChefDeListe.objects.filter(user=self.candidat, sector=self.autre_secteur).exists())

    def test_retirer_une_designation(self):
        cdl = ChefDeListe.objects.create(user=self.candidat, sector=self.sector)
        self.client.login(username="chef_service_dsg", password="pass")
        r = self.client.post("/quarts/reglages/", {"action": "retirer", "pk": cdl.pk})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(ChefDeListe.objects.filter(pk=cdl.pk).exists())
