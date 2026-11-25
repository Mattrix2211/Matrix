"""AC-20 : une exigence locale renforce l'exigence commune, elle ne la lève jamais (contrôle sur les valeurs finales)."""
import json

from django.contrib.auth import get_user_model

from accounts.models import UserProfile
from training.models import TrainingCourse, TrainingRequirement

from matrix.tests.habilitation.outils import MondeFictif

User = get_user_model()


class ExigenceLocaleTests(MondeFictif):
    def setUp(self):
        self.cours = TrainingCourse.objects.create(title="Cours commun", validity_days=30)
        self.commune = TrainingRequirement.objects.create(course=self.cours, applies_to_role="EQUIPIER", required=True)
        self.locale = TrainingRequirement.objects.create(
            course=self.cours, applies_to_role="", applies_to_ship=self.navire, required=True)

    def _patch(self, donnees, multipart=False):
        client = self.client_de("cdt_b")
        url = f"/api/training/requirements/{self.locale.pk}/"
        if multipart:
            from django.test.client import MULTIPART_CONTENT, encode_multipart, BOUNDARY
            return client.put(url, encode_multipart(BOUNDARY, donnees), content_type=MULTIPART_CONTENT)
        return client.patch(url, data=json.dumps(donnees), content_type="application/json")

    def test_toutes_les_ecritures_de_faux_sont_refusees(self):
        for valeur in (False, "false", "FALSE", "f", "F", "n", "no", "NO", "off", "Off", "0", 0):
            self.assertEqual(self._patch({"required": valeur}).status_code, 400, valeur)
        self.locale.refresh_from_db()
        self.assertTrue(self.locale.required)

    def test_un_formulaire_sans_la_case_cochee_ne_leve_pas_l_exigence(self):
        reponse = self._patch({"course": self.cours.pk, "applies_to_ship": self.navire.pk}, multipart=True)
        self.assertEqual(reponse.status_code, 400)
        self.locale.refresh_from_db()
        self.assertTrue(self.locale.required)

    def test_une_locale_sans_role_est_comparee_a_toute_commune_du_cours(self):
        self.assertEqual(self._patch({"required": False}).status_code, 400)  # commune « EQUIPIER », locale sans rôle

    def test_sans_exigence_commune_la_locale_reste_libre(self):
        self.commune.delete()
        self.assertEqual(self._patch({"required": False}).status_code, 200)
