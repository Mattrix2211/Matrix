"""Tests de la désignation des responsables transverses (spécialité / classe
de navire) depuis l'onglet « Utilisateurs » des Réglages (/parametre/), tâche
Notion « Dashboards transverses par spécialité et par classe de navire ».

Gestion réservée aux superutilisateurs Django (MASTER_ADMIN), même page et
même règle d'accès que les autres référentiels globaux (grades, spécialités)
déjà gérés par cet onglet."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import ResponsableSpecialite, SpecialityChoice, UserProfile
from org.models import ResponsableClasseNavire


class GestionResponsablesTransversesTests(TestCase):
    def setUp(self):
        self.url = reverse("settings")
        self.specialite = SpecialityChoice.objects.create(name="Électricité")
        self.marin = User.objects.create_user(username="marin_elec", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})
        self.admin = User.objects.create_superuser(username="admin_rt", password="pass", email="a@a.fr")

    def test_utilisateur_non_superuser_ne_peut_pas_designer_de_responsable(self):
        chef = User.objects.create_user(username="chef_rt", password="pass")
        UserProfile.objects.update_or_create(user=chef, defaults={"role": "COMMANDANT"})
        self.client.login(username="chef_rt", password="pass")

        response = self.client.post(self.url, {
            "action": "add_responsable_specialite",
            "specialite_id": self.specialite.id,
            "user_id": self.marin.id,
        })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ResponsableSpecialite.objects.exists())

    def test_master_admin_peut_designer_un_responsable_de_specialite(self):
        self.client.login(username="admin_rt", password="pass")

        response = self.client.post(self.url, {
            "action": "add_responsable_specialite",
            "specialite_id": self.specialite.id,
            "user_id": self.marin.id,
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ResponsableSpecialite.objects.filter(specialite=self.specialite, user=self.marin).exists()
        )

    def test_master_admin_peut_retirer_un_responsable_de_specialite(self):
        responsabilite = ResponsableSpecialite.objects.create(specialite=self.specialite, user=self.marin)
        self.client.login(username="admin_rt", password="pass")

        response = self.client.post(self.url, {
            "action": "retirer_responsable_specialite",
            "pk": responsabilite.id,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ResponsableSpecialite.objects.filter(pk=responsabilite.id).exists())

    def test_master_admin_peut_designer_un_responsable_de_classe_navire(self):
        self.client.login(username="admin_rt", password="pass")

        response = self.client.post(self.url, {
            "action": "add_responsable_classe",
            "name": "La Fayette",
            "user_id": self.marin.id,
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ResponsableClasseNavire.objects.filter(classe_navire="La Fayette", user=self.marin).exists()
        )

    def test_master_admin_peut_retirer_un_responsable_de_classe_navire(self):
        responsabilite = ResponsableClasseNavire.objects.create(classe_navire="Suffren", user=self.marin)
        self.client.login(username="admin_rt", password="pass")

        response = self.client.post(self.url, {
            "action": "retirer_responsable_classe",
            "pk": responsabilite.id,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ResponsableClasseNavire.objects.filter(pk=responsabilite.id).exists())

    def test_designation_deux_fois_le_meme_marin_affiche_un_avertissement_sans_planter(self):
        ResponsableSpecialite.objects.create(specialite=self.specialite, user=self.marin)
        self.client.login(username="admin_rt", password="pass")

        response = self.client.post(self.url, {
            "action": "add_responsable_specialite",
            "specialite_id": self.specialite.id,
            "user_id": self.marin.id,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ResponsableSpecialite.objects.filter(specialite=self.specialite, user=self.marin).count(), 1)
