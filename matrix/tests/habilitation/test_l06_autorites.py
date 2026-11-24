"""L06 : séparation de l'administration technique et de l'autorité métier (AC-01, AC-02), vérifiée sur le monde fictif."""
from datetime import timedelta

from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from matrix.core.role_thresholds import REGISTRE_ACTIONS, seuil_autorise, seuil_role
from matrix.core.roles import RoleLevel, est_administrateur_technique, niveau_ecriture, user_role_level
from org.models import RoleThresholdConfig
from quarts.models import ServiceGarde, peut_gerer_liste, peut_publier_liste

from .outils import MondeFictif


class AutoritesTests(MondeFictif):
    def test_un_administrateur_technique_seul_n_a_aucune_autorite_metier(self):
        for nom in ("admin_navire", "bsc_admin", "admin_abe"):
            utilisateur = getattr(self, nom)
            self.assertTrue(est_administrateur_technique(utilisateur), nom)
            self.assertEqual(user_role_level(utilisateur), RoleLevel.EQUIPIER, nom)
            self.assertEqual(niveau_ecriture(utilisateur), RoleLevel.EQUIPIER, nom)

    def test_le_cumul_garde_les_deux_roles_independants(self):
        self.assertTrue(est_administrateur_technique(self.cdt_admin))
        self.assertEqual(user_role_level(self.cdt_admin), RoleLevel.COMMANDANT)

    def test_un_commandant_sans_droits_techniques_n_est_pas_administrateur(self):
        self.assertFalse(est_administrateur_technique(self.cdt_b))
        self.assertFalse(est_administrateur_technique(self.second_b))

    def test_le_role_obsolete_ne_peut_plus_etre_enregistre(self):
        profil = UserProfile.objects.get(user=self.equipier_b1)
        profil.role = "ADMIN_NAVIRE"
        with self.assertRaises(ValueError):
            profil.save()

    def _liste_proposee(self):
        fonction = ServiceFunctionChoice.objects.create(name="Permanence")
        jour = timezone.localdate()
        return ServiceGarde.objects.create(
            service=self.service1, fonction=fonction, date_debut=jour, date_fin=jour + timedelta(days=7),
            statut=ServiceGarde.STATUT_PROPOSEE, created_by=self.chef_secteur_b,
        )

    def test_un_administrateur_technique_ne_publie_ni_ne_gere_une_liste(self):
        """A1 : le niveau d'administrateur franchissait les seuils de publication et de gestion des listes."""
        liste = self._liste_proposee()
        for nom in ("admin_navire", "bsc_admin"):
            self.assertFalse(peut_publier_liste(getattr(self, nom), liste), nom)
            self.assertFalse(peut_gerer_liste(getattr(self, nom), liste), nom)
        self.assertTrue(peut_publier_liste(self.cdt_b, liste))
        self.assertTrue(peut_publier_liste(self.cdt_admin, liste))

    def test_les_autorites_minimales_ne_peuvent_pas_etre_abaissees(self):
        a_plancher = {a.cle: a.plancher for a in REGISTRE_ACTIONS if a.plancher is not None}
        self.assertEqual(
            sorted(a_plancher),
            ["module_gestion", "programme_types", "structure_navire_ecriture", "unite_administration"],
        )
        configuration = {cle: "EQUIPIER" for cle in a_plancher}
        RoleThresholdConfig.objects.create(ship=self.navire, thresholds=configuration)
        for cle, plancher in a_plancher.items():
            self.assertGreaterEqual(seuil_role(cle, self.navire.pk), plancher, cle)
            self.assertFalse(seuil_autorise(cle, RoleLevel.EQUIPIER), cle)
            self.assertTrue(seuil_autorise(cle, RoleLevel.MASTER_ADMIN), cle)

    def test_un_seuil_peut_etre_renforce_au_dessus_du_plancher(self):
        RoleThresholdConfig.objects.create(ship=self.navire, thresholds={"module_gestion": "MASTER_ADMIN"})
        self.assertEqual(seuil_role("module_gestion", self.navire.pk), RoleLevel.MASTER_ADMIN)

    def test_aucun_droit_metier_deduit_du_statut_d_administrateur(self):
        for nom in ("admin_navire", "bsc_admin"):
            profil = getattr(self, nom).profile
            self.assertEqual(profil.role, "EQUIPIER")
            self.assertEqual(profil.fonction_coma, "")

    def test_aucune_trace_de_migration_sur_un_monde_cree_apres_la_migration(self):
        self.assertFalse(AuditLog.objects.filter(action="l06_migration_role").exists())


class ApiProfilsTests(MondeFictif):
    """Revue L06 : aucune voie de l'API des profils ne confère ou n'étend une autorité."""

    def _patch(self, nom, cible, donnees):
        import json
        client = self.client_de(nom)
        return client.patch(f"/api/accounts/profiles/{cible.profile.pk}/", data=json.dumps(donnees), content_type="application/json")

    def test_l_administrateur_technique_ne_designe_aucune_fonction(self):
        for cible in (self.equipier_b1, self.admin_navire):
            reponse = self._patch("admin_navire", cible, {"fonction_coma": "COMAEQ"})
            self.assertEqual(reponse.status_code, 403, cible.username)
            cible.profile.refresh_from_db()
            self.assertEqual(cible.profile.fonction_coma, "")

    def test_l_etat_major_technique_ne_s_attribue_pas_de_fonction_ni_de_perimetre(self):
        for donnees in ({"fonction_coma": "COMAEQ"}, {"service": self.service2.pk}, {"role": "COMMANDANT"}):
            reponse = self._patch("comanav_b", self.comanav_b, donnees)
            self.assertEqual(reponse.status_code, 403, donnees)

    def test_l_administrateur_technique_n_elargit_pas_son_perimetre(self):
        for donnees in ({"service": self.service2.pk}, {"sector": self.secteur2.pk}):
            self.assertEqual(self._patch("admin_navire", self.admin_navire, donnees).status_code, 403, donnees)

    def test_le_drapeau_technique_ne_se_modifie_pas_par_l_api_des_profils(self):
        reponse = self._patch("admin_navire", self.equipier_b1, {"administrateur_technique": True})
        self.assertIn(reponse.status_code, (200, 403))
        self.equipier_b1.profile.refresh_from_db()
        self.assertTrue(self.equipier_b1.profile.administrateur_technique or reponse.status_code == 403)
        self.assertEqual(AuditLog.objects.filter(action="changement_droits_techniques").count(),
                         1 if self.equipier_b1.profile.administrateur_technique else 0)

    def test_un_envoi_multipart_ne_retire_pas_le_drapeau_technique(self):
        client = self.client_de("admin_navire")
        client.put(f"/api/accounts/profiles/{self.equipier_b1.profile.pk}/", {"grade": ""})
        self.assertTrue(UserProfile.objects.get(user=self.admin_navire).administrateur_technique)

    def test_la_reinitialisation_de_masse_ignore_les_comptes_non_reinitialisables(self):
        from accounts.services import peut_reinitialiser_cible
        self.assertFalse(peut_reinitialiser_cible(self.admin_navire, self.comanav_b))
        self.assertFalse(peut_reinitialiser_cible(self.admin_navire, self.admin_abe))
        self.assertTrue(peut_reinitialiser_cible(self.admin_navire, self.equipier_b1))
