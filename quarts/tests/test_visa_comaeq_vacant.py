"""Visa exceptionnel du commandant quand le poste de COMAEQ est vacant (règle propre à la feuille de service)."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from org.models import Ship
from quarts.models import FeuilleService, peut_viser_comaeq


def _marin(username, role, ship, equipage="", fonction_coma=""):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(
        user=user, defaults={"role": role, "ship": ship, "equipage": equipage, "fonction_coma": fonction_coma}
    )
    return User.objects.get(pk=user.pk)


class VisaComaeqVacantTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(
            name="FREMM Vacant", code="FVA", classe_navire="FREMM", double_equipage=True, equipage_a_bord="A",
        )
        self.autre_ship = Ship.objects.create(name="Autre", code="AUT")
        self.cdt_a = _marin("cdt_a", "COMMANDANT", self.ship, "A")
        self.cdt_b = _marin("cdt_b", "COMMANDANT", self.ship, "B")
        self.second_a = _marin("second_a", "COMMANDANT_EN_SECOND", self.ship, "A")
        self.cdt_autre = _marin("cdt_autre", "COMMANDANT", self.autre_ship)
        self.admin = _marin("admin", "ADMIN_UNITE", self.ship, "A")
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, equipage="A", date=timezone.localdate(), statut=FeuilleService.STATUT_VISA_COMAEQ,
        )

    def _poste_pourvu(self, equipage="A"):
        return _marin(f"comaeq_{equipage}", "ETAT_MAJOR", self.ship, equipage, "COMAEQ")

    def test_titulaire_present_lui_seul_vise_sans_escalade(self):
        comaeq = self._poste_pourvu()
        self.assertTrue(peut_viser_comaeq(comaeq, self.feuille))
        for autre in (self.cdt_a, self.second_a, self.admin):
            self.assertFalse(peut_viser_comaeq(autre, self.feuille))
        self.feuille._notifier_prochain_visa()
        self.assertFalse(AuditLog.objects.filter(action="feuille_service_comaeq_vacant").exists())

    def test_titulaire_absent_mais_en_poste_n_ouvre_pas_l_exception(self):
        # L'absence temporaire n'est pas une vacance : le titulaire reste configuré.
        self._poste_pourvu()
        self.assertFalse(peut_viser_comaeq(self.cdt_a, self.feuille))

    def test_poste_vacant_le_commandant_de_l_equipage_vise(self):
        self.assertTrue(peut_viser_comaeq(self.cdt_a, self.feuille))

    def test_poste_vacant_refuse_second_admin_autre_equipage_autre_batiment(self):
        for refuse in (self.second_a, self.admin, self.cdt_b, self.cdt_autre):
            self.assertFalse(peut_viser_comaeq(refuse, self.feuille), refuse.username)

    def test_titulaire_dans_l_autre_equipage_ne_comble_pas_la_vacance(self):
        self._poste_pourvu("B")
        self.assertTrue(peut_viser_comaeq(self.cdt_a, self.feuille))

    def test_commandant_de_l_equipage_a_terre_vise_sa_propre_feuille_vacante(self):
        feuille_b = FeuilleService.objects.create(
            ship=self.ship, equipage="B", date=timezone.localdate(), statut=FeuilleService.STATUT_VISA_COMAEQ,
        )
        self.assertTrue(peut_viser_comaeq(self.cdt_b, feuille_b))
        self.assertFalse(peut_viser_comaeq(self.cdt_a, feuille_b))

    def test_visa_exceptionnel_trace_et_marque_dans_l_historique(self):
        self.feuille.viser_comaeq(self.cdt_a)
        self.assertTrue(AuditLog.objects.filter(
            action="feuille_service_visa_comaeq_exceptionnel", actor=self.cdt_a
        ).exists())
        self.assertFalse(AuditLog.objects.filter(action="feuille_service_visa_comaeq").exists())
        self.assertTrue(self.feuille.versions.get().contenu_fige["visa_exceptionnel"])

    def test_visa_du_titulaire_n_est_pas_exceptionnel(self):
        comaeq = self._poste_pourvu()
        self.feuille.viser_comaeq(comaeq)
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_visa_comaeq").exists())
        self.assertFalse(self.feuille.versions.get().contenu_fige["visa_exceptionnel"])

    def test_interface_signale_l_absence_de_titulaire_et_l_exception(self):
        self.client.force_login(self.cdt_a)
        url = reverse("feuille-service-detail", args=[self.ship.pk, f"{self.feuille.date:%Y-%m-%d}"])
        reponse = self.client.get(url)
        self.assertContains(reponse, "Aucun titulaire COMAEQ")
        self.assertContains(reponse, "relève exceptionnellement du commandant")
        self.assertContains(reponse, "Viser et publier (COMAEQ)")

    def test_post_du_second_refuse_et_commandant_publie(self):
        url = reverse("feuille-service-detail", args=[self.ship.pk, f"{self.feuille.date:%Y-%m-%d}"])
        self.client.force_login(self.second_a)
        self.assertEqual(self.client.post(url, {"action": "viser_comaeq"}).status_code, 403)
        self.client.force_login(self.cdt_a)
        self.client.post(url, {"action": "viser_comaeq"})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_PUBLIEE)
