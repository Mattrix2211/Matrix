"""Liste des occurrences : colonne de synthèse bornée au périmètre, indépendante des filtres de la liste."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from maintenance.models import MaintenanceOccurrence
from maintenance.tests.test_fiche_imprimable import _navire


class SyntheseListeTests(TestCase):
    def setUp(self):
        self.sector_a, self.occ_a = _navire("SA")
        self.sector_b, self.occ_b = _navire("SB")
        user = User.objects.create_user(username="chef_synthese", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "CHEF_SERVICE", "sector": self.sector_a})
        self.user = User.objects.get(pk=user.pk)
        self.client.login(username="chef_synthese", password="pass")

    def _synthese(self, **params):
        return self.client.get(reverse("maintenance-occurrences"), params).context["synthese"]

    def test_retards_comptes_dans_le_perimetre_seulement(self):
        hier = timezone.localdate() - timedelta(days=3)
        MaintenanceOccurrence.objects.filter(pk=self.occ_a.pk).update(scheduled_for=hier)
        MaintenanceOccurrence.objects.filter(pk=self.occ_b.pk).update(scheduled_for=hier)
        self.assertEqual(self._synthese()["en_retard"], 1)

    def test_la_synthese_ignore_les_filtres_de_la_liste(self):
        MaintenanceOccurrence.objects.filter(pk=self.occ_a.pk).update(status="WAITING_VALIDATION")
        sans_filtre = self._synthese()
        avec_filtre = self._synthese(statut="DONE")
        self.assertEqual(sans_filtre, avec_filtre)
        self.assertEqual(sans_filtre["a_valider"], 1)

    def test_assignation_reflete_dans_les_chiffres(self):
        self.assertEqual(self._synthese()["non_assignees"], 1)
        self.occ_a.assignees.add(self.user)
        synthese = self._synthese()
        self.assertEqual((synthese["non_assignees"], synthese["miennes"]), (0, 1))

    def test_colonne_et_impression_de_ligne_visibles(self):
        page = self.client.get(reverse("maintenance-occurrences"))
        self.assertContains(page, "À traiter")
        self.assertContains(page, "mx-table-cartes")
        self.assertContains(page, 'aria-label="Imprimer la fiche')
