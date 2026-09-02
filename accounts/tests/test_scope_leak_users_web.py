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
from org.models import Sector, Service, Ship


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
