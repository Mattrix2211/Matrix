"""Lien service -> commandant adjoint (COMAEQ, COMOPS, COMANAV, COMAVIA) et routage des visas."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.forms import UserProfileForm
from accounts.models import RoleAvailability, UserProfile
from matrix.core.commandants_adjoints import (
    commandant_adjoint_du_service, est_commandant_adjoint_du_service, service_de, titulaires_commandant_adjoint,
)
from org.models import Section, Sector, Service, Ship
from training.models import TrainingCourse, TrainingRecord, dossiers_formation_visibles_q
from training.web_views import peut_valider_proposition_bord


class CommandantsAdjointsBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Frégate", code="FRG")
        self.machine = Service.objects.create(ship=self.navire, name="Machine", commandant_adjoint="COMAEQ")
        self.pont = Service.objects.create(ship=self.navire, name="Pont", commandant_adjoint="COMANAV")
        self.libre = Service.objects.create(ship=self.navire, name="Divers")
        self.secteur = Sector.objects.create(service=self.machine, name="Propulsion")
        self.section = Section.objects.create(sector=self.secteur, name="Moteurs")
        self.secteur_pont = Sector.objects.create(service=self.pont, name="Manoeuvre")
        self.secteur_libre = Sector.objects.create(service=self.libre, name="Divers secteur")
        self.comaeq = self._marin("comaeq", "ETAT_MAJOR", ship=self.navire, fonction_coma="COMAEQ")
        self.comanav = self._marin("comanav", "ETAT_MAJOR", ship=self.navire, fonction_coma="COMANAV")
        self.em_simple = self._marin("em", "ETAT_MAJOR", ship=self.navire)

    def _marin(self, nom, role, **rattachement):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **rattachement})
        return User.objects.get(pk=user.pk)


class TitulairesTests(CommandantsAdjointsBase):
    def test_service_de_remonte_la_hierarchie(self):
        marin = self._marin("marin", "EQUIPIER", section=self.section)
        self.assertEqual(service_de(marin), self.machine)
        self.assertIsNone(service_de(self._marin("sans", "EQUIPIER", ship=self.navire)))

    def test_commandant_adjoint_du_service(self):
        self.assertEqual(commandant_adjoint_du_service(self.machine), "COMAEQ")
        self.assertEqual(commandant_adjoint_du_service(self.libre), "")
        self.assertEqual(commandant_adjoint_du_service(None), "")

    def test_titulaires_seulement_le_code_demande_et_actifs(self):
        self.assertEqual(list(titulaires_commandant_adjoint(self.navire, "COMAEQ")), [self.comaeq])
        self.assertFalse(titulaires_commandant_adjoint(self.navire, "COMOPS").exists())
        self.assertFalse(titulaires_commandant_adjoint(self.navire, "").exists())
        User.objects.filter(pk=self.comaeq.pk).update(is_active=False)
        self.assertFalse(titulaires_commandant_adjoint(self.navire, "COMAEQ").exists())

    def test_titulaire_d_un_autre_batiment_exclu(self):
        autre = Ship.objects.create(name="Autre", code="AUT")
        self._marin("comaeq_autre", "ETAT_MAJOR", ship=autre, fonction_coma="COMAEQ")
        self.assertEqual(list(titulaires_commandant_adjoint(self.navire, "COMAEQ")), [self.comaeq])

    def test_double_equipage_titulaire_de_l_equipage_concerne(self):
        Ship.objects.filter(pk=self.navire.pk).update(double_equipage=True, equipage_a_bord="A")
        self.navire.refresh_from_db()
        UserProfile.objects.filter(user=self.comaeq).update(equipage="A")
        comaeq_b = self._marin("comaeq_b", "ETAT_MAJOR", ship=self.navire, fonction_coma="COMAEQ", equipage="B")
        self.assertEqual(list(titulaires_commandant_adjoint(self.navire, "COMAEQ", "B")), [comaeq_b])
        self.assertEqual(list(titulaires_commandant_adjoint(self.navire, "COMAEQ")), [self.comaeq])
        self.assertTrue(est_commandant_adjoint_du_service(comaeq_b, self.machine, "B"))
        self.assertFalse(est_commandant_adjoint_du_service(comaeq_b, self.machine, "A"))

    def test_champ_service_non_modifiable_par_l_api(self):
        admin = self._marin("adm", "ADMIN_NAVIRE", ship=self.navire)
        client = APIClient()
        client.force_authenticate(admin)
        client.patch(f"/api/org/services/{self.libre.pk}/", {"commandant_adjoint": "COMOPS"}, format="json")
        self.libre.refresh_from_db()
        self.assertEqual(self.libre.commandant_adjoint, "")


class FormulaireProfilTests(TestCase):
    def test_role_sans_ligne_de_disponibilite_est_actif(self):
        RoleAvailability.objects.create(code="EQUIPIER", active=False)
        codes = [c[0] for c in UserProfileForm().fields["role"].choices]
        self.assertNotIn("EQUIPIER", codes)
        self.assertIn("COMMANDANT_EN_SECOND", codes)
        self.assertIn("CHEF_SERVICE", codes)

    def test_expose_la_fonction_de_commandant_adjoint(self):
        self.assertIn("fonction_coma", UserProfileForm().fields)


class ValidationFormationBordTests(CommandantsAdjointsBase):
    def setUp(self):
        super().setUp()
        self.proposeur = self._marin("prop", "CHEF_SECTEUR", sector=self.secteur)
        self.proposeur_pont = self._marin("prop_pont", "CHEF_SECTEUR", sector=self.secteur_pont)
        self.proposeur_libre = self._marin("prop_libre", "CHEF_SECTEUR", sector=self.secteur_libre)
        self.chef_service = self._marin("chef_machine", "CHEF_SERVICE", service=self.machine)
        self.chef_service_libre = self._marin("chef_libre", "CHEF_SERVICE", service=self.libre)

    def test_titulaire_du_coma_du_service_valide(self):
        self.assertTrue(peut_valider_proposition_bord(self.comaeq, self.proposeur))

    def test_etat_major_d_un_autre_coma_ou_generique_ne_valide_pas(self):
        self.assertFalse(peut_valider_proposition_bord(self.comanav, self.proposeur))
        self.assertFalse(peut_valider_proposition_bord(self.em_simple, self.proposeur))

    def test_chef_de_service_du_perimetre_valide_toujours(self):
        self.assertTrue(peut_valider_proposition_bord(self.chef_service, self.proposeur))

    def test_service_sans_coma_repli_sur_le_seuil_actuel(self):
        self.assertTrue(peut_valider_proposition_bord(self.em_simple, self.proposeur_libre))
        self.assertTrue(peut_valider_proposition_bord(self.chef_service_libre, self.proposeur_libre))

    def test_coma_configure_sans_titulaire_repli_sur_le_seuil_actuel(self):
        UserProfile.objects.filter(user=self.comaeq).update(fonction_coma="")
        self.assertTrue(peut_valider_proposition_bord(self.em_simple, self.proposeur))

    def test_commandant_valide_toujours_second_selon_le_seuil_actuel(self):
        cdt = self._marin("cdt", "COMMANDANT", ship=self.navire)
        second = self._marin("second", "COMMANDANT_EN_SECOND", ship=self.navire)
        self.assertTrue(peut_valider_proposition_bord(cdt, self.proposeur))
        self.assertTrue(peut_valider_proposition_bord(second, self.proposeur))


class VisibiliteDossiersTests(CommandantsAdjointsBase):
    def setUp(self):
        super().setUp()
        self.cours = TrainingCourse.objects.create(title="Cours", validity_days=365)
        self.marin_machine = self._marin("m1", "EQUIPIER", section=self.section)
        self.marin_pont = self._marin("m2", "EQUIPIER", sector=self.secteur_pont)
        self.marin_libre = self._marin("m3", "EQUIPIER", sector=self.secteur_libre)
        self.dossiers = {
            nom: TrainingRecord.objects.create(
                user=u, course=self.cours,
                completed_at=timezone.localdate(), expires_at=timezone.localdate() + timezone.timedelta(days=30),
            )
            for nom, u in (("machine", self.marin_machine), ("pont", self.marin_pont), ("libre", self.marin_libre))
        }

    def _vus(self, user):
        q = dossiers_formation_visibles_q(user)
        return {n for n, d in self.dossiers.items() if TrainingRecord.objects.filter(q, pk=d.pk).exists()}

    def test_coma_voit_les_marins_de_ses_services_et_ceux_sans_coma(self):
        self.assertEqual(self._vus(self.comaeq), {"machine", "libre"})
        self.assertEqual(self._vus(self.comanav), {"pont", "libre"})

    def test_etat_major_sans_fonction_ne_voit_que_les_services_sans_coma(self):
        self.assertEqual(self._vus(self.em_simple), {"libre"})

    def test_sans_coma_configure_repli_etat_major_voit_le_navire(self):
        Service.objects.filter(ship=self.navire).update(commandant_adjoint="")
        self.assertEqual(self._vus(self.em_simple), {"machine", "pont", "libre"})

    def test_commandant_et_second_voient_tout_le_navire(self):
        cdt = self._marin("cdt", "COMMANDANT", ship=self.navire)
        second = self._marin("second", "COMMANDANT_EN_SECOND", ship=self.navire)
        for chef in (cdt, second):
            self.assertEqual(self._vus(chef), {"machine", "pont", "libre"})

    def test_chef_de_service_inchange(self):
        chef = self._marin("chef", "CHEF_SERVICE", service=self.machine)
        self.assertEqual(self._vus(chef), {"machine"})
