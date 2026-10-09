"""Lecture des dossiers de formation (TrainingRecord) : soi-même, chefs directs
en remontant la hiérarchie, Personnel BRH du navire, référents ; jamais les
autres marins du bord."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Section, Sector, Service, Ship
from training.models import PersonnelBRH, TrainingCourse, TrainingRecord


class LectureDossiersFormationTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire lecture", code="LEC")
        self.service = Service.objects.create(ship=self.navire, name="Service machine")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur propulsion")
        self.section = Section.objects.create(sector=self.secteur, name="Section moteurs")
        self.autre_service = Service.objects.create(ship=self.navire, name="Service pont")
        self.autre_secteur = Sector.objects.create(service=self.autre_service, name="Secteur manoeuvre")
        self.autre_section = Section.objects.create(sector=self.autre_secteur, name="Section amarrage")
        self.cours = TrainingCourse.objects.create(title="Cours lecture", validity_days=365)

        self.marin = self._marin("marin_lec", "EQUIPIER", section=self.section)
        self.collegue = self._marin("collegue_lec", "EQUIPIER", section=self.autre_section)
        self.collegue_meme_section = self._marin("collegue_section_lec", "EQUIPIER", section=self.section)
        self.chef_section = self._marin("chef_section_lec", "CHEF_SECTION", section=self.section)
        self.chef_secteur = self._marin("chef_secteur_lec", "CHEF_SECTEUR", sector=self.secteur)
        self.chef_service = self._marin("chef_service_lec", "CHEF_SERVICE", service=self.service)
        self.etat_major = self._marin("etat_major_lec", "ETAT_MAJOR", ship=self.navire)
        self.chef_autre_branche = self._marin("chef_autre_lec", "CHEF_SECTEUR", sector=self.autre_secteur)
        self.brh = self._marin("brh_lec", "EQUIPIER", section=self.autre_section)
        PersonnelBRH.objects.create(ship=self.navire, user=self.brh)
        self.sans_perimetre = self._marin("sans_perimetre_lec", "CHEF_SERVICE")
        self.master = self._marin("master_lec", "MASTER_ADMIN")

        self.dossier = TrainingRecord.objects.create(
            user=self.marin, course=self.cours,
            completed_at=timezone.localdate(), expires_at=timezone.localdate() + timezone.timedelta(days=365),
        )

    def _marin(self, username, role, **rattachement):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **rattachement})
        return user

    def _ids_vus_par(self, user):
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=user.pk))
        return {e["id"] for e in client.get("/api/training/records/").data}

    def test_soi_meme(self):
        self.assertIn(self.dossier.pk, self._ids_vus_par(self.marin))

    def test_chefs_directs_en_remontant(self):
        for chef in (self.chef_section, self.chef_secteur, self.chef_service, self.etat_major):
            self.assertIn(self.dossier.pk, self._ids_vus_par(chef), chef.username)

    def test_personnel_brh(self):
        self.assertIn(self.dossier.pk, self._ids_vus_par(self.brh))

    def test_master_admin_voit_tout(self):
        self.assertIn(self.dossier.pk, self._ids_vus_par(self.master))

    def test_autre_specialite_meme_rang_refuse(self):
        self.assertNotIn(self.dossier.pk, self._ids_vus_par(self.collegue))

    def test_collegue_de_meme_section_refuse(self):
        self.assertNotIn(self.dossier.pk, self._ids_vus_par(self.collegue_meme_section))

    def test_chef_d_une_autre_branche_refuse(self):
        self.assertNotIn(self.dossier.pk, self._ids_vus_par(self.chef_autre_branche))

    def test_perimetre_vide_ne_voit_rien(self):
        self.assertEqual(self._ids_vus_par(self.sans_perimetre), set())

    def test_detail_d_un_collegue_introuvable(self):
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=self.collegue.pk))
        self.assertEqual(client.get(f"/api/training/records/{self.dossier.pk}/").status_code, 404)

    def test_catalogue_web_ne_montre_pas_les_validations_des_autres(self):
        self.client.login(username="collegue_lec", password="pass")
        r = self.client.get("/formations/")
        self.assertEqual(r.status_code, 200)
        formation = next(f for f in r.context["formations"] if f.pk == self.cours.pk)
        self.assertEqual(formation.nb_a_jour, 0)
        self.assertEqual(formation.dernieres_validations, [])
