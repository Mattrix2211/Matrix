from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from taches.models import Tache


class SeedDemoTachesTests(TestCase):
    def test_jeu_de_donnees_idempotent_et_complet(self):
        for _ in range(2):
            call_command("seed_demo", stdout=StringIO())
        statuts = sorted(Tache.objects.values_list("statut", flat=True))
        self.assertEqual(statuts, [Tache.STATUT_A_FAIRE] * 3 + [Tache.STATUT_BLOQUEE, Tache.STATUT_TERMINEE])
        bloquee = Tache.objects.get(statut=Tache.STATUT_BLOQUEE)
        self.assertEqual(bloquee.participants.get().username, "chef_secteur_b")

    def test_demande_et_annonce_de_demo(self):
        from annonces.models import Annonce
        from demandes.models import Demande

        for _ in range(2):
            call_command("seed_demo", stdout=StringIO())
        demande = Demande.objects.get()
        self.assertEqual((demande.etat, demande.interlocuteurs.get().username), (Demande.ETAT_EN_TRAITEMENT, "chef_secteur_b"))
        annonce = Annonce.objects.get()
        self.assertTrue(annonce.accuse_requis)
