"""Le commandant en second lit comme le commandant, sans ses écritures : un test par seuil."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from matrix.core import navigation, recherche
from matrix.core.mixins import utilisateurs_visibles_par
from matrix.core.role_thresholds import seuil_role
from matrix.core.roles import NIVEAU_VISION_COMMANDEMENT, RoleLevel
from org.models import Section, Sector, Service, Ship
from quarts.models import NIVEAU_LECTURE_GLOBALE_LISTE, Quart, peut_gerer_liste, utilisateur_autorise_pour_perimetre
from quarts.web_views import _listes_visibles, _peut_lire_liste
from training.models import (
    TrainingCourse, TrainingRecord, dossiers_formation_visibles_q, peut_valider_formation,
)
from training.web_views import _peut_gerer_brh, _peut_gerer_referent_navire


class VisionCommandementBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bâtiment vision", code="VIS")
        self.service = Service.objects.create(ship=self.navire, name="Machine")
        self.secteur = Sector.objects.create(service=self.service, name="Propulsion")
        self.section = Section.objects.create(sector=self.secteur, name="Moteurs")
        self.second = self._marin("second", "COMMANDANT_EN_SECOND", ship=self.navire)
        self.commandant = self._marin("cdt", "COMMANDANT", ship=self.navire)
        self.chef = self._marin("chef", "CHEF_SERVICE", service=self.service)
        self.marin = self._marin("marin", "EQUIPIER", section=self.section)
        self.autre_navire = Ship.objects.create(name="Autre bâtiment", code="AUT")
        self.etranger = self._marin("etranger", "EQUIPIER", ship=self.autre_navire)

    def _marin(self, nom, role, **rattachement):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **rattachement})
        return User.objects.get(pk=user.pk)


class SeuilsDeLectureTests(VisionCommandementBase):
    def test_niveau_commun(self):
        self.assertEqual(NIVEAU_VISION_COMMANDEMENT, RoleLevel.COMMANDANT_EN_SECOND)
        self.assertLess(NIVEAU_LECTURE_GLOBALE_LISTE, RoleLevel.COMMANDANT)

    def test_annuaire_lecture_oui_ecriture_non(self):
        self.client.login(username="second", password="pass")
        reponse = self.client.get("/users/")
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.context["peut_gerer"])
        self.assertNotContains(reponse, 'data-bs-target="#createUserModal"')
        self.assertNotContains(reponse, 'id="bulkActionsBtn"')
        reponse = self.client.post("/users/", {"action": "bulk_delete_users", "selected_ids": [self.marin.pk]})
        self.assertEqual(reponse.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.marin.pk).exists())

    def test_annuaire_commandant_garde_l_ecriture(self):
        self.client.login(username="cdt", password="pass")
        reponse = self.client.get("/users/")
        self.assertTrue(reponse.context["peut_gerer"])
        self.assertContains(reponse, 'data-bs-target="#createUserModal"')

    def test_annuaire_ferme_au_chef_de_service(self):
        self.client.login(username="chef", password="pass")
        self.assertEqual(self.client.get("/users/").status_code, 403)

    def test_navigation_et_recherche(self):
        self.assertTrue(navigation._commandant_ou_plus(self.second))
        self.assertTrue(recherche._commandant_ou_plus(self.second))
        self.assertFalse(navigation._commandant_ou_plus(self.chef))

    def test_comptes_visibles_tout_le_navire_jamais_la_flotte(self):
        vus = set(utilisateurs_visibles_par(self.second))
        self.assertIn(self.marin, vus)
        self.assertNotIn(self.etranger, vus)
        self.assertNotIn(self.commandant, set(utilisateurs_visibles_par(self.chef)))

    def test_api_perimetre_navire(self):
        client = APIClient()
        client.force_authenticate(self.second)
        ids = {e["id"] for e in client.get("/api/accounts/users/").data}
        self.assertIn(self.marin.pk, ids)
        self.assertNotIn(self.etranger.pk, ids)
        profils = {e["id"] for e in client.get("/api/accounts/profiles/").data}
        self.assertIn(self.marin.profile.pk, profils)
        self.assertNotIn(self.etranger.profile.pk, profils)

    def test_module_gestion(self):
        self.assertEqual(seuil_role("module_gestion", self.navire.pk), RoleLevel.COMMANDANT_EN_SECOND)


class QuartsEtFormationsTests(VisionCommandementBase):
    def setUp(self):
        super().setUp()
        self.quart = Quart.objects.create(
            ship=self.navire, date_debut=timezone.localdate(), date_fin=timezone.localdate(),
        )

    def test_listes_de_quarts_lecture_oui_ecriture_non(self):
        self.assertIn(self.quart, _listes_visibles(Quart, self.second))
        self.assertTrue(_peut_lire_liste(self.second, self.quart))
        self.assertFalse(peut_gerer_liste(self.second, self.quart))
        self.assertFalse(utilisateur_autorise_pour_perimetre(self.second, ship=self.navire))
        self.assertTrue(utilisateur_autorise_pour_perimetre(self.commandant, ship=self.navire))

    def test_fiche_liste_en_lecture_seule(self):
        self.client.login(username="second", password="pass")
        reponse = self.client.get(f"/quarts/quart/{self.quart.pk}/")
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.context["peut_gerer"])

    def test_formations_listes_lecture_oui_validation_non(self):
        cours = TrainingCourse.objects.create(title="Cours vision", validity_days=365)
        dossier = TrainingRecord.objects.create(
            user=self.marin, course=cours,
            completed_at=timezone.localdate(), expires_at=timezone.localdate() + timezone.timedelta(days=30),
        )
        client = APIClient()
        client.force_authenticate(self.second)
        ids = {e["id"] for e in client.get("/api/training/records/").data}
        self.assertIn(dossier.pk, ids)
        self.assertFalse(peut_valider_formation(self.second, cours, self.navire))
        self.assertFalse(_peut_gerer_referent_navire(self.second))
        self.assertFalse(_peut_gerer_brh(self.second))
        self.assertTrue(peut_valider_formation(self.commandant, cours, self.navire))

    def test_formations_api_globale_en_lecture(self):
        TrainingCourse.objects.create(
            title="Proposition", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION", updated_by=self.chef,
        )
        client = APIClient()
        client.force_authenticate(self.second)
        titres = {e["title"] for e in client.get("/api/training/courses/").data}
        self.assertIn("Proposition", titres)

    def test_dossiers_bornes_au_navire(self):
        cours = TrainingCourse.objects.create(title="Cours étranger", validity_days=365)
        dossier = TrainingRecord.objects.create(
            user=self.etranger, course=cours,
            completed_at=timezone.localdate(), expires_at=timezone.localdate() + timezone.timedelta(days=30),
        )
        for acteur in (self.second, self.commandant):
            self.assertFalse(TrainingRecord.objects.filter(dossiers_formation_visibles_q(acteur), pk=dossier.pk).exists())
        master = self._marin("master", "MASTER_ADMIN")
        self.assertTrue(TrainingRecord.objects.filter(dossiers_formation_visibles_q(master), pk=dossier.pk).exists())
