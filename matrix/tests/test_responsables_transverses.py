"""Tests de la désignation des responsables transverses (spécialité / classe
de navire) depuis l'onglet « Utilisateurs » des Réglages (/parametre/), tâche
Notion « Dashboards transverses par spécialité et par classe de navire ».

Gestion soumise au seuil de rôle configurable `responsabilite_transverse_gestion`
(portée GLOBALE, cf. matrix/core/role_thresholds.py) : MASTER_ADMIN par défaut
(donc réservée aux superutilisateurs Django tant qu'aucun seuil n'est abaissé),
mais un ADMIN_NAVIRE peut abaisser ce seuil pour un rôle inférieur — même
mécanisme que `referentiel_global_ecriture` (cf.
matrix/tests/test_permissions_matrix.py::test_seuil_global_referentiel_ne_depend_pas_du_navire)."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import ResponsableSpecialite, SpecialityChoice, UserProfile
from matrix.core.role_thresholds import invalidate_cache
from org.models import ResponsableClasseNavire, RoleThresholdConfig


class GestionResponsablesTransversesTests(TestCase):
    def setUp(self):
        self.url = reverse("settings")
        self.specialite = SpecialityChoice.objects.create(name="Électricité")
        self.marin = User.objects.create_user(username="marin_elec", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})
        self.admin = User.objects.create_superuser(username="admin_rt", password="pass", email="a@a.fr")

    def test_utilisateur_role_insuffisant_refuse_par_defaut_sans_seuil_abaisse(self):
        """Sans configuration explicite, le seuil `responsabilite_transverse_gestion`
        vaut MASTER_ADMIN par défaut : un COMMANDANT reste donc refusé — aucune
        RoleThresholdConfig n'est créée dans ce test."""
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

    def test_seuil_abaisse_autorise_le_role_configure_et_bloque_les_roles_inferieurs(self):
        """Une fois `responsabilite_transverse_gestion` abaissé à COMMANDANT (portée
        GLOBALE, ship=None — même mécanisme que `referentiel_global_ecriture`), un
        COMMANDANT peut désigner ET retirer un responsable, alors qu'un rôle
        inférieur (CHEF_SERVICE) reste bloqué."""
        commandant = User.objects.create_user(username="commandant_rt", password="pass")
        UserProfile.objects.update_or_create(user=commandant, defaults={"role": "COMMANDANT"})
        chef_service = User.objects.create_user(username="chef_service_rt", password="pass")
        UserProfile.objects.update_or_create(user=chef_service, defaults={"role": "CHEF_SERVICE"})

        RoleThresholdConfig.objects.create(
            ship=None, thresholds={"responsabilite_transverse_gestion": "COMMANDANT"},
        )
        invalidate_cache(None)
        # Le cache des seuils (django.core.cache) n'est pas un état de base de
        # données : il n'est donc pas réinitialisé automatiquement entre les
        # tests par le rollback de transaction de TestCase. On l'invalide
        # explicitement en fin de test pour ne pas polluer les tests suivants.
        self.addCleanup(invalidate_cache, None)

        # Un CHEF_SERVICE (rôle inférieur au seuil configuré) reste refusé.
        self.client.login(username="chef_service_rt", password="pass")
        response = self.client.post(self.url, {
            "action": "add_responsable_specialite",
            "specialite_id": self.specialite.id,
            "user_id": self.marin.id,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ResponsableSpecialite.objects.exists())
        self.client.logout()

        # Le COMMANDANT, désormais au niveau du seuil configuré, peut désigner...
        self.client.login(username="commandant_rt", password="pass")
        response = self.client.post(self.url, {
            "action": "add_responsable_specialite",
            "specialite_id": self.specialite.id,
            "user_id": self.marin.id,
        })
        self.assertEqual(response.status_code, 302)
        responsabilite = ResponsableSpecialite.objects.get(specialite=self.specialite, user=self.marin)

        # ... et retirer ce même responsable.
        response = self.client.post(self.url, {
            "action": "retirer_responsable_specialite",
            "pk": responsabilite.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ResponsableSpecialite.objects.filter(pk=responsabilite.id).exists())

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
