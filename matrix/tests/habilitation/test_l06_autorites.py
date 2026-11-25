"""L06 : séparation de l'administration technique et de l'autorité métier (AC-01, AC-02), vérifiée sur le monde fictif."""
from datetime import timedelta

from django.contrib.auth import get_user_model

from django.utils import timezone

from accounts.models import AuditLog, DemandeReinitialisation, ServiceFunctionChoice, UserProfile
from matrix.core.role_thresholds import REGISTRE_ACTIONS, seuil_autorise, seuil_role
from matrix.core.roles import RoleLevel, est_administrateur_technique, niveau_ecriture, user_role_level
from org.models import RoleThresholdConfig
from quarts.models import ServiceGarde, peut_gerer_liste, peut_publier_liste

from .outils import MondeFictif

User = get_user_model()


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

    def test_seul_l_administrateur_general_attribue_et_retire_les_droits_techniques_avec_justification(self):
        """AC-19 : nominatif, justifié, historisé ; ni l'administrateur technique, ni le commandant, ni personne sur soi-même."""
        for nom in ("admin_navire", "cdt_admin", "cdt_b", "second_b"):
            reponse = self._patch(nom, self.equipier_b1, {"administrateur_technique": True, "justification": "essai"})
            self.assertEqual(reponse.status_code, 403, nom)
        self.assertFalse(UserProfile.objects.get(user=self.equipier_b1).administrateur_technique)
        sans = self._patch("master_admin", self.equipier_b1, {"administrateur_technique": True})
        self.assertEqual(sans.status_code, 400)  # justification obligatoire
        self.assertFalse(UserProfile.objects.get(user=self.equipier_b1).administrateur_technique)
        avec = self._patch("master_admin", self.equipier_b1, {"administrateur_technique": True, "justification": "poste d'administrateur du bâtiment"})
        self.assertEqual(avec.status_code, 200)
        ligne = AuditLog.objects.get(action="changement_droits_techniques")
        self.assertIn("administrateur_technique=False -> True", ligne.details)
        self.assertIn("poste d'administrateur du bâtiment", ligne.details)
        self.assertEqual((ligne.actor, ligne.target_user), (self.master_admin, self.equipier_b1))
        self._patch("master_admin", self.equipier_b1, {"administrateur_technique": True, "justification": "inchangé"})  # pas de trace
        self.assertEqual(AuditLog.objects.filter(action="changement_droits_techniques").count(), 1)
        retrait = self._patch("master_admin", self.equipier_b1, {"administrateur_technique": False, "justification": "fin de fonction"})
        self.assertEqual(retrait.status_code, 200)
        self.assertFalse(UserProfile.objects.get(user=self.equipier_b1).administrateur_technique)
        self.assertEqual(AuditLog.objects.filter(action="changement_droits_techniques").count(), 2)
        for nom in ("master_admin", "admin_navire"):  # jamais sur soi-même
            cible = User.objects.get(username=nom)
            self.assertEqual(self._patch(nom, cible, {"administrateur_technique": False, "justification": "x"}).status_code, 403, nom)

    def test_le_technique_ne_peut_pas_retirer_les_droits_d_un_pair_pour_reprendre_son_compte(self):
        self.assertEqual(self._patch("admin_navire", self.bsc_admin, {"administrateur_technique": False, "justification": "x"}).status_code, 403)
        web = self.client_de("admin_navire").post("/users/", {"action": "set_technique", "pk": self.bsc_admin.pk, "valeur": "0", "justification": "x"})
        self.assertEqual(web.status_code, 403)
        self.assertTrue(UserProfile.objects.get(user=self.bsc_admin).administrateur_technique)
        reponse = self.client_de("admin_navire").post("/users/", {"action": "set_password", "pk": self.bsc_admin.pk})
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(DemandeReinitialisation.objects.filter(user=self.bsc_admin).exists())

    def test_les_valeurs_de_formulaire_du_drapeau_sont_interpretees(self):
        for valeur in ("on", "true"):
            self._patch("master_admin", self.equipier_b1, {"administrateur_technique": valeur, "justification": "essai"})
            self.assertTrue(UserProfile.objects.get(user=self.equipier_b1).administrateur_technique, valeur)
            UserProfile.objects.filter(user=self.equipier_b1).update(administrateur_technique=False)

    def test_un_envoi_multipart_ne_retire_pas_le_drapeau_technique(self):
        from django.test.client import MULTIPART_CONTENT, BOUNDARY, encode_multipart
        UserProfile.objects.filter(user=self.admin_abe).update(ship=self.navire)  # compte technique rattaché à ce bâtiment
        cible = UserProfile.objects.get(user=self.admin_abe)
        corps = encode_multipart(BOUNDARY, {"role": "EQUIPIER", "grade": "X"})  # le champ booléen est absent du formulaire
        reponse = self.client_de("cdt_b").put(f"/api/accounts/profiles/{cible.pk}/", data=corps, content_type=MULTIPART_CONTENT)
        self.assertEqual(reponse.status_code, 200)
        profil = UserProfile.objects.get(user=self.admin_abe)
        self.assertEqual((profil.grade, profil.administrateur_technique), ("X", True))

    def test_la_reinitialisation_de_masse_ignore_les_comptes_non_reinitialisables(self):
        from accounts.services import peut_reinitialiser_cible
        self.assertFalse(peut_reinitialiser_cible(self.admin_navire, self.comanav_b))
        self.assertFalse(peut_reinitialiser_cible(self.admin_navire, self.admin_abe))
        self.assertTrue(peut_reinitialiser_cible(self.admin_navire, self.equipier_b1))

    def test_un_compte_porteur_d_une_designation_n_est_pas_reinitialisable_par_un_technique(self):
        from accounts.services import DESIGNATIONS
        for relation in DESIGNATIONS:  # une désignation renommée ou supprimée ne doit pas sortir silencieusement du contrôle
            self.assertTrue(hasattr(User, relation), relation)


