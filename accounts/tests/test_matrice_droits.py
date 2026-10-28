"""Matrice rôle × écran de l'administration : annuaire, édition, réinitialisation
de mot de passe, onglets de /parametre/ et modules. Un lien n'est affiché que si
l'accès est autorisé, et chaque action sensible est tracée dans l'AuditLog."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog
from matrix.core.role_thresholds import invalidate_cache
from org.models import ModuleActivation, ResponsableClasseNavire, RoleThresholdConfig, Ship

ONGLETS = [
    "generale", "utilisateurs", "responsables", "seuils_role", "modules", "equipage",
    "notifications", "journal", "navires", "hierarchie", "installations",
]
# Onglets attendus (200) par acteur, navire sans double équipage, seuils par défaut.
ONGLETS_AUTORISES = {
    "master": set(ONGLETS),
    "admin_a": {"seuils_role", "modules", "notifications"},
    "admin_b": {"seuils_role", "modules", "notifications"},
    "commandant": {"modules", "notifications"},
    "chef": {"notifications"},
    "equipier": {"notifications"},
}


class MatriceDroitsBase(TestCase):
    def setUp(self):
        self.a = Ship.objects.create(name="Navire A matrice", code="MXA")
        self.b = Ship.objects.create(name="Navire B matrice", code="MXB")
        self.acteurs = {
            "master": User.objects.create_superuser("master_mx", "m@example.com", "pass"),
            "admin_a": self.marin("admin_a_mx", "ADMIN_NAVIRE", self.a),
            "admin_b": self.marin("admin_b_mx", "ADMIN_NAVIRE", self.b),
            "commandant": self.marin("commandant_mx", "COMMANDANT", self.a),
            "chef": self.marin("chef_mx", "CHEF_SERVICE", self.a),
            "equipier": self.marin("equipier_mx", "EQUIPIER", self.a),
        }
        self.equipier_b = self.marin("equipier_b_mx", "EQUIPIER", self.b)

    def marin(self, nom, role, navire):
        user = User.objects.create_user(nom, password="pass")
        profil = user.profile
        profil.role, profil.ship = role, navire
        profil.save()
        return user

    def connecter(self, cle):
        self.client.force_login(self.acteurs[cle])

    def abaisser_seuil(self, cle_action, role, navire=None):
        RoleThresholdConfig.objects.update_or_create(ship=navire, defaults={"thresholds": {cle_action: role}})
        invalidate_cache(navire.id if navire else None)
        self.addCleanup(invalidate_cache, navire.id if navire else None)


class AnnuaireEtEditionTests(MatriceDroitsBase):
    def test_acces_a_l_annuaire_par_role(self):
        attendu = {"master": 200, "admin_a": 200, "admin_b": 200, "commandant": 200, "chef": 403, "equipier": 403}
        for cle, code in attendu.items():
            self.connecter(cle)
            self.assertEqual(self.client.get(reverse("user-directory")).status_code, code, cle)

    def test_l_annuaire_est_borne_au_navire_et_cache_les_comptes_maitres(self):
        self.connecter("admin_a")
        noms = {u.username for u in self.client.get(reverse("user-directory")).context["users"]}
        self.assertIn("equipier_mx", noms)
        self.assertNotIn("equipier_b_mx", noms)
        self.assertNotIn("master_mx", noms)
        self.connecter("admin_b")
        noms = {u.username for u in self.client.get(reverse("user-directory")).context["users"]}
        self.assertEqual(noms & {"equipier_mx", "admin_a_mx"}, set())
        self.assertIn("equipier_b_mx", noms)

    def test_page_d_edition_par_role_et_cible(self):
        cibles = {
            # (acteur, cible) -> code attendu
            ("master", "equipier"): 200, ("master", "admin_b"): 200,
            ("admin_a", "equipier"): 200, ("admin_a", "commandant"): 200, ("admin_a", "admin_a"): 200,
            ("admin_a", "admin_b"): 404, ("admin_a", "master"): 404,
            ("commandant", "equipier"): 200, ("commandant", "admin_a"): 404, ("commandant", "master"): 404,
            ("chef", "equipier"): 403, ("equipier", "equipier"): 403,
        }
        for (acteur, cible), code in cibles.items():
            self.connecter(acteur)
            url = reverse("user-edit", args=[self.acteurs[cible].pk])
            self.assertEqual(self.client.get(url).status_code, code, f"{acteur} -> {cible}")
        self.connecter("admin_b")
        self.assertEqual(self.client.get(reverse("user-edit", args=[self.acteurs["equipier"].pk])).status_code, 404)

    def test_pas_de_lien_vers_un_compte_non_modifiable(self):
        self.connecter("commandant")
        page = self.client.get(reverse("user-directory"))
        self.assertContains(page, reverse("user-edit", args=[self.acteurs["equipier"].pk]))
        self.assertNotContains(page, reverse("user-edit", args=[self.acteurs["admin_a"].pk]))

    def test_les_roles_proposes_suivent_le_droit_d_attribution(self):
        self.connecter("commandant")
        codes = {r["code"] for r in self.client.get(reverse("user-directory")).context["roles"]}
        self.assertNotIn("ADMIN_NAVIRE", codes)
        self.assertNotIn("COMMANDANT", codes)
        self.assertIn("EQUIPIER", codes)
        self.connecter("admin_a")
        codes = {r["code"] for r in self.client.get(reverse("user-directory")).context["roles"]}
        self.assertIn("ADMIN_NAVIRE", codes)
        self.assertNotIn("MASTER_ADMIN", codes)

    def test_edition_hors_perimetre_ou_de_rang_superieur_refusee(self):
        for acteur, cible in (("admin_a", "equipier_b"), ("commandant", "admin_a")):
            self.connecter(acteur)
            cible_user = self.equipier_b if cible == "equipier_b" else self.acteurs[cible]
            self.client.post(reverse("user-directory"), {
                "action": "edit_user", "pk": cible_user.pk, "username": "pirate", "role": "EQUIPIER",
            })
            cible_user.refresh_from_db()
            self.assertNotEqual(cible_user.username, "pirate", f"{acteur} -> {cible}")

    def test_changement_de_role_trace(self):
        self.connecter("admin_a")
        cible = self.acteurs["equipier"]
        self.client.post(reverse("user-directory"), {
            "action": "edit_user", "pk": cible.pk, "username": cible.username, "role": "CHEF_SECTION",
        })
        journal = AuditLog.objects.get(action="changement_role", target_user=cible)
        self.assertEqual((journal.actor, journal.details), (self.acteurs["admin_a"], "role=EQUIPIER -> CHEF_SECTION"))

    def test_changement_de_role_groupe_et_api_traces(self):
        self.connecter("admin_a")
        cible = self.acteurs["equipier"]
        self.client.post(reverse("user-directory"), {"action": "bulk_update_role", "selected_ids": [cible.pk], "role": "CHEF_SECTION"})
        self.assertEqual(AuditLog.objects.get(action="bulk_update_role", target_user=cible).details, "role=EQUIPIER -> CHEF_SECTION")
        reponse = self.client.patch(
            f"/api/accounts/profiles/{cible.profile.pk}/", {"role": "CHEF_SECTEUR"}, content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="changement_role", target_user=cible, details="role=CHEF_SECTION -> CHEF_SECTEUR").exists())


class SuppressionDeSoiTests(MatriceDroitsBase):
    def test_suppression_de_soi_refusee(self):
        self.connecter("commandant")
        moi = self.acteurs["commandant"]
        reponse = self.client.post(reverse("user-directory"), {"action": "delete_user", "pk": moi.pk}, follow=True)
        self.assertTrue(User.objects.filter(pk=moi.pk).exists())
        self.assertFalse(AuditLog.objects.filter(action="delete_user", target_user=moi).exists())
        self.assertContains(reponse, "ne pouvez pas supprimer votre propre compte")

    def test_suppression_groupee_ignore_l_appelant(self):
        self.connecter("commandant")
        moi, autre = self.acteurs["commandant"], self.acteurs["equipier"]
        reponse = self.client.post(
            reverse("user-directory"), {"action": "bulk_delete_users", "selected_ids": [moi.pk, autre.pk]}, follow=True,
        )
        self.assertTrue(User.objects.filter(pk=moi.pk).exists())
        self.assertFalse(User.objects.filter(pk=autre.pk).exists())
        self.assertContains(reponse, "ne pouvez pas supprimer votre propre compte")

    def test_menu_supprimer_absent_sur_sa_propre_ligne(self):
        self.connecter("commandant")
        html = self.client.get(reverse("user-directory")).content.decode()
        self.assertNotIn(f'data-action="delete_user" data-pk="{self.acteurs["commandant"].pk}"', html)
        self.assertIn(f'data-action="delete_user" data-pk="{self.acteurs["equipier"].pk}"', html)


class AnnuaireDoubleEquipageTests(MatriceDroitsBase):
    def test_admin_du_navire_voit_les_deux_equipages_mais_pas_un_autre_navire(self):
        self.a.double_equipage = True
        self.a.save()
        for cle, equipage in (("equipier", "A"), ("chef", "B")):
            profil = self.acteurs[cle].profile
            profil.equipage = equipage
            profil.save()
        self.connecter("admin_a")
        noms = {u.username for u in self.client.get(reverse("user-directory")).context["users"]}
        self.assertTrue({"equipier_mx", "chef_mx"} <= noms)
        self.assertNotIn("equipier_b_mx", noms)


class ReinitialisationMatriceTests(MatriceDroitsBase):
    def reinitialiser(self, acteur, cible):
        self.connecter(acteur)
        return self.client.post(reverse("user-directory"), {"action": "set_password", "pk": cible.pk})

    def test_reinitialisation_par_role_seuil_par_defaut(self):
        cible = self.acteurs["equipier"]
        for acteur in ("commandant", "chef", "equipier"):
            self.assertEqual(self.reinitialiser(acteur, cible).status_code, 403, acteur)
        self.assertEqual(self.reinitialiser("admin_a", cible).status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="reinitialisation_mot_de_passe", actor=self.acteurs["admin_a"], target_user=cible).exists())
        self.assertEqual(self.reinitialiser("master", self.equipier_b).status_code, 200)

    def test_reinitialisation_hors_navire_ou_maitre_refusee(self):
        for acteur, cible in (("admin_a", self.equipier_b), ("admin_b", self.acteurs["equipier"]), ("admin_a", self.acteurs["master"])):
            reponse = self.reinitialiser(acteur, cible)
            self.assertEqual(reponse.status_code, 302, acteur)
            cible.refresh_from_db()
            self.assertTrue(cible.check_password("pass"))
        self.assertFalse(AuditLog.objects.filter(action="reinitialisation_mot_de_passe").exists())

    def test_seuil_abaisse_ne_donne_pas_acces_aux_rangs_superieurs(self):
        self.abaisser_seuil("mot_de_passe_reinitialisation", "COMMANDANT", self.a)
        self.assertEqual(self.reinitialiser("commandant", self.acteurs["equipier"]).status_code, 200)
        refus = self.reinitialiser("commandant", self.acteurs["admin_a"])
        self.assertEqual(refus.status_code, 302)
        self.assertTrue(self.acteurs["admin_a"].check_password("pass"))

    def test_bouton_affiche_seulement_pour_qui_peut_et_sur_les_autres_comptes(self):
        self.connecter("admin_a")
        page = self.client.get(reverse("user-directory"))
        self.assertContains(page, 'data-username="equipier_mx"')
        self.assertNotContains(page, 'data-username="admin_a_mx"')
        self.connecter("commandant")
        self.assertNotContains(self.client.get(reverse("user-directory")), 'data-bs-target="#resetPasswordModal"')


class ParametresMatriceTests(MatriceDroitsBase):
    def test_onglets_accessibles_par_role(self):
        for cle, autorises in ONGLETS_AUTORISES.items():
            self.connecter(cle)
            for onglet in ONGLETS:
                attendu = 200 if onglet in autorises else 403
                self.assertEqual(self.client.get("/parametre/", {"tab": onglet}).status_code, attendu, f"{cle} / {onglet}")

    def test_lien_affiche_si_et_seulement_si_acces(self):
        for cle, autorises in ONGLETS_AUTORISES.items():
            self.connecter(cle)
            page = self.client.get("/parametre/", {"tab": "notifications"}).content.decode()
            for onglet in ONGLETS:
                lien = f'href="/parametre/?tab={onglet}'
                self.assertEqual(lien in page, onglet in autorises, f"{cle} / {onglet}")

    def test_onglet_equipage_reserve_au_double_equipage(self):
        self.a.double_equipage = True
        self.a.save()
        for cle, attendu in (("admin_a", 200), ("commandant", 200), ("chef", 403), ("admin_b", 403)):
            self.connecter(cle)
            self.assertEqual(self.client.get("/parametre/", {"tab": "equipage"}).status_code, attendu, cle)

    def test_modules_bornes_au_navire_de_l_acteur(self):
        for cle, navire, autre in (("admin_a", self.a, self.b), ("commandant", self.a, self.b), ("admin_b", self.b, self.a)):
            self.connecter(cle)
            self.client.post("/parametre/", {"action": "toggle_module", "cle_module": "rondes", "ship_id": autre.pk})
            self.assertFalse(ModuleActivation.objects.get(ship=navire, module="rondes").active, cle)
            self.assertFalse(ModuleActivation.objects.filter(ship=autre, module="rondes").exists(), cle)
            ModuleActivation.objects.all().delete()
            self.assertTrue(AuditLog.objects.filter(action="toggle_module", actor=self.acteurs[cle]).exists())

    def test_modules_refuse_sous_le_seuil(self):
        for cle in ("chef", "equipier"):
            self.connecter(cle)
            reponse = self.client.post("/parametre/", {"action": "toggle_module", "cle_module": "rondes"})
            self.assertEqual(reponse.status_code, 403, cle)
        self.assertFalse(ModuleActivation.objects.exists())

    def test_seuils_de_role_bornes_au_navire_de_l_administrateur(self):
        self.connecter("admin_a")
        self.client.post("/parametre/", {
            "action": "update_role_threshold", "cle_action": "module_gestion", "nouveau_role": "ADMIN_NAVIRE", "ship_id": self.b.pk,
        })
        self.assertTrue(RoleThresholdConfig.objects.filter(ship=self.a).exists())
        self.assertFalse(RoleThresholdConfig.objects.filter(ship=self.b).exists())
        self.assertTrue(AuditLog.objects.filter(action="update_role_threshold", actor=self.acteurs["admin_a"]).exists())
        self.connecter("commandant")
        reponse = self.client.post("/parametre/", {"action": "update_role_threshold", "cle_action": "module_gestion", "nouveau_role": "EQUIPIER"})
        self.assertEqual(reponse.status_code, 403)

    def test_responsables_limites_aux_marins_du_navire(self):
        self.abaisser_seuil("responsabilite_transverse_gestion", "ADMIN_NAVIRE")
        self.connecter("admin_a")
        page = self.client.get("/parametre/", {"tab": "responsables"})
        noms = {u.username for u in page.context["marins_disponibles"]}
        self.assertIn("equipier_mx", noms)
        self.assertNotIn("equipier_b_mx", noms)
        self.client.post("/parametre/", {"action": "add_responsable_classe", "name": "Classe X", "user_id": self.equipier_b.pk})
        self.assertFalse(ResponsableClasseNavire.objects.exists())
        self.client.post("/parametre/", {"action": "add_responsable_classe", "name": "Classe X", "user_id": self.acteurs["equipier"].pk})
        self.assertEqual(ResponsableClasseNavire.objects.count(), 1)


class CreationUtilisateurRoleTests(MatriceDroitsBase):
    def _selectionnes(self, cle):
        import re
        self.connecter(cle)
        html = self.client.get(reverse("user-create")).content.decode()
        select = re.search(r'<select[^>]*id="fRole".*?</select>', html, re.S).group(0)
        return re.findall(r'<option value="([^"]*)"\s+selected', select)

    def test_formulaire_sans_role_eleve_preselectionne(self):
        for cle in ("commandant", "admin_a"):
            self.assertEqual(self._selectionnes(cle), [""], cle)

    def test_creation_sans_role_refusee(self):
        self.connecter("admin_a")
        avant = User.objects.count()
        reponse = self.client.post(reverse("user-directory"), {
            "action": "create_user", "first_name": "Sans", "last_name": "Role", "ship_id": self.a.pk,
        }, follow=True)
        self.assertContains(reponse, "Choisissez un rôle valide.")
        self.assertEqual(User.objects.count(), avant)

    def test_creation_avec_role_autorise_applique_le_role(self):
        self.connecter("commandant")
        self.client.post(reverse("user-directory"), {
            "action": "create_user", "first_name": "Avec", "last_name": "Role", "role": "CHEF_SECTION",
            "ship_id": self.a.pk, "equipage": "BLEU",
        })
        self.assertEqual(User.objects.get(username="avec.role").profile.role, "CHEF_SECTION")

    def test_actions_de_masse_sans_role_preselectionne(self):
        self.connecter("admin_a")
        html = self.client.get(reverse("user-directory")).content.decode()
        self.assertIn('id="bulkRole" required>\n              <option value="" selected disabled>', html)
