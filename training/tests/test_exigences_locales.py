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


class CoherenceIndependanteDeL_ordreTests(MondeFictif):
    """AC-20 : l'invariant tient quel que soit l'ordre des opérations et l'interface (modèle, API, administration)."""

    def setUp(self):
        self.general = User.objects.create_user(username="general_ordre", password="pass")
        UserProfile.objects.filter(user=self.general).update(administrateur_general=True)
        self.cours = TrainingCourse.objects.create(title="Cours ordre", validity_days=30)

    def _api(self, nom, methode, url, donnees):
        return getattr(self.client_de(nom), methode)(url, data=json.dumps(donnees), content_type="application/json")

    def test_la_commune_devenue_obligatoire_releve_les_locales_facultatives_avec_trace(self):
        from accounts.models import AuditLog
        locale = TrainingRequirement.objects.create(course=self.cours, applies_to_role="EQUIPIER", applies_to_ship=self.navire, required=False)
        ailleurs = TrainingRequirement.objects.create(course=self.cours, applies_to_role="CHEF_SERVICE", applies_to_ship=self.navire, required=False)
        commune = self._api("general_ordre", "post", "/api/training/requirements/",
                            {"course": self.cours.pk, "applies_to_role": "EQUIPIER", "required": False})
        self.assertEqual(commune.status_code, 201)
        pk = commune.json()["id"]
        self.assertEqual(self._api("general_ordre", "patch", f"/api/training/requirements/{pk}/", {"required": True}).status_code, 200)
        locale.refresh_from_db()
        ailleurs.refresh_from_db()
        self.assertTrue(locale.required)
        self.assertFalse(ailleurs.required)  # rôle sans rapport : inchangée
        self.assertTrue(AuditLog.objects.filter(action="exigence_locale_renforcee", details__contains=f"exigence={locale.pk}").exists())

    def test_creation_d_une_commune_obligatoire_apres_la_locale_facultative(self):
        locale = TrainingRequirement.objects.create(course=self.cours, applies_to_role="", applies_to_ship=self.navire, required=False)
        TrainingRequirement.objects.create(course=self.cours, applies_to_role="EQUIPIER", required=True)
        locale.refresh_from_db()
        self.assertTrue(locale.required)

    def test_changement_de_perimetre_ou_de_role_d_une_exigence(self):
        TrainingRequirement.objects.create(course=self.cours, applies_to_role="EQUIPIER", required=True)
        locale = TrainingRequirement.objects.create(course=self.cours, applies_to_role="CHEF_SERVICE", applies_to_ship=self.navire, required=False)
        url = f"/api/training/requirements/{locale.pk}/"
        self.assertEqual(self._api("cdt_b", "patch", url, {"applies_to_role": "EQUIPIER"}).status_code, 400)  # rôle recoupé
        self.assertEqual(self._api("cdt_b", "patch", url, {"applies_to_role": ""}).status_code, 400)
        autre = TrainingCourse.objects.create(title="Autre cours", validity_days=30)
        self.assertEqual(self._api("cdt_b", "patch", url, {"course": autre.pk}).status_code, 200)  # aucun recoupement
        # Une commune ne devient pas locale facultative si une autre commune obligatoire la couvre, mais le peut si elle est seule.
        seule = TrainingRequirement.objects.create(course=autre, applies_to_role="EQUIPIER", required=True)
        seule_url = f"/api/training/requirements/{seule.pk}/"
        self.assertEqual(self._api("general_ordre", "patch", seule_url,
                                   {"applies_to_ship": self.navire.pk, "required": False}).status_code, 200)

    def test_le_modele_refuse_l_affaiblissement_pour_toute_interface(self):
        from django.core.exceptions import ValidationError
        TrainingRequirement.objects.create(course=self.cours, applies_to_role="EQUIPIER", required=True)
        faible = TrainingRequirement(course=self.cours, applies_to_role="EQUIPIER", applies_to_ship=self.navire, required=False)
        with self.assertRaises(ValidationError):
            faible.full_clean()  # administration Django, formulaires
        with self.assertRaises(ValidationError):
            faible.save()  # ORM, commandes de gestion
        self.assertFalse(TrainingRequirement.objects.filter(applies_to_ship=self.navire).exists())
        TrainingRequirement(course=self.cours, applies_to_role="EQUIPIER", applies_to_ship=self.navire, required=True).save()
