"""Tests des modules activables par bâtiment (tâche Notion « Modules
activables par bâtiment (administration distribuée, configuration) »,
Phase 1 - Socle).

Couvre :
- le comportement par défaut (aucune configuration explicite = tous les
  modules activés, pour ne rien changer aux navires existants) ;
- le seuil de rôle configurable `module_gestion` (COMMANDANT par défaut) qui
  protège l'onglet « Modules » des Réglages et l'action de bascule ;
- le masquage de l'entrée de menu correspondante dans la navigation
  (matrix/templates/base.html) une fois un module désactivé ;
- la protection d'accès direct par URL aux vues web du module désactivé
  (matrix/core/middleware.py::ModuleActivationMiddleware), avec un message
  clair plutôt qu'une erreur technique ;
- que l'API REST (/api/*) n'est PAS bloquée par la désactivation d'un module
  (la protection ne porte que sur la couche web, par choix de conception) ;
- qu'aucune donnée n'est supprimée : réactiver un module fait tout
  réapparaître tel quel.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from matrix.core.modules import invalidate_cache, module_actif
from matrix.core.role_thresholds import invalidate_cache as invalidate_role_thresholds_cache
from org.models import ModuleActivation, RoleThresholdConfig, Sector, Service, Ship


class ComportementParDefautTests(TestCase):
    """Sans aucune ModuleActivation enregistrée, tous les modules du registre
    doivent rester activés — non-régression pour les navires existants."""

    def test_tous_les_modules_du_registre_sont_actifs_par_defaut(self):
        ship = Ship.objects.create(name="Frégate Défaut", code="FR-DEF")
        for cle in ("assets", "maintenance", "logistics", "training", "quarts", "rondes", "reports"):
            self.assertTrue(module_actif(cle, ship.id), f"{cle} devrait être activé par défaut")

    def test_module_inconnu_du_registre_toujours_considere_actif(self):
        # Les apps de socle (accounts, org, notifications, dashboard,
        # calendar_app, threads) ne sont volontairement pas dans le registre :
        # une clé qui n'y figure pas doit toujours résoudre à "activé".
        ship = Ship.objects.create(name="Frégate Socle", code="FR-SOC")
        self.assertTrue(module_actif("notifications", ship.id))
        self.assertTrue(module_actif("dashboard", ship.id))

    def test_utilisateur_sans_navire_toujours_considere_actif(self):
        self.assertTrue(module_actif("assets", None))


class ToggleModuleTests(TestCase):
    """Bascule effective d'un module (modèle + fonction de résolution)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Frégate Toggle", code="FR-TOG")
        self.addCleanup(invalidate_cache, self.ship.id)

    def test_desactiver_puis_reactiver_ne_supprime_aucune_donnee(self):
        service = Service.objects.create(name="Service Toggle", ship=self.ship)
        sector = Sector.objects.create(name="Secteur Toggle", service=service)
        asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=sector)
        asset = Asset.objects.create(
            internal_id="EXT-001", asset_type=asset_type, ship=self.ship, service=service, sector=sector,
        )
        ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        invalidate_cache(self.ship.id)
        self.assertFalse(module_actif("assets", self.ship.id))
        # La donnée existe toujours en base, désactivation = masquage uniquement.
        self.assertTrue(Asset.objects.filter(pk=asset.pk).exists())

        activation = ModuleActivation.objects.get(ship=self.ship, module="assets")
        activation.active = True
        activation.save(update_fields=["active"])
        invalidate_cache(self.ship.id)
        self.assertTrue(module_actif("assets", self.ship.id))
        self.assertTrue(Asset.objects.filter(pk=asset.pk).exists())


