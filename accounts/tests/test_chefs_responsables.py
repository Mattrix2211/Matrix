"""Chef du responsable de spécialité : un chef encadre plusieurs responsables
mais pas tous ; seul le chef DU responsable concerné vise ; écran de gestion
soumis au seuil « responsabilite_transverse_gestion »."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.chefs_responsables import chefs_du_responsable, peut_viser, qui_vise, responsables_sans_chef
from accounts.models import (
    AuditLog, ChefResponsableSpecialite, ResponsableSpecialite, SpecialityChoice, UserProfile,
)


def _marin(username):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": "EQUIPIER"})
    return user


class ResolutionChefTests(TestCase):
    def setUp(self):
        self.meca, self.elec, self.sic = (SpecialityChoice.objects.create(name=n) for n in ("Mécan", "Élec", "SIC"))
        self.r_meca = ResponsableSpecialite.objects.create(specialite=self.meca, user=_marin("r_meca"))
        self.r_elec = ResponsableSpecialite.objects.create(specialite=self.elec, user=_marin("r_elec"))
        self.r_sic = ResponsableSpecialite.objects.create(specialite=self.sic, user=_marin("r_sic"))
        self.chef1, self.chef2 = _marin("chef1"), _marin("chef2")
        ChefResponsableSpecialite.objects.create(user=self.chef1).responsables.set([self.r_meca, self.r_elec])
        ChefResponsableSpecialite.objects.create(user=self.chef2).responsables.set([self.r_sic])

    def test_un_chef_encadre_plusieurs_responsables_mais_pas_tous(self):
        self.assertEqual(list(chefs_du_responsable(self.r_meca)), [self.chef1])
        self.assertEqual(list(chefs_du_responsable(self.r_elec)), [self.chef1])
        self.assertEqual(list(chefs_du_responsable(self.r_sic)), [self.chef2])

    def test_seul_le_chef_du_responsable_concerne_vise(self):
        self.assertEqual(list(qui_vise(self.meca)), [self.chef1])
        self.assertTrue(peut_viser(self.chef1, self.elec))
        self.assertFalse(peut_viser(self.chef1, self.sic))
        self.assertFalse(peut_viser(self.chef2, self.meca))
        self.assertFalse(peut_viser(_marin("autre"), self.meca))

    def test_responsable_sans_chef_tolere_et_signale(self):
        ChefResponsableSpecialite.objects.get(user=self.chef2).delete()
        self.assertEqual(list(responsables_sans_chef()), [self.r_sic])
        self.assertEqual(list(qui_vise(self.sic)), [])


class EcranChefsTests(TestCase):
    def setUp(self):
        self.url = reverse("settings")
        self.admin = User.objects.create_superuser(username="adm", password="pass", email="a@a.fr")
        self.specialite = SpecialityChoice.objects.create(name="Mécan")
        self.autre_spe = SpecialityChoice.objects.create(name="Élec")
        self.r1 = ResponsableSpecialite.objects.create(specialite=self.specialite, user=_marin("r1"))
        self.r2 = ResponsableSpecialite.objects.create(specialite=self.autre_spe, user=_marin("r2"))
        self.chef = _marin("chef")

    def _definir(self, ids):
        return self.client.post(self.url, {
            "action": "definir_chef_responsable", "user_id": self.chef.pk, "responsable_ids": ids,
        }, follow=True)

    def test_role_insuffisant_refuse_par_defaut(self):
        commandant = _marin("cdt")
        UserProfile.objects.filter(user=commandant).update(role="COMMANDANT")
        self.client.force_login(commandant)
        self.assertEqual(self._definir([self.r1.pk]).status_code, 403)
        self.assertFalse(ChefResponsableSpecialite.objects.exists())

    def test_designation_partielle_tracee_sans_avertissement_de_totalite(self):
        self.client.force_login(self.admin)
        reponse = self._definir([self.r1.pk])
        self.assertEqual(list(ChefResponsableSpecialite.objects.get().responsables.all()), [self.r1])
        self.assertTrue(AuditLog.objects.filter(action="definir_chef_responsable", target_user=self.chef).exists())
        self.assertNotContains(reponse, "encadre tous les responsables")
        self.assertContains(reponse, "a pas de chef")  # r2 sans chef : toléré, signalé

    def test_chef_de_tous_les_responsables_refuse(self):
        self.client.force_login(self.admin)
        reponse = self._definir([self.r1.pk, self.r2.pk])
        self.assertContains(reponse, "ne peut pas encadrer tous les responsables")
        self.assertFalse(ChefResponsableSpecialite.objects.exists())

    def test_chef_autorise_s_il_n_y_a_qu_un_responsable(self):
        self.r2.delete()
        self.client.force_login(self.admin)
        self._definir([self.r1.pk])
        self.assertEqual(list(ChefResponsableSpecialite.objects.get().responsables.all()), [self.r1])

    def test_retrait_refuse_si_un_chef_encadrerait_tous_les_restants(self):
        r3 = ResponsableSpecialite.objects.create(specialite=SpecialityChoice.objects.create(name="SIC"), user=_marin("r3"))
        ChefResponsableSpecialite.objects.create(user=self.chef).responsables.set([self.r1, self.r2])
        self.client.force_login(self.admin)
        reponse = self.client.post(self.url, {"action": "retirer_responsable_specialite", "pk": r3.pk}, follow=True)
        self.assertContains(reponse, "Retrait refusé")
        self.assertTrue(ResponsableSpecialite.objects.filter(pk=r3.pk).exists())

    def test_retrait_autorise_si_aucun_chef_ne_couvre_tous_les_restants(self):
        r3 = ResponsableSpecialite.objects.create(specialite=SpecialityChoice.objects.create(name="SIC"), user=_marin("r3"))
        ChefResponsableSpecialite.objects.create(user=self.chef).responsables.set([self.r1])
        self.client.force_login(self.admin)
        self.client.post(self.url, {"action": "retirer_responsable_specialite", "pk": r3.pk}, follow=True)
        self.assertFalse(ResponsableSpecialite.objects.filter(pk=r3.pk).exists())

    def test_donnee_preexistante_couvrant_tous_signalee_sans_etre_cassee(self):
        ChefResponsableSpecialite.objects.create(user=self.chef).responsables.set([self.r1, self.r2])
        self.client.force_login(self.admin)
        reponse = self.client.get(self.url, {"tab": "utilisateurs"})
        self.assertContains(reponse, "encadre tous les responsables")
        self.assertEqual(ChefResponsableSpecialite.objects.get().responsables.count(), 2)

    def test_un_responsable_ne_peut_etre_son_propre_chef(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {
            "action": "definir_chef_responsable", "user_id": self.r1.user_id, "responsable_ids": [self.r1.pk],
        })
        self.assertFalse(ChefResponsableSpecialite.objects.exists())

    def test_retrait_trace(self):
        self.client.force_login(self.admin)
        self._definir([self.r1.pk])
        chef = ChefResponsableSpecialite.objects.get()
        self.client.post(self.url, {"action": "retirer_chef_responsable", "pk": chef.pk})
        self.assertFalse(ChefResponsableSpecialite.objects.exists())
        self.assertTrue(AuditLog.objects.filter(action="retirer_chef_responsable").exists())
