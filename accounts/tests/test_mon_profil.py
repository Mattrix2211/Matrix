from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from training.models import TrainingCourse, TrainingRecord


class MonProfilViewTests(TestCase):
    """« Mon profil » (/users/profil/) : fiche personnelle en lecture seule,
    enrichie de la liste des qualifications validées du marin connecté (cf.
    tâche Notion « Mon profil enrichi d'une lecture des qualifications
    validées »)."""

    def setUp(self):
        self.url = "/users/profil/"
        self.marin = User.objects.create_user(username="marin_profil", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})
        self.autre_marin = User.objects.create_user(username="autre_profil", password="pass")
        UserProfile.objects.update_or_create(user=self.autre_marin, defaults={"role": "EQUIPIER"})

    def test_anonyme_redirige_vers_connexion(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r.url)

    def test_marin_connecte_accede_a_son_profil(self):
        self.client.login(username="marin_profil", password="pass")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Mon profil")

    def test_affiche_les_qualifications_validees_du_marin_connecte(self):
        cours = TrainingCourse.objects.create(title="Sécurité incendie")
        record = TrainingRecord.objects.create(
            user=self.marin,
            course=cours,
            completed_at=timezone.localdate() - timedelta(days=100),
            expires_at=timezone.localdate() + timedelta(days=200),
        )

        self.client.login(username="marin_profil", password="pass")
        r = self.client.get(self.url)

        self.assertEqual(list(r.context["mes_qualifications"]), [record])
        self.assertContains(r, "Sécurité incendie")

    def test_isolation_un_marin_ne_voit_pas_les_qualifications_dun_autre(self):
        """Sur SON profil, un marin ne doit voir que SES propres qualifications
        (principe n°3, CLAUDE.md) — pas celles d'un autre marin."""
        cours = TrainingCourse.objects.create(title="Premiers secours")
        TrainingRecord.objects.create(
            user=self.autre_marin,
            course=cours,
            completed_at=timezone.localdate() - timedelta(days=50),
            expires_at=timezone.localdate() + timedelta(days=300),
        )

        self.client.login(username="marin_profil", password="pass")
        r = self.client.get(self.url)

        self.assertEqual(list(r.context["mes_qualifications"]), [])
        self.assertNotContains(r, "Premiers secours")

    def test_message_clair_si_aucune_qualification(self):
        self.client.login(username="marin_profil", password="pass")
        r = self.client.get(self.url)
        self.assertContains(r, "Aucune formation validée n'est actuellement enregistrée à votre nom.")

    def test_badge_qualification_a_jour(self):
        cours = TrainingCourse.objects.create(title="Formation à jour")
        TrainingRecord.objects.create(
            user=self.marin,
            course=cours,
            completed_at=timezone.localdate() - timedelta(days=10),
            expires_at=timezone.localdate() + timedelta(days=200),
        )

        self.client.login(username="marin_profil", password="pass")
        r = self.client.get(self.url)

        self.assertContains(r, "À jour")

    def test_badge_qualification_bientot_expiree(self):
        cours = TrainingCourse.objects.create(title="Formation bientôt expirée")
        TrainingRecord.objects.create(
            user=self.marin,
            course=cours,
            completed_at=timezone.localdate() - timedelta(days=300),
            expires_at=timezone.localdate() + timedelta(days=10),
        )

        self.client.login(username="marin_profil", password="pass")
        r = self.client.get(self.url)

        self.assertContains(r, "Bientôt expirée")

    def test_badge_qualification_expiree(self):
        cours = TrainingCourse.objects.create(title="Formation expirée")
        TrainingRecord.objects.create(
            user=self.marin,
            course=cours,
            completed_at=timezone.localdate() - timedelta(days=400),
            expires_at=timezone.localdate() - timedelta(days=5),
        )

        self.client.login(username="marin_profil", password="pass")
        r = self.client.get(self.url)

        self.assertContains(r, "Expirée")

    def test_affiche_le_rattachement_organisationnel_en_lecture_seule(self):
        self.marin.profile.grade = "Second maître"
        self.marin.profile.specialite = "Électrotechnicien"
        self.marin.profile.matricule = "MAT1234"
        self.marin.profile.save()

        self.client.login(username="marin_profil", password="pass")
        r = self.client.get(self.url)

        self.assertContains(r, "Second maître")
        self.assertContains(r, "Électrotechnicien")
        self.assertContains(r, "MAT1234")
        # Aucun formulaire d'édition du rattachement : la gestion reste
        # centralisée dans l'annuaire (COMMANDANT et au-dessus).
        self.assertNotContains(r, '<form method="post"')