class OngletModulesPermissionsTests(TestCase):
    """Accès à l'onglet « Modules » et à l'action de bascule, soumis au seuil
    configurable `module_gestion` (COMMANDANT par défaut)."""

    def setUp(self):
        self.url = reverse("settings")
        self.ship = Ship.objects.create(name="Frégate Permissions", code="FR-PERM")
        self.admin = User.objects.create_superuser(username="admin_mod", password="pass", email="a@a.fr")
        self.addCleanup(invalidate_cache, self.ship.id)

    def _marin(self, username, role, ship=None):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship or self.ship})
        return user

    def test_role_inferieur_au_seuil_par_defaut_refuse(self):
        chef_service = self._marin("chef_service_mod", "CHEF_SERVICE")
        self.client.login(username="chef_service_mod", password="pass")

        response = self.client.get(self.url, {"tab": "modules"})
        self.assertEqual(response.status_code, 403)

        response = self.client.post(self.url, {
            "action": "toggle_module", "cle_module": "assets", "ship_id": self.ship.id,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ModuleActivation.objects.exists())

    def test_commandant_peut_gerer_les_modules_de_son_navire_par_defaut(self):
        commandant = self._marin("commandant_mod", "COMMANDANT")
        self.client.login(username="commandant_mod", password="pass")

        response = self.client.get(self.url, {"tab": "modules"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_tab"], "modules")
        self.assertContains(response, "Matériels &amp; installations")

        response = self.client.post(self.url, {
            "action": "toggle_module", "cle_module": "assets", "ship_id": self.ship.id,
        })
        self.assertEqual(response.status_code, 302)
        activation = ModuleActivation.objects.get(ship=self.ship, module="assets")
        self.assertFalse(activation.active)

    def test_admin_navire_peut_aussi_gerer_les_modules(self):
        # ADMIN_NAVIRE est au-dessus de COMMANDANT dans la hiérarchie
        # (matrix/core/roles.py), il satisfait donc le seuil par défaut.
        self._marin("admin_navire_mod", "ADMIN_NAVIRE")
        self.client.login(username="admin_navire_mod", password="pass")

        response = self.client.get(self.url, {"tab": "modules"})
        self.assertEqual(response.status_code, 200)

    def test_seuil_module_gestion_abaisse_autorise_un_role_inferieur(self):
        chef_service = self._marin("chef_service_abaisse", "CHEF_SERVICE")
        RoleThresholdConfig.objects.create(
            ship=self.ship, thresholds={"module_gestion": "CHEF_SERVICE"},
        )
        invalidate_role_thresholds_cache(self.ship.id)
        self.addCleanup(invalidate_role_thresholds_cache, self.ship.id)

        self.client.login(username="chef_service_abaisse", password="pass")
        response = self.client.get(self.url, {"tab": "modules"})
        self.assertEqual(response.status_code, 200)

    def test_lien_modules_absent_de_la_navigation_pour_un_role_non_habilite(self):
        self._marin("chef_nav_mod", "CHEF_SERVICE")
        self.client.login(username="chef_nav_mod", password="pass")

        response = self.client.get(self.url, {"tab": "notifications"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">Modules<")

    def test_master_admin_peut_choisir_le_navire_et_basculer(self):
        self.client.login(username="admin_mod", password="pass")

        response = self.client.get(self.url, {"tab": "modules", "ship": self.ship.id})
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.url, {
            "action": "toggle_module", "cle_module": "logistics", "ship_id": self.ship.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            ModuleActivation.objects.get(ship=self.ship, module="logistics").active
        )


class NavigationEtAccesDirectTests(TestCase):
    """Masquage du menu et protection d'accès direct par URL aux vues web
    d'un module désactivé, pour un marin ordinaire (pas de droits de
    gestion des modules)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Frégate Accès", code="FR-ACC")
        self.marin = User.objects.create_user(username="marin_acces", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "CHEF_SECTION", "ship": self.ship},
        )
        self.client.login(username="marin_acces", password="pass")
        self.addCleanup(invalidate_cache, self.ship.id)

    def test_module_actif_menu_et_vue_accessibles(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'aria-label="Matériels"')

        response = self.client.get(reverse("asset-list"))
        self.assertEqual(response.status_code, 200)

    def test_module_desactive_masque_le_lien_de_menu(self):
        ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        invalidate_cache(self.ship.id)

        response = self.client.get(reverse("home"))
        self.assertNotContains(response, 'aria-label="Matériels"')
        self.assertNotContains(response, 'aria-label="Installations"')

    def test_module_desactive_bloque_l_acces_direct_par_url_avec_message_clair(self):
        ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        invalidate_cache(self.ship.id)

        response = self.client.get(reverse("asset-list"), follow=True)
        self.assertRedirects(response, reverse("home"))
        messages = list(response.context["messages"])
        self.assertTrue(any("désactivé" in str(m) for m in messages))
        # Message en français clair, pas une trace technique.
        self.assertFalse(any("Traceback" in str(m) or "Exception" in str(m) for m in messages))

    def test_module_reactive_redonne_acces_a_la_vue(self):
        activation = ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        invalidate_cache(self.ship.id)
        self.assertEqual(self.client.get(reverse("asset-list")).status_code, 302)

        activation.active = True
        activation.save(update_fields=["active"])
        invalidate_cache(self.ship.id)

        response = self.client.get(reverse("asset-list"))
        self.assertEqual(response.status_code, 200)

    def test_module_desactive_ne_bloque_pas_l_api_rest(self):
        # La protection ne porte que sur la couche web (pages HTML) — l'API
        # REST reste accessible pour ne pas casser d'éventuels clients
        # externes ni les enchaînements internes entre modules.
        ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        invalidate_cache(self.ship.id)

        response = self.client.get("/api/assets/assets/")
        self.assertEqual(response.status_code, 200)

    def test_module_toujours_actif_ne_bloque_pas_les_autres_modules(self):
        # Désactiver "assets" ne doit pas empêcher l'accès aux vues d'un
        # autre module resté activé.
        ModuleActivation.objects.create(ship=self.ship, module="assets", active=False)
        invalidate_cache(self.ship.id)

        response = self.client.get(reverse("quarts-index"))
        self.assertEqual(response.status_code, 200)