class SeuilsTechniqueTests(MondeFictif):
    def _poster(self, nom, action, cle, role="EQUIPIER"):
        return self.client_de(nom).post("/parametre/", {"action": action, "cle_action": cle, "nouveau_role": role, "ship_id": self.navire.pk})

    def test_l_administrateur_technique_seul_ne_modifie_aucun_seuil_metier(self):
        for cle in ("liste_service_publication", "feuille_service_visa_service", "alerte_organisation_validation", "asset_ecriture_simple"):
            defaut = seuil_role(cle, self.navire.pk)
            for role in ("EQUIPIER", "COMMANDANT"):  # ni abaisser ni renforcer
                self.assertEqual(self._poster("admin_navire", "update_role_threshold", cle, role).status_code, 403, cle)
            self.assertEqual(seuil_role(cle, self.navire.pk), defaut, cle)
            RoleThresholdConfig.objects.update_or_create(ship=self.navire, defaults={"thresholds": {cle: "COMMANDANT"}})
            self.assertEqual(self._poster("admin_navire", "reset_role_threshold", cle).status_code, 403, cle)
            self.assertEqual(seuil_role(cle, self.navire.pk), RoleLevel.COMMANDANT, cle)
            RoleThresholdConfig.objects.all().delete()

    def test_l_administrateur_technique_regle_un_seuil_technique_et_consulte_les_autres(self):
        self.assertEqual(self._poster("admin_navire", "update_role_threshold", "mot_de_passe_reinitialisation", "ADMIN_NAVIRE").status_code, 302)
        reponse = self.client_de("admin_navire").get("/parametre/?tab=seuils_role")
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Lecture seule")

    def test_le_commandant_regle_un_seuil_metier_mais_pas_sous_un_plancher(self):
        self._poster("cdt_b", "update_role_threshold", "asset_ecriture_simple", "CHEF_SERVICE")
        self.assertEqual(seuil_role("asset_ecriture_simple", self.navire.pk), RoleLevel.CHEF_SERVICE)
        self._poster("cdt_b", "update_role_threshold", "module_gestion", "EQUIPIER")
        self.assertEqual(seuil_role("module_gestion", self.navire.pk), RoleLevel.COMMANDANT)
        self.assertEqual(self._poster("equipier_b1", "update_role_threshold", "asset_ecriture_simple", "CHEF_SERVICE").status_code, 403)
        self.assertTrue(AuditLog.objects.filter(action="update_role_threshold", actor=self.cdt_b).exists())

    def test_un_seuil_metier_enregistre_au_palier_obsolete_equivaut_au_commandant(self):
        RoleThresholdConfig.objects.create(ship=self.navire, thresholds={"asset_ecriture_simple": "ADMIN_NAVIRE"})
        self.assertEqual(seuil_role("asset_ecriture_simple", self.navire.pk), RoleLevel.COMMANDANT)

    def test_un_compte_d_administration_django_n_est_pas_reinitialisable_par_un_technique(self):
        from accounts.services import peut_reinitialiser_cible
        self.assertTrue(self.staff_sans_droit.is_staff)
        self.assertFalse(peut_reinitialiser_cible(self.admin_navire, self.staff_sans_droit))
        reponse = self.client_de("admin_navire").post("/users/", {"action": "set_password", "pk": self.staff_sans_droit.pk})
        self.assertEqual(reponse.status_code, 302)  # message, pas de page 403 ni de mot de passe provisoire


class RelationsUtilisateurTests(MondeFictif):
    def test_toute_nouvelle_relation_vers_un_compte_est_examinee(self):
        """Une relation vers l'utilisateur peut porter une autorité (désignation) : elle doit être classée soit dans
        `accounts.services.DESIGNATIONS` (protège le compte à la réinitialisation), soit dans la liste des relations
        examinées et jugées sans autorité (`relations_utilisateur_examinees.txt`). Une nouvelle relation fait échouer ce test."""
        from pathlib import Path

        from accounts.services import DESIGNATIONS
        examinees = set(Path(__file__).with_name("relations_utilisateur_examinees.txt").read_text(encoding="utf-8").split())
        actuelles = {r.get_accessor_name() for r in User._meta.related_objects}
        self.assertEqual(actuelles - set(DESIGNATIONS) - examinees, set(),
                         "Nouvelle relation vers l'utilisateur : l'ajouter à DESIGNATIONS si elle donne une autorité, sinon au fichier des relations examinées.")
        self.assertEqual(set(DESIGNATIONS) - actuelles, set(), "Désignation supprimée ou renommée.")
