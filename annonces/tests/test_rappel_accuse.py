"""Rappel unique d'accusé de réception des annonces."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from annonces import services
from annonces.models import Annonce, ParametresAnnonces
from annonces.tasks import rappeler_accuses_annonces
from notifications.models import Notification

from .test_annonces import AnnoncesBase


class RappelAccuseTests(AnnoncesBase):
    def setUp(self):
        super().setUp()
        self.annonce = services.publier(
            self.chef_energie, "Consigne", "Lire", "info", f"service:{self.energie.pk}", accuse_requis=True)
        self._vieillir(self.annonce)

    def _vieillir(self, annonce, jours=3):
        Annonce.objects.filter(pk=annonce.pk).update(diffusee_le=timezone.now() - timedelta(days=jours))

    def _rappels(self, user=None):
        qs = Notification.objects.filter(verb__startswith=services.PREFIXE_RAPPEL)
        return qs.filter(user=user) if user else qs

    def test_rappel_unique_meme_apres_deux_executions(self):
        self.assertEqual(rappeler_accuses_annonces()["rappels"], 1)
        self.assertEqual(rappeler_accuses_annonces()["rappels"], 0)
        rappel = self._rappels(self.marin).get()
        self.assertTrue(rappel.action_requise)
        self.assertEqual(rappel.target, self.annonce)
        self.assertFalse(self._rappels(self.chef_energie).exists())  # l'auteur n'est jamais relancé

    def test_pas_de_rappel_si_accuse_fait(self):
        services.accuser(self.marin, self.annonce)
        self.assertEqual(services.rappeler_accuses(), 0)

    def test_accuse_solde_le_rappel(self):
        services.rappeler_accuses()
        services.accuser(self.marin, self.annonce)
        self.assertIsNotNone(self._rappels(self.marin).get().traitee_le)

    def test_pas_de_rappel_avant_le_delai(self):
        self._vieillir(self.annonce, 1)
        self.assertEqual(services.rappeler_accuses(), 0)

    def test_pas_de_rappel_si_delai_nul(self):
        ParametresAnnonces.objects.create(jours_rappel_accuse=0)
        self.assertEqual(services.rappeler_accuses(), 0)

    def test_delai_reglable(self):
        ParametresAnnonces.objects.create(jours_rappel_accuse=5)
        self.assertEqual(services.rappeler_accuses(), 0)
        self._vieillir(self.annonce, 5)
        self.assertEqual(services.rappeler_accuses(), 1)

    def test_pas_de_rappel_si_expiree_archivee_ou_sans_accuse(self):
        Annonce.objects.filter(pk=self.annonce.pk).update(date_fin=self.jour - timedelta(days=1))
        self.assertEqual(services.rappeler_accuses(), 0)
        Annonce.objects.filter(pk=self.annonce.pk).update(date_fin=None, archivee=True)
        self.assertEqual(services.rappeler_accuses(), 0)
        Annonce.objects.filter(pk=self.annonce.pk).update(archivee=False, accuse_requis=False)
        self.assertEqual(services.rappeler_accuses(), 0)

    def test_perimetre_des_destinataires(self):
        services.rappeler_accuses()
        for exclu in (self.matelot_pont, self.etranger):
            self.assertFalse(self._rappels(exclu).exists())

    def test_annonce_non_encore_diffusee_ignoree(self):
        futur = services.publier(self.cdt, "Plus tard", "x", "info", f"ship:{self.navire.pk}",
                                 accuse_requis=True, date_effet=self.jour + timedelta(days=1))
        services.rappeler_accuses()
        self.assertFalse(self._rappels().filter(object_id=str(futur.pk)).exists())

    def test_notification_de_diffusion_inchangee(self):
        diffusion = Notification.objects.get(user=self.marin, verb__startswith="Annonce")
        self.assertTrue(diffusion.action_requise)
        services.rappeler_accuses()
        diffusion.refresh_from_db()
        self.assertIsNone(diffusion.traitee_le)


class ReglageRappelTests(AnnoncesBase):
    def _poster(self, jours):
        return self.client.post(reverse("settings"), {"action": "update_parametres_annonces", "jours_rappel_accuse": jours})

    def test_reglage_reserve_au_maitre_admin(self):
        self.client.login(username="cdt", password="pass")
        self._poster("4")
        self.assertFalse(ParametresAnnonces.objects.exists())

    def test_modification_validee_et_tracee(self):
        User.objects.create_superuser("root", password="pass")
        self.client.login(username="root", password="pass")
        self._poster("4")
        self.assertEqual(ParametresAnnonces.objects.get().jours_rappel_accuse, 4)
        self.assertTrue(AuditLog.objects.filter(action="update_parametres_annonces", details__contains="2 -> 4").exists())
        for invalide in ("abc", "-1", "400"):
            self._poster(invalide)
        self.assertEqual(ParametresAnnonces.objects.get().jours_rappel_accuse, 4)
        self.assertContains(self.client.get(reverse("settings"), {"tab": "seuils_role"}), "Jours avant le rappel")
