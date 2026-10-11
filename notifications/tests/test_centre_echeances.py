"""Centre des échéances : tâche, réponse attendue et qualification apparaissent une fois, au bon marin, et se soldent."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from dashboard.aujourdhui import a_faire, supervision
from notifications.models import Notification
from taches import services
from taches.tests.test_taches import TachesBase
from threads.utils import ajouter_commentaire
from training.models import TrainingCourse, TrainingRecord


class CentreEcheancesTests(TachesBase):
    def test_critere_de_demo(self):
        tache = self._tache(echeance=self.aujourdhui + timedelta(days=2))
        cours = TrainingCourse.objects.create(title="Lutte incendie", validity_days=365)
        TrainingRecord.objects.create(
            user=self.marin, course=cours, completed_at=self.aujourdhui - timedelta(days=350),
            expires_at=self.aujourdhui + timedelta(days=10),
        )
        ajouter_commentaire(tache, self.chef, "@marin peux-tu confirmer la pièce ?")

        titres = [e["titre"] for e in a_faire(self.marin, self.aujourdhui)]
        self.assertEqual(sorted(titres), sorted([tache.titre, "Lutte incendie", str(tache)]))
        self.assertEqual(Notification.objects.filter(user=self.marin, action_requise=True).count(), 1)
        self.assertEqual(a_faire(self.voisin, self.aujourdhui), [])

        ajouter_commentaire(tache, self.marin, "Pièce confirmée.")
        alerte = Notification.objects.get(user=self.marin, action_requise=True)
        self.assertIsNotNone(alerte.traitee_le)
        self.assertEqual(len(a_faire(self.marin, self.aujourdhui)), 2)

        services.rendre_compte(tache, self.marin, "Fait")
        self.assertEqual([e["titre"] for e in a_faire(self.marin, self.aujourdhui)], ["Lutte incendie"])
        self.assertTrue(Notification.objects.filter(user=self.marin).exists())

    def test_mention_hors_perimetre_ignoree(self):
        tache = self._tache()
        ajouter_commentaire(tache, self.marin, "@etranger regarde")
        self.assertFalse(Notification.objects.filter(user=self.etranger).exists())

    def test_le_chef_voit_les_qualifications_du_marin(self):
        cours = TrainingCourse.objects.create(title="Secourisme", validity_days=365)
        TrainingRecord.objects.create(
            user=self.marin, course=cours, completed_at=self.aujourdhui - timedelta(days=400),
            expires_at=self.aujourdhui - timedelta(days=5),
        )
        commandant = self._marin("cdt", None, "COMMANDANT", "A")
        lignes = supervision(commandant, self.aujourdhui)["qualifications"]
        self.assertEqual([l["titre"] for l in lignes], ["Secourisme"])
        self.assertTrue(lignes[0]["expiree"])

    def test_mention_repetee_une_seule_alerte(self):
        tache = self._tache()
        ajouter_commentaire(tache, self.chef, "@marin un point ?")
        ajouter_commentaire(tache, self.chef, "@marin relance")
        self.assertEqual(Notification.objects.filter(user=self.marin, action_requise=True).count(), 1)

    def test_mention_sans_acces_a_l_objet_ne_cree_pas_d_alerte(self):
        # Même secteur : le collègue est visible de l'auteur, mais la tâche privée ne lui est pas ouverte.
        collegue = self._marin("collegue", self.secteur, "EQUIPIER", "A")
        tache = self._tache(partagee=False, assigne=self.marin)
        ajouter_commentaire(tache, self.marin, "@collegue tu peux voir ?")
        self.assertFalse(Notification.objects.filter(user=collegue).exists())
