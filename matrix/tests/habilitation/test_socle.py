"""Point de contrôle commun : parité avec les mécanismes existants et refus par défaut (lot L29)."""
from django.contrib.auth.models import AnonymousUser

from matrix.core.ecriture_service import niveau_ecriture_sur
from matrix.core.habilitation import NOMS_FACTEURS, Action, Decision, evaluer
from matrix.core.roles import RoleLevel
from org.models import ModuleActivation

from .outils import MondeFictif

PROFILS = ("equipier_b1", "chef_section_b1", "chef_service_b", "chef_service_sec", "comanav_b", "comaeq_b", "second_b", "cdt_b",
           "admin_navire", "master_admin", "equipier_a", "cdt_a", "equipier_abe", "cdt_abe", "soutien_terre")


class SocleTests(MondeFictif):
    def test_un_visiteur_non_connecte_ou_desactive_est_refuse(self):
        for action in Action:
            decision = evaluer(AnonymousUser(), action)
            self.assertFalse(decision)
            self.assertEqual(decision.facteur, "authentifie")
        self.equipier_b1.is_active = False
        self.assertEqual(evaluer(self.equipier_b1, Action.LIRE).facteur, "authentifie")

    def test_l_ecriture_sur_un_objet_est_identique_au_niveau_d_ecriture_existant(self):
        for profil in PROFILS:
            utilisateur = getattr(self, profil)
            for niveau in (RoleLevel.EQUIPIER, RoleLevel.CHEF_SECTION, RoleLevel.CHEF_SERVICE):
                attendu = niveau_ecriture_sur(utilisateur, self.ticket_sec) >= niveau
                decision = evaluer(utilisateur, Action.ECRIRE, objet=self.ticket_sec, niveau_requis=niveau)
                self.assertEqual(decision.autorise, attendu, f"{profil}/{niveau.name}")

    def test_la_lecture_d_un_objet_est_refusee_comme_usage(self):
        with self.assertRaises(ValueError):
            evaluer(self.cdt_b, Action.LIRE, objet=self.ticket_sec)

    def test_un_module_desactive_refuse_la_lecture_comme_l_ecriture(self):
        ModuleActivation.objects.create(ship=self.navire, module="logistics", active=False)
        for action in Action:
            decision = evaluer(self.cdt_b, action, module="logistics")
            self.assertFalse(decision)
            self.assertEqual(decision.facteur, "module_actif")
        self.assertTrue(evaluer(self.cdt_b, Action.LIRE, module="maintenance"))

    def test_un_etat_major_n_ecrit_que_sur_ses_services(self):
        self.assertTrue(evaluer(self.comaeq_b, Action.ECRIRE, objet=self.ticket_sec, niveau_requis=RoleLevel.CHEF_SECTION))
        refus = evaluer(self.comanav_b, Action.ECRIRE, objet=self.ticket_sec, niveau_requis=RoleLevel.CHEF_SECTION)
        self.assertEqual(refus.facteur, "niveau_sur_service")

    def test_les_facteurs_sont_nommes_et_ordonnes(self):
        self.assertEqual(NOMS_FACTEURS, ("authentifie", "module_actif", "niveau_sur_service"))
        self.assertEqual(Decision(True).facteur, "")
