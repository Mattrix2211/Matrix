"""Annuaire web du personnel (UserDirectoryView, accounts/web_views.py) :
seul MASTER_ADMIN (ou un superutilisateur) doit voir la flotte entière, tous
les autres rôles admis dans l'annuaire (ADMIN_NAVIRE et COMMANDANT compris,
cf. matrix/core/scopes.py::is_master_admin) sont rattachés à un navire précis
et ne doivent voir que le personnel de leur propre navire.

Avant correction (audit sécurité du 2026-08-29), l'annuaire renvoyait tout le
personnel de la flotte par défaut, et un COMMANDANT pouvait en plus consulter
le personnel d'un autre navire en forçant le paramètre d'URL ?ship=<id>. Cf.
tâche « Sécurité : restreindre un COMMANDANT (et rôles supérieurs) à son
propre navire dans l'annuaire du personnel ». Pendant technique de
test_scope_leak_users_api.py, côté web plutôt qu'API.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Section, Sector, Service, Ship


class ScopeLeakUsersWebTests(TestCase):
    def setUp(self):
        # Navire A
        self.ship_a = Ship.objects.create(name="Navire A annuaire web", code="NA-ANW")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A annuaire web")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A annuaire web")

        # Navire B
        self.ship_b = Ship.objects.create(name="Navire B annuaire web", code="NB-ANW")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B annuaire web")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B annuaire web")

        self.equipier_b = User.objects.create_user(username="equipier_b_anw", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier_b, defaults={"role": "EQUIPIER", "sector": self.sector_b}
        )
        self.commandant_a = User.objects.create_user(username="commandant_a_anw", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant_a, defaults={"role": "COMMANDANT", "ship": self.ship_a}
        )
        self.admin_navire_a = User.objects.create_user(username="admin_navire_a_anw", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin_navire_a, defaults={"role": "ADMIN_NAVIRE", "ship": self.ship_a}
        )
        self.master_admin = User.objects.create_superuser(
            username="master_admin_anw", password="pass", email="master_admin_anw@example.com"
        )

    def test_commandant_ne_voit_pas_le_personnel_dun_autre_navire_par_defaut(self):
        self.client.login(username="commandant_a_anw", password="pass")
        r = self.client.get("/users/")
        self.assertEqual(r.status_code, 200)
        usernames = {u.username for u in r.context["users"]}
        self.assertIn("commandant_a_anw", usernames)
        self.assertNotIn("equipier_b_anw", usernames)

    def test_commandant_ne_peut_pas_forcer_la_vue_dun_autre_navire_via_lurl(self):
        """Avant correction, ?ship=<id> permettait de contourner le périmètre
        et d'afficher le personnel d'un navire tiers."""
        self.client.login(username="commandant_a_anw", password="pass")
        r = self.client.get(f"/users/?ship={self.ship_b.id}")
        self.assertEqual(r.status_code, 200)
        usernames = {u.username for u in r.context["users"]}
        self.assertNotIn("equipier_b_anw", usernames)

    def test_admin_navire_ne_voit_pas_le_personnel_dun_autre_navire(self):
        self.client.login(username="admin_navire_a_anw", password="pass")
        r = self.client.get("/users/")
        self.assertEqual(r.status_code, 200)
        usernames = {u.username for u in r.context["users"]}
        self.assertNotIn("equipier_b_anw", usernames)

    def test_master_admin_voit_la_flotte_entiere(self):
        self.client.login(username="master_admin_anw", password="pass")
        r = self.client.get("/users/")
        self.assertEqual(r.status_code, 200)
        usernames = {u.username for u in r.context["users"]}
        self.assertIn("equipier_b_anw", usernames)
        self.assertIn("commandant_a_anw", usernames)


class ScopeLeakUsersWebWriteTests(TestCase):
    """IDOR en écriture : avant correction, UserDirectoryView.post() résolvait
    l'utilisateur cible via User.objects.get(pk=...)/filter(id__in=...) sans
    aucun filtre de périmètre navire, permettant à un COMMANDANT/ADMIN_NAVIRE
    d'éditer, supprimer ou réinitialiser le mot de passe d'un utilisateur
    d'un autre navire (ou d'agir dessus via une action groupée) en forgeant
    une requête POST directe, hors de l'interface (qui ne propose que les
    utilisateurs de son propre navire)."""

    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A annuaire écriture", code="NA-ANE")
        self.ship_b = Ship.objects.create(name="Navire B annuaire écriture", code="NB-ANE")

        self.equipier_b = User.objects.create_user(
            username="equipier_b_ane", password="pass", first_name="Prenom", last_name="Origine"
        )
        UserProfile.objects.update_or_create(
            user=self.equipier_b, defaults={"role": "EQUIPIER", "ship": self.ship_b}
        )
        self.commandant_a = User.objects.create_user(username="commandant_a_ane", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant_a, defaults={"role": "COMMANDANT", "ship": self.ship_a}
        )

    def test_edit_user_refuse_une_cible_dun_autre_navire(self):
        self.client.login(username="commandant_a_ane", password="pass")
        r = self.client.post(
            "/users/",
            {
                "action": "edit_user",
                "pk": self.equipier_b.pk,
                "first_name": "Modifie",
                "last_name": "ParUnAutre",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_b.refresh_from_db()
        self.assertEqual(self.equipier_b.first_name, "Prenom")
        self.assertEqual(self.equipier_b.last_name, "Origine")

    def test_delete_user_refuse_une_cible_dun_autre_navire(self):
        self.client.login(username="commandant_a_ane", password="pass")
        r = self.client.post("/users/", {"action": "delete_user", "pk": self.equipier_b.pk})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.equipier_b.pk).exists())

    def test_set_password_refuse_une_cible_dun_autre_navire(self):
        self.client.login(username="commandant_a_ane", password="pass")
        r = self.client.post(
            "/users/",
            {"action": "set_password", "pk": self.equipier_b.pk, "password": "MotDePasseForce123!"},
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_b.refresh_from_db()
        self.assertFalse(self.equipier_b.check_password("MotDePasseForce123!"))

    def test_bulk_update_role_refuse_une_cible_dun_autre_navire(self):
        self.client.login(username="commandant_a_ane", password="pass")
        r = self.client.post(
            "/users/",
            {
                "action": "bulk_update_role",
                "selected_ids": [str(self.equipier_b.pk)],
                "role": "CHEF_SERVICE",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_b.profile.refresh_from_db()
        self.assertEqual(self.equipier_b.profile.role, "EQUIPIER")

    def test_bulk_reset_passwords_refuse_une_cible_dun_autre_navire(self):
        self.client.login(username="commandant_a_ane", password="pass")
        r = self.client.post(
            "/users/",
            {"action": "bulk_reset_passwords", "selected_ids": [str(self.equipier_b.pk)]},
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_b.refresh_from_db()
        # Le mot de passe d'origine ("pass") reste valide : aucune réinitialisation
        # n'a dû avoir lieu sur un utilisateur hors périmètre.
        self.assertTrue(self.equipier_b.check_password("pass"))

    def test_edit_user_fonctionne_sur_une_cible_du_meme_navire(self):
        """Non-régression : l'action reste opérationnelle pour une cible dans
        le périmètre de l'appelant."""
        equipier_a = User.objects.create_user(username="equipier_a_ane", password="pass")
        UserProfile.objects.update_or_create(
            user=equipier_a, defaults={"role": "EQUIPIER", "ship": self.ship_a}
        )
        self.client.login(username="commandant_a_ane", password="pass")
        r = self.client.post(
            "/users/",
            {"action": "edit_user", "pk": equipier_a.pk, "first_name": "Modifie", "last_name": "AvecDroit"},
        )
        self.assertEqual(r.status_code, 302)
        equipier_a.refresh_from_db()
        self.assertEqual(equipier_a.first_name, "Modifie")
        self.assertEqual(equipier_a.last_name, "AvecDroit")


