"""Annonce -> tâche : création pré-remplie, lien des deux côtés, confidentialité des tâches liées."""
from types import SimpleNamespace

from django.urls import reverse

from accounts.models import AuditLog
from annonces import services
from annonces.tests.test_annonces import AnnoncesBase
from notifications.liens import liens_accessibles
from notifications.models import Notification
from taches.models import Tache


class AnnonceTacheTests(AnnoncesBase):
    def setUp(self):
        super().setUp()
        self.marin2 = self._marin("marin2", self.energie, self.propulsion, "EQUIPIER")
        self.annonce = services.publier(self.chef_energie, "Rangement du local", "Avant jeudi", "info", f"service:{self.energie.pk}")

    def _creer(self, user, assigne, **extra):
        self.client.force_login(user)
        return self.client.post(reverse("taches-index"), {
            "titre": "Ranger", "assigne": assigne.pk, "annonce": self.annonce.pk, **extra})

    def test_formulaire_prerempli_pour_le_publieur(self):
        self.client.force_login(self.chef_energie)
        r = self.client.get(reverse("taches-index"), {"annonce": self.annonce.pk})
        self.assertEqual(r.context["annonce_source"], self.annonce)
        self.assertContains(r, 'value="Rangement du local"')
        self.assertContains(r, "Voir l'annonce")
        detail = self.client.get(reverse("annonce-detail", args=[self.annonce.pk]))
        self.assertContains(detail, "Créer une tâche à partir de cette annonce")

    def test_identifiant_annonce_non_ascii_ignore_sans_erreur(self):
        self.client.force_login(self.chef_energie)
        r = self.client.get(reverse("taches-index"), {"annonce": "\u00b2"})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["annonce_source"])

    def test_bouton_et_prerempli_absents_sans_droit_d_attribution(self):
        self.client.force_login(self.marin)
        self.assertNotContains(self.client.get(reverse("annonce-detail", args=[self.annonce.pk])), "Créer une tâche")
        r = self.client.get(reverse("taches-index"), {"annonce": self.annonce.pk})
        self.assertIsNone(r.context["annonce_source"])
        self._creer(self.marin, self.marin)
        self.assertFalse(Tache.objects.exists())

    def test_annonce_non_consultable_refusee(self):
        autre = services.publier(self.cdt, "Pont seul", "x", "info", f"service:{self.pont.pk}")
        self.client.force_login(self.chef_energie)
        self.client.post(reverse("taches-index"), {"titre": "x", "assigne": self.marin.pk, "annonce": autre.pk})
        self.assertFalse(Tache.objects.exists())

    def test_creation_lie_la_tache_trace_et_notifie(self):
        r = self._creer(self.chef_energie, self.marin)
        tache = Tache.objects.get()
        self.assertRedirects(r, reverse("tache-detail", args=[tache.pk]))
        self.assertEqual(tache.annonce, self.annonce)
        self.assertIn(f"annonce={self.annonce.pk}", AuditLog.objects.get(action="tache_creation").details)
        notif = Notification.objects.get(user=self.marin, verb__contains="attribué la tâche")
        self.assertIn(reverse("tache-detail", args=[tache.pk]), liens_accessibles(SimpleNamespace(user=self.marin), [notif]).values())
        # Lien des deux côtés.
        self.assertContains(self.client.get(reverse("tache-detail", args=[tache.pk])), "Issue de l'annonce")
        self.assertContains(self.client.get(reverse("annonce-detail", args=[self.annonce.pk])), "Tâches liées")

    def test_destinataire_ne_voit_que_ses_taches_liees(self):
        self._creer(self.chef_energie, self.marin)
        self._creer(self.chef_energie, self.marin2)
        self.client.force_login(self.marin)
        r = self.client.get(reverse("annonce-detail", args=[self.annonce.pk]))
        self.assertEqual([t.assigne for t in r.context["taches_liees"]], [self.marin])
        self.client.force_login(self.chef_energie)
        r = self.client.get(reverse("annonce-detail", args=[self.annonce.pk]))
        self.assertEqual(len(r.context["taches_liees"]), 2)

    def test_equipage_a_terre_ne_cree_pas(self):
        profil = self.chef_energie.profile
        profil.equipage = "B"
        profil.save()
        self.navire.double_equipage, self.navire.equipage_a_bord = True, "A"
        self.navire.save()
        self._creer(self.chef_energie, self.marin)
        self.assertFalse(Tache.objects.exists())
