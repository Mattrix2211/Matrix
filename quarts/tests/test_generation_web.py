"""Tests de l'interface web de la génération intelligente de répartition
(Phase 2, tâche Notion « Génération intelligente des listes de service »)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Sector, Service, Ship
from quarts.models import ChefDeListe, CreneauQuart, Quart


def _marin(nom, secteur):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": "EQUIPIER", "sector": secteur})
    return user


class GenerationWebTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Génération Web", code="GWB")
        self.sector = Sector.objects.create(service=Service.objects.create(ship=self.ship, name="Pont"), name="Manœuvre")

        self.chef = _marin("chef_generation", self.sector)
        ChefDeListe.objects.create(user=self.chef, sector=self.sector)
        self.marin = _marin("marin_generation", self.sector)
        self.marin_hors_perimetre = User.objects.create_user(username="hors_perimetre_generation", password="pass")
        UserProfile.objects.update_or_create(user=self.marin_hors_perimetre, defaults={"role": "EQUIPIER"})

        self.quart = Quart.objects.create(
            sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
        )
        debut = timezone.now() + timedelta(days=1)
        self.creneau = CreneauQuart.objects.create(
            quart=self.quart, poste="Passerelle", debut=debut, fin=debut + timedelta(hours=4),
        )

    def test_generer_proposition_affiche_le_calcul_sans_rien_enregistrer(self):
        self.client.login(username="chef_generation", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "generer_proposition"})
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.context["proposition"])
        self.assertEqual(len(r.context["proposition"]), 1)
        # Le chef de liste fait lui-même partie du périmètre (marin comme un
        # autre) : les deux marins du secteur sont éligibles à charge égale,
        # le départage alphabétique retient "chef_generation".
        eligibles = {m.pk for m in r.context["proposition"][0]["eligibles"]}
        self.assertEqual(eligibles, {self.chef.pk, self.marin.pk})
        self.assertEqual(r.context["proposition"][0]["propose"], self.chef)
        self.creneau.refresh_from_db()
        self.assertIsNone(self.creneau.marin)

    def test_generation_refusee_hors_brouillon(self):
        self.quart.publier(self.chef)
        self.client.login(username="chef_generation", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "generer_proposition"})
        self.assertEqual(r.status_code, 302)

    def test_non_gestionnaire_ne_peut_pas_declencher_la_generation(self):
        self.client.login(username="marin_generation", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "generer_proposition"})
        self.assertEqual(r.status_code, 400)

    def test_appliquer_proposition_affecte_reellement_le_creneau(self):
        self.client.login(username="chef_generation", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {
            "action": "appliquer_proposition", f"creneau_{self.creneau.pk}": self.marin.pk,
        })
        self.assertEqual(r.status_code, 302)
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.marin, self.marin)

    def test_appliquer_proposition_ignore_un_marin_hors_perimetre(self):
        self.client.login(username="chef_generation", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {
            "action": "appliquer_proposition", f"creneau_{self.creneau.pk}": self.marin_hors_perimetre.pk,
        })
        self.assertEqual(r.status_code, 302)
        self.creneau.refresh_from_db()
        self.assertIsNone(self.creneau.marin)

    def test_rejeter_proposition_ne_modifie_rien(self):
        self.client.login(username="chef_generation", password="pass")
        r = self.client.post(f"/quarts/quart/{self.quart.pk}/", {"action": "rejeter_proposition"})
        self.assertEqual(r.status_code, 302)
        self.creneau.refresh_from_db()
        self.assertIsNone(self.creneau.marin)

    def test_bouton_de_generation_disparait_quand_plus_aucun_creneau_libre(self):
        self.creneau.marin = self.marin
        self.creneau.save(update_fields=["marin"])
        self.client.login(username="chef_generation", password="pass")
        r = self.client.get(f"/quarts/quart/{self.quart.pk}/")
        self.assertFalse(r.context["peut_generer_proposition"])