class ScopeLeakUsersWebAssignmentDestinationTests(TestCase):
    """Avant correction, create_user et les actions bulk_update_ship/service/
    sector/section ne validaient que le PÉRIMÈTRE DE LA CIBLE (l'utilisateur
    modifié devait déjà appartenir au navire de l'appelant), jamais la valeur
    de DESTINATION demandée : un COMMANDANT/ADMIN_NAVIRE pouvait ainsi
    rattacher un utilisateur de son propre navire à un navire/service/
    secteur/section d'un AUTRE navire. Cf.
    matrix/core/scopes.py::resoudre_affectation_dans_perimetre."""

    def setUp(self):
        # Navire A (celui du COMMANDANT appelant)
        self.ship_a = Ship.objects.create(name="Navire A affectation", code="NA-AFF")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A affectation")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A affectation")
        self.section_a = Section.objects.create(sector=self.sector_a, name="Section A affectation")

        # Navire B (hors périmètre de l'appelant)
        self.ship_b = Ship.objects.create(name="Navire B affectation", code="NB-AFF")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B affectation")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B affectation")
        self.section_b = Section.objects.create(sector=self.sector_b, name="Section B affectation")

        self.commandant_a = User.objects.create_user(username="commandant_a_aff", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant_a, defaults={"role": "COMMANDANT", "ship": self.ship_a}
        )
        self.equipier_a = User.objects.create_user(username="equipier_a_aff", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier_a, defaults={"role": "EQUIPIER", "ship": self.ship_a}
        )

    def test_bulk_update_ship_refuse_une_destination_hors_perimetre(self):
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {"action": "bulk_update_ship", "selected_ids": [str(self.equipier_a.pk)], "ship_id": self.ship_b.pk},
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.profile.refresh_from_db()
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_a.pk)

    def test_bulk_update_service_refuse_une_destination_hors_perimetre(self):
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {
                "action": "bulk_update_service",
                "selected_ids": [str(self.equipier_a.pk)],
                "service_id": self.service_b.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.profile.refresh_from_db()
        self.assertIsNone(self.equipier_a.profile.service_id)

    def test_bulk_update_sector_refuse_une_destination_hors_perimetre(self):
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {
                "action": "bulk_update_sector",
                "selected_ids": [str(self.equipier_a.pk)],
                "sector_id": self.sector_b.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.profile.refresh_from_db()
        self.assertIsNone(self.equipier_a.profile.sector_id)

    def test_bulk_update_section_refuse_une_destination_hors_perimetre(self):
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {
                "action": "bulk_update_section",
                "selected_ids": [str(self.equipier_a.pk)],
                "section_id": self.section_b.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.profile.refresh_from_db()
        self.assertIsNone(self.equipier_a.profile.section_id)

    def test_bulk_update_ship_fonctionne_avec_une_destination_dans_le_perimetre(self):
        """Non-régression : affecter au propre navire de l'appelant reste possible."""
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {"action": "bulk_update_ship", "selected_ids": [str(self.equipier_a.pk)], "ship_id": self.ship_a.pk},
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.profile.refresh_from_db()
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_a.pk)

    def test_create_user_refuse_une_destination_hors_perimetre(self):
        self.client.login(username="commandant_a_aff", password="pass")
        nb_utilisateurs_avant = User.objects.count()
        r = self.client.post(
            "/users/",
            {
                "action": "create_user",
                "first_name": "Nouveau",
                "last_name": "MarinHorsPerimetre",
                "role": "EQUIPIER",
                "ship_id": self.ship_b.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(User.objects.count(), nb_utilisateurs_avant)
        self.assertFalse(User.objects.filter(first_name="Nouveau", last_name="MarinHorsPerimetre").exists())

    def test_create_user_fonctionne_avec_une_destination_dans_le_perimetre(self):
        """Non-régression : la création reste possible dans le périmètre de l'appelant."""
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {
                "action": "create_user",
                "first_name": "Nouveau",
                "last_name": "MarinDansPerimetre",
                "role": "EQUIPIER",
                "ship_id": self.ship_a.pk,
                "sector_id": self.sector_a.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        nouveau = User.objects.get(first_name="Nouveau", last_name="MarinDansPerimetre")
        self.assertEqual(nouveau.profile.ship_id, self.ship_a.pk)
        self.assertEqual(nouveau.profile.sector_id, self.sector_a.pk)

    # -- edit_user : avant correction (retour Tech Lead), la cible était bien
    # bornée au périmètre de l'appelant (cf. ScopeLeakUsersWebWriteTests
    # ci-dessus) mais ship_id/service_id/sector_id/section_id de DESTINATION
    # étaient résolus par un simple get_or_none(Model, pk), sans passer par
    # resoudre_affectation_dans_perimetre : un COMMANDANT/ADMIN_NAVIRE
    # pouvait donc contourner tout le correctif de create_user/bulk_update_*
    # en utilisant "Modifier" sur un utilisateur de son propre périmètre.

    def test_edit_user_refuse_une_destination_hors_perimetre_navire(self):
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {
                "action": "edit_user",
                "pk": self.equipier_a.pk,
                "first_name": "TentativeModif",
                "ship_id": self.ship_b.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.refresh_from_db()
        self.equipier_a.profile.refresh_from_db()
        # Aucune modification, pas même les champs simples (username/nom) qui
        # accompagnaient la requête : la validation de la destination doit
        # avoir lieu AVANT toute écriture, pour ne jamais laisser un état
        # partiellement appliqué.
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_a.pk)
        self.assertNotEqual(self.equipier_a.first_name, "TentativeModif")

    def test_edit_user_refuse_une_destination_hors_perimetre_service(self):
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {"action": "edit_user", "pk": self.equipier_a.pk, "service_id": self.service_b.pk},
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.profile.refresh_from_db()
        self.assertIsNone(self.equipier_a.profile.service_id)
        # La destination invalide bloque tout, y compris le champ déjà valide
        # (navire) transmis dans la même requête : aucune écriture partielle.
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_a.pk)

    def test_edit_user_refuse_une_destination_hors_perimetre_secteur(self):
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {"action": "edit_user", "pk": self.equipier_a.pk, "sector_id": self.sector_b.pk},
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.profile.refresh_from_db()
        self.assertIsNone(self.equipier_a.profile.sector_id)

    def test_edit_user_refuse_une_destination_hors_perimetre_section(self):
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {"action": "edit_user", "pk": self.equipier_a.pk, "section_id": self.section_b.pk},
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.profile.refresh_from_db()
        self.assertIsNone(self.equipier_a.profile.section_id)

    def test_edit_user_fonctionne_avec_une_destination_dans_le_perimetre(self):
        """Non-régression : édition + rattachement dans le périmètre de
        l'appelant restent opérationnels après correction."""
        self.client.login(username="commandant_a_aff", password="pass")
        r = self.client.post(
            "/users/",
            {
                "action": "edit_user",
                "pk": self.equipier_a.pk,
                "first_name": "Modifie",
                "ship_id": self.ship_a.pk,
                "sector_id": self.sector_a.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.equipier_a.refresh_from_db()
        self.equipier_a.profile.refresh_from_db()
        self.assertEqual(self.equipier_a.first_name, "Modifie")
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_a.pk)
        self.assertEqual(self.equipier_a.profile.sector_id, self.sector_a.pk)
