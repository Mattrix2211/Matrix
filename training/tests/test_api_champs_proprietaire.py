"""API validations de formation : marin, formation et validateur ne se réécrivent pas."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Ship
from training.models import ReferentFormation, TrainingCourse, TrainingRecord


class ApiValidationsChampsProprietaireTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A trc", code="A-TRC")
        self.autre_navire = Ship.objects.create(name="Navire B trc", code="B-TRC")
        self.cours = TrainingCourse.objects.create(title="Cours trc", validity_days=365)
        self.autre_cours = TrainingCourse.objects.create(title="Autre cours trc", validity_days=365)
        self.marin = self._marin("marin_trc", self.navire)
        self.marin_autre_navire = self._marin("marin_b_trc", self.autre_navire)
        self.referent = self._marin("referent_trc", self.navire)
        ReferentFormation.objects.create(course=self.cours, ship=self.navire, user=self.referent)
        self.record = TrainingRecord.objects.create(
            user=self.marin, course=self.cours,
            completed_at=timezone.localdate(), expires_at=timezone.localdate() + timezone.timedelta(days=365),
        )
        self.client = APIClient()
        self.client.login(username="referent_trc", password="pass")

    def _marin(self, username, navire):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "EQUIPIER", "ship": navire})
        return user

    def _url(self):
        return f"/api/training/records/{self.record.pk}/"

    def test_referent_ne_peut_pas_reaffecter_la_validation_a_un_marin_hors_autorite(self):
        r = self.client.patch(self._url(), {"user": self.marin_autre_navire.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        self.record.refresh_from_db()
        self.assertEqual(self.record.user, self.marin)

    def test_referent_ne_peut_pas_changer_la_formation_vers_une_autre(self):
        r = self.client.patch(self._url(), {"course": self.autre_cours.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        self.record.refresh_from_db()
        self.assertEqual(self.record.course, self.cours)

    def test_validateur_non_choisi_par_l_appelant(self):
        r = self.client.post(
            "/api/training/records/",
            {"user": self.marin.pk, "course": self.cours.pk, "completed_at": str(timezone.localdate()),
             "expires_at": str(timezone.localdate() + timezone.timedelta(days=30)),
             "validated_by": self.marin_autre_navire.pk, "created_by": self.marin_autre_navire.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        enregistrement = TrainingRecord.objects.get(pk=r.data["id"])
        self.assertEqual(enregistrement.validated_by, self.referent)
        self.assertEqual(enregistrement.created_by, self.referent)

    def test_modification_legitime_toujours_possible(self):
        r = self.client.patch(self._url(), {"user": self.marin.pk, "validated_by": self.marin.pk}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.record.refresh_from_db()
        self.assertNotEqual(self.record.validated_by, self.marin)

    def test_dossier_d_un_autre_navire_invisible_pour_un_referent(self):
        autre = TrainingRecord.objects.create(
            user=self.marin_autre_navire, course=self.cours,
            completed_at=timezone.localdate(), expires_at=timezone.localdate() + timezone.timedelta(days=365),
        )
        r = self.client.get("/api/training/records/")
        ids = {e["id"] for e in r.data}
        self.assertIn(self.record.pk, ids)
        self.assertNotIn(autre.pk, ids)
        self.assertEqual(self.client.get(f"/api/training/records/{autre.pk}/").status_code, 404)


class ApiSessionsEtFormationsChampsTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A trs", code="A-TRS")
        self.autre_navire = Ship.objects.create(name="Navire B trs", code="B-TRS")
        self.cours = TrainingCourse.objects.create(title="Cours trs", validity_days=365)
        self.chef = self._marin("chef_trs", "CHEF_SECTION", self.navire)
        self.equipier = self._marin("equipier_trs", "EQUIPIER", self.navire)
        self.etranger = self._marin("etranger_trs", "EQUIPIER", self.autre_navire)
        self.client = APIClient()
        self.client.login(username="chef_trs", password="pass")

    def _marin(self, username, role, navire):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": navire})
        return user

    def _session(self, **extra):
        return {"course": self.cours.pk, "scheduled_at": timezone.now().isoformat(), **extra}

    def test_instructeur_hors_perimetre_refuse(self):
        r = self.client.post("/api/training/sessions/", self._session(instructor=self.etranger.pk), format="json")
        self.assertEqual(r.status_code, 400, r.content)

    def test_reservation_hors_perimetre_refusee(self):
        r = self.client.post("/api/training/sessions/", self._session(reservations=[self.etranger.pk]), format="json")
        self.assertEqual(r.status_code, 400, r.content)

    def test_instructeur_du_perimetre_accepte(self):
        r = self.client.post("/api/training/sessions/", self._session(instructor=self.equipier.pk), format="json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_auteur_de_la_formation_pose_par_le_serveur(self):
        r = self.client.post(
            "/api/training/courses/",
            {"title": "Nouvelle", "validity_days": 100, "created_by": self.etranger.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(TrainingCourse.objects.get(pk=r.data["id"]).created_by, self.chef)
