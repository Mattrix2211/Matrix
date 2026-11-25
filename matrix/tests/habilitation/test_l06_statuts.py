"""AC-10, AC-11 : trois statuts d'administration distincts, désignation du second, parité web / API, accès directs."""
import json

from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from matrix.core.roles import GENERAL, SUPERUTILISATEUR_DJANGO, TECHNIQUE, statuts_d_administration

from .outils import MondeFictif

User = get_user_model()


class StatutsTests(MondeFictif):
    def test_les_trois_statuts_sont_distincts_et_cumulables(self):
        self.assertEqual(statuts_d_administration(self.admin_navire), {TECHNIQUE})
        self.assertEqual(statuts_d_administration(self.cdt_b), set())
        self.assertEqual(statuts_d_administration(self.cdt_admin), {TECHNIQUE})
        self.assertIn(GENERAL, statuts_d_administration(self.master_admin))
        self.assertNotIn(SUPERUTILISATEUR_DJANGO, statuts_d_administration(User.objects.get(username="staff_sans_droit")))
        simple_superutilisateur = User.objects.create_superuser("su_django", password="x", email="s@s.fr")
        self.assertEqual(statuts_d_administration(simple_superutilisateur), {SUPERUTILISATEUR_DJANGO})  # pas administrateur général

    def _patch(self, nom, cible, donnees):
        return self.client_de(nom).patch(
            f"/api/accounts/profiles/{cible.profile.pk}/", data=json.dumps(donnees), content_type="application/json")

    def test_le_commandant_designe_et_revoque_le_second(self):
        self.assertEqual(self._patch("cdt_b", self.equipier_b1, {"role": "COMMANDANT_EN_SECOND"}).status_code, 200)
        self.assertEqual(UserProfile.objects.get(user=self.equipier_b1).role, "COMMANDANT_EN_SECOND")
        self.assertEqual(self._patch("cdt_b", self.equipier_b1, {"role": "EQUIPIER"}).status_code, 200)
        self.assertEqual(AuditLog.objects.filter(action="changement_role", target_user=self.equipier_b1).count(), 2)

    def test_personne_d_autre_ne_designe_le_second(self):
        for nom in ("admin_navire", "second_b", "comanav_b", "chef_service_b", "equipier_b1", "cdt_abe"):
            self.assertEqual(self._patch(nom, self.equipier_b2, {"role": "COMMANDANT_EN_SECOND"}).status_code, 403 if nom != "cdt_abe" else 404, nom)
        self.assertEqual(UserProfile.objects.get(user=self.equipier_b2).role, "EQUIPIER")

    def test_le_second_ne_s_attribue_pas_la_fonction_ni_ne_designe_son_successeur(self):
        self.assertEqual(self._patch("second_b", self.second_b, {"role": "COMMANDANT"}).status_code, 403)
        self.assertEqual(self._patch("second_b", self.equipier_b1, {"role": "COMMANDANT_EN_SECOND"}).status_code, 403)

    def test_parite_le_commandant_modifie_la_fonction_d_un_compte_technique_sans_toucher_au_drapeau(self):
        cible = self.admin_navire
        self.assertEqual(self._patch("cdt_b", cible, {"role": "CHEF_SERVICE"}).status_code, 200)
        profil = UserProfile.objects.get(user=cible)
        self.assertEqual((profil.role, profil.administrateur_technique), ("CHEF_SERVICE", True))
        web = self.client_de("cdt_b").post(reverse("user-directory"), {"action": "edit_user", "pk": cible.pk, "username": cible.username, "role": "CHEF_SECTEUR"})
        self.assertIn(web.status_code, (200, 302))
        profil.refresh_from_db()
        self.assertEqual((profil.role, profil.administrateur_technique), ("CHEF_SECTEUR", True))


class InterfaceTechniqueTests(MondeFictif):
    def test_l_annuaire_est_propose_a_l_administrateur_technique_et_pas_a_un_equipier(self):
        self.assertContains(self.client_de("admin_navire").get(reverse("home")), reverse("user-directory"))
        self.assertNotContains(self.client_de("equipier_b1").get(reverse("home")), 'href="' + reverse("user-directory") + '"')

    def test_seul_l_administrateur_general_voit_et_utilise_la_gestion_des_droits_techniques(self):
        technique = self.client_de("admin_navire").get(reverse("user-directory"))
        self.assertNotContains(technique, "Attribuer les droits techniques")
        self.assertNotContains(technique, "Nouvel utilisateur")
        general = self.client_de("master_admin")
        self.assertContains(general.get(reverse("user-directory")), "Attribuer les droits techniques")
        sans = general.post(reverse("user-directory"), {"action": "set_technique", "pk": self.equipier_b1.pk, "valeur": "1"})
        self.assertEqual(sans.status_code, 302)  # justification obligatoire : refusé avec un message
        self.assertFalse(UserProfile.objects.get(user=self.equipier_b1).administrateur_technique)
        general.post(reverse("user-directory"), {"action": "set_technique", "pk": self.equipier_b1.pk, "valeur": "1", "justification": "poste"})
        self.assertTrue(UserProfile.objects.get(user=self.equipier_b1).administrateur_technique)
        self.assertIn("poste", AuditLog.objects.get(action="changement_droits_techniques").details)
        general.post(reverse("user-directory"), {"action": "set_technique", "pk": self.master_admin.pk, "valeur": "1", "justification": "moi"})
        self.assertFalse(UserProfile.objects.get(user=self.master_admin).administrateur_technique)  # jamais sur soi-même

    def test_acces_direct_aux_fonctions_masquees(self):
        for nom in ("cdt_b", "second_b", "chef_service_b", "equipier_b1"):
            reponse = self.client_de(nom).post(reverse("user-directory"), {"action": "set_technique", "pk": self.equipier_b2.pk, "valeur": "1"})
            self.assertEqual(reponse.status_code, 403, nom)
        self.assertFalse(UserProfile.objects.get(user=self.equipier_b2).administrateur_technique)
        autre = self.client_de("admin_navire").post(reverse("user-directory"), {"action": "set_technique", "pk": self.equipier_abe.pk, "valeur": "1"})
        self.assertFalse(UserProfile.objects.get(user=self.equipier_abe).administrateur_technique, autre.status_code)
        for action in ("edit_user", "bulk_update_role", "delete_user", "bulk_delete_users"):
            reponse = self.client_de("admin_navire").post(reverse("user-directory"), {"action": action, "pk": self.equipier_b1.pk, "selected_ids": [self.equipier_b1.pk]})
            self.assertEqual(reponse.status_code, 403, action)

    def test_la_securite_est_consultable_par_le_technique_et_le_commandant_pas_par_un_chef(self):
        for nom, code in (("admin_navire", 200), ("cdt_b", 200), ("chef_service_b", 403), ("second_b", 403)):
            self.assertEqual(self.client_de(nom).get("/parametre/?tab=seuils_role").status_code, code, nom)
