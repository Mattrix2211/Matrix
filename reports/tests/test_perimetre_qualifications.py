"""Les bilans ne listent que les qualifications que l'appelant a le droit de lire."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Service, Ship
from reports.services import construire_contexte_instantane, construire_contexte_periode
from training.models import TrainingCourse, TrainingRecord


class QualificationsBilanPerimetreTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire QB", code="QB")
        self.machine = Service.objects.create(ship=self.navire, name="Machine", commandant_adjoint="COMAEQ")
        self.pont = Service.objects.create(ship=self.navire, name="Pont", commandant_adjoint="COMANAV")
        self.comaeq = self._u("comaeq_qb", "ETAT_MAJOR", ship=self.navire, fonction_coma="COMAEQ")
        self._u("comanav_qb", "ETAT_MAJOR", ship=self.navire, fonction_coma="COMANAV")
        self.marin_machine = self._u("marin_machine_qb", "EQUIPIER", ship=self.navire, service=self.machine)
        self.marin_pont = self._u("marin_pont_qb", "EQUIPIER", ship=self.navire, service=self.pont)
        cours = TrainingCourse.objects.create(title="Cours QB", validity_days=365)
        self.aujourdhui = timezone.localdate()
        for marin in (self.marin_machine, self.marin_pont):
            TrainingRecord.objects.create(
                user=marin, course=cours, completed_at=self.aujourdhui,
                expires_at=self.aujourdhui + timedelta(days=10),
            )

    def _u(self, username, role, **rattachement):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **rattachement})
        return User.objects.get(pk=user.pk)

    def _marins(self, qualifications):
        return {q.user_id for q in qualifications}

    def test_instantane_exclut_les_services_d_un_autre_coma(self):
        contexte = construire_contexte_instantane("ship", self.navire.id, self.comaeq)
        self.assertEqual(
            self._marins(contexte["qualifications_proches_expiration"]), {self.marin_machine.id}
        )

    def test_periode_exclut_les_services_d_un_autre_coma(self):
        contexte = construire_contexte_periode(
            "ship", self.navire.id, self.comaeq,
            self.aujourdhui - timedelta(days=1), self.aujourdhui + timedelta(days=30),
        )
        self.assertEqual(self._marins(contexte["qualifications_obtenues"]), {self.marin_machine.id})
        self.assertEqual(self._marins(contexte["qualifications_expirees"]), {self.marin_machine.id})
