"""Scénarios de démonstration mer/quai : idempotents et conformes aux profils annoncés."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from quarts.activation import peut_activer_liste
from quarts.models import ChefDeListe, ServiceGarde
from django.contrib.auth.models import User


class DemoMerQuaiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo_mer_quai", stdout=StringIO())

    def test_relance_sans_doublon(self):
        avant = ServiceGarde.objects.count()
        call_command("seed_demo_mer_quai", stdout=StringIO())
        self.assertEqual(ServiceGarde.objects.count(), avant)
        self.assertEqual(ChefDeListe.objects.filter(user__username="historique_abe").count(), 1)

    def test_listes_previsionnelles_et_droits_d_activation(self):
        previsionnelles = ServiceGarde.objects.filter(application=ServiceGarde.APPLICATION_PREVISIONNELLE)
        self.assertEqual(previsionnelles.count(), 3)
        liste = previsionnelles.get(nom__contains="activation anticipée")
        self.assertTrue(peut_activer_liste(User.objects.get(username="chef_liste_abe"), liste))
        self.assertFalse(peut_activer_liste(User.objects.get(username="historique_abe"), liste))
        self.assertFalse(peut_activer_liste(User.objects.get(username="marin_abe_1"), liste))

    def test_la_designation_historique_est_a_qualifier(self):
        self.assertTrue(ChefDeListe.objects.get(user__username="historique_abe").a_qualifier)
