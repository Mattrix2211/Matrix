"""« Qualifications de l'équipe » : seuls les dossiers lisibles par l'appelant."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from dashboard.aujourdhui import qualifications_equipe
from org.models import Section, Sector, Service, Ship
from training.models import TrainingCourse, TrainingRecord


class QualificationsEquipePerimetreTests(TestCase):
    def setUp(self):
        navire = Ship.objects.create(name="Navire QE", code="QE")
        service = Service.objects.create(ship=navire, name="Service QE")
        secteur = Sector.objects.create(service=service, name="Secteur QE")
        section = Section.objects.create(sector=secteur, name="Section QE")
        self.aujourdhui = timezone.localdate()
        self.equipier = self._u("equipier_qe", "EQUIPIER", section=section)
        self.collegue = self._u("collegue_qe", "EQUIPIER", section=section)
        self.chef = self._u("chef_qe", "CHEF_SECTION", section=section)
        cours = TrainingCourse.objects.create(title="Cours QE", validity_days=365)
        TrainingRecord.objects.create(
            user=self.collegue, course=cours, completed_at=self.aujourdhui,
            expires_at=self.aujourdhui + timedelta(days=5),
        )

    def _u(self, username, role, **rattachement):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **rattachement})
        return User.objects.get(pk=user.pk)

    def test_un_equipier_ne_lit_pas_les_dossiers_de_ses_collegues(self):
        self.assertEqual(qualifications_equipe(self.equipier, self.aujourdhui), [])

    def test_le_chef_lit_les_dossiers_de_son_perimetre(self):
        self.assertEqual(len(qualifications_equipe(self.chef, self.aujourdhui)), 1)
