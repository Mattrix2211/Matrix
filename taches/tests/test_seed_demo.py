from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from taches.models import Tache


class SeedDemoTachesTests(TestCase):
    def test_jeu_de_donnees_idempotent_et_complet(self):
        for _ in range(2):
            call_command("seed_demo", stdout=StringIO())
        statuts = sorted(Tache.objects.values_list("statut", flat=True))
        self.assertEqual(statuts, [Tache.STATUT_A_FAIRE, Tache.STATUT_BLOQUEE, Tache.STATUT_TERMINEE])
        bloquee = Tache.objects.get(statut=Tache.STATUT_BLOQUEE)
        self.assertEqual(bloquee.participants.get().username, "chef_secteur_b")
