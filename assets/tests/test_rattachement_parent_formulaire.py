from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType, Installation


class InstallationRattachementParentFormulaireTests(TestCase):
    """T3 : formulaire de rattachement parent (création + modification) sur
    Installation, seuil CHEF_SERVICE."""

    def setUp(self):
        self.ship = Ship.objects.create(name="S1")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec", service=self.service)
        self.autre_secteur = Sector.objects.create(name="AutreSec", service=self.service)

        self.chef = User.objects.create_user(username="chef_i", password="pass")
        self.chef_section = User.objects.create_user(username="chef_section_i", password="pass")
        self.equipier = User.objects.create_user(username="equipier_i", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE"})
        UserProfile.objects.update_or_create(user=self.chef_section, defaults={"role": "CHEF_SECTION"})
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})

        self.groupe = Installation.objects.create(
            designation="Groupe propulsion", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.hors_secteur = Installation.objects.create(
            designation="Hors secteur", ship=self.ship, service=self.service, sector=self.autre_secteur,
        )

    def test_creation_avec_parent_par_chef_service(self):
        self.client.login(username="chef_i", password="pass")
        r = self.client.post("/installations/", {
            "action": "create_installation",
            "designation": "Moteur bâbord",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.groupe.id),
        })
        self.assertEqual(r.status_code, 302)
        moteur = Installation.objects.get(designation="Moteur bâbord")
        self.assertEqual(moteur.parent_id, self.groupe.id)

    def test_modification_du_parent_par_chef_service(self):
        turbo = Installation.objects.create(
            designation="Turbo", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.client.login(username="chef_i", password="pass")
        r = self.client.post(f"/installations/{turbo.id}/", {
            "action": "edit_installation",
            "pk": str(turbo.id),
            "designation": turbo.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.groupe.id),
        })
        self.assertEqual(r.status_code, 302)
        turbo.refresh_from_db()
        self.assertEqual(turbo.parent_id, self.groupe.id)

    def test_refus_si_cycle_detecte(self):
        turbo = Installation.objects.create(
            designation="Turbo", ship=self.ship, service=self.service, sector=self.sector, parent=self.groupe,
        )
        self.client.login(username="chef_i", password="pass")
        r = self.client.post(f"/installations/{self.groupe.id}/", {
            "action": "edit_installation",
            "pk": str(self.groupe.id),
            "designation": self.groupe.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(turbo.id),
        }, follow=True)
        self.groupe.refresh_from_db()
        self.assertIsNone(self.groupe.parent)
        messages_affiches = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("boucle" in m for m in messages_affiches))

    def test_refus_si_role_insuffisant(self):
        self.client.login(username="equipier_i", password="pass")
        r = self.client.post(f"/installations/{self.groupe.id}/", {
            "action": "edit_installation",
            "pk": str(self.groupe.id),
            "designation": self.groupe.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.hors_secteur.id),
        })
        self.assertEqual(r.status_code, 403)
        self.groupe.refresh_from_db()
        self.assertIsNone(self.groupe.parent)

    def test_chef_section_peut_modifier_les_autres_champs_sans_le_parent(self):
        # Un chef de section ne peut pas gérer le rattachement (réservé CHEF_SERVICE),
        # mais l'édition normale (sans le champ parent_id, absent de son formulaire)
        # reste possible dès CHEF_SECTION (T-SEC).
        self.client.login(username="chef_section_i", password="pass")
        r = self.client.post(f"/installations/{self.groupe.id}/", {
            "action": "edit_installation",
            "pk": str(self.groupe.id),
            "designation": "Groupe propulsion renommé",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
        })
        self.assertEqual(r.status_code, 302)
        self.groupe.refresh_from_db()
        self.assertEqual(self.groupe.designation, "Groupe propulsion renommé")

    def test_equipier_ne_peut_pas_modifier_une_installation(self):
        # T-SEC : l'édition d'une fiche installation (même sans le champ parent_id)
        # est réservée à CHEF_SECTION et au-dessus, y compris via la fiche détail.
        self.client.login(username="equipier_i", password="pass")
        r = self.client.post(f"/installations/{self.groupe.id}/", {
            "action": "edit_installation",
            "pk": str(self.groupe.id),
            "designation": "Groupe propulsion renommé",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
        })
        self.assertEqual(r.status_code, 403)
        self.groupe.refresh_from_db()
        self.assertEqual(self.groupe.designation, "Groupe propulsion")

    def test_equipier_ne_peut_pas_supprimer_une_installation_depuis_la_fiche(self):
        # T-SEC : la suppression via la fiche détail (InstallationDetailView.post)
        # passait au travers de MAINTENANCE_WRITE_ACTIONS ; doit être bloquée.
        self.client.login(username="equipier_i", password="pass")
        r = self.client.post(f"/installations/{self.groupe.id}/", {
            "action": "delete_installation",
            "pk": str(self.groupe.id),
        })
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Installation.objects.filter(pk=self.groupe.id).exists())

    def test_filtre_perimetre_options_proposees_a_la_modification(self):
        self.client.login(username="chef_i", password="pass")
        r = self.client.get(f"/installations/{self.groupe.id}/")
        options = list(r.context["installations_pour_parent"])
        # L'installation d'un autre secteur n'est pas un rattachement raisonnable.
        self.assertNotIn(self.hors_secteur, options)
        # L'installation ne peut pas se rattacher à elle-même.
        self.assertNotIn(self.groupe, options)

    def test_peut_gerer_parent_false_pour_un_equipier(self):
        self.client.login(username="equipier_i", password="pass")
        r = self.client.get("/installations/")
        self.assertFalse(r.context["peut_gerer_parent"])

    def test_refus_si_parent_hors_secteur_a_la_creation(self):
        # Un CHEF_SERVICE légitime tente de POSTer directement un parent_id d'un autre
        # secteur, en contournant le menu déroulant filtré côté client : le serveur doit
        # revalider le périmètre et refuser, sans créer l'installation.
        self.client.login(username="chef_i", password="pass")
        r = self.client.post("/installations/", {
            "action": "create_installation",
            "designation": "Pompe intruse",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.hors_secteur.id),
        }, follow=True)
        self.assertFalse(Installation.objects.filter(designation="Pompe intruse").exists())
        messages_affiches = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("secteur" in m for m in messages_affiches))

    def test_refus_si_parent_hors_secteur_a_la_modification(self):
        # Idem à la modification : le POST direct d'un parent_id hors secteur ne doit
        # pas être accepté, même si le menu déroulant ne le proposait pas.
        turbo = Installation.objects.create(
            designation="Turbo", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.client.login(username="chef_i", password="pass")
        r = self.client.post(f"/installations/{turbo.id}/", {
            "action": "edit_installation",
            "pk": str(turbo.id),
            "designation": turbo.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.hors_secteur.id),
        }, follow=True)
        turbo.refresh_from_db()
        self.assertIsNone(turbo.parent)
        messages_affiches = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("secteur" in m for m in messages_affiches))


class AssetRattachementParentFormulaireTests(TestCase):
    """T3 : formulaire de rattachement parent (création + modification) sur
    Asset (matériel mobile), seuil CHEF_SERVICE."""

    def setUp(self):
        self.ship = Ship.objects.create(name="S1")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec", service=self.service)
        self.autre_secteur = Sector.objects.create(name="AutreSec", service=self.service)
        self.asset_type = AssetType.objects.create(name="Multimètre", category="Mesure", sector=self.sector)
        self.asset_type_autre_secteur = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.autre_secteur)

        self.chef = User.objects.create_user(username="chef_a", password="pass")
        self.equipier = User.objects.create_user(username="equipier_a", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SERVICE"})
        UserProfile.objects.update_or_create(user=self.equipier, defaults={"role": "EQUIPIER"})

        self.caisse = Asset.objects.create(
            asset_type=self.asset_type, designation="Caisse à outils",
            ship=self.ship, service=self.service, sector=self.sector,
        )
        self.hors_secteur = Asset.objects.create(
            asset_type=self.asset_type_autre_secteur, designation="Hors secteur",
            ship=self.ship, service=self.service, sector=self.autre_secteur,
        )

    def test_creation_avec_parent_par_chef_service(self):
        self.client.login(username="chef_a", password="pass")
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "asset_type_id": self.asset_type.id,
            "designation": "Multimètre n°1",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.caisse.id),
        })
        self.assertEqual(r.status_code, 302)
        outil = Asset.objects.get(designation="Multimètre n°1")
        self.assertEqual(outil.parent_id, self.caisse.id)

    def test_modification_du_parent_par_chef_service(self):
        outil = Asset.objects.create(
            asset_type=self.asset_type, designation="Multimètre n°2",
            ship=self.ship, service=self.service, sector=self.sector,
        )
        self.client.login(username="chef_a", password="pass")
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(outil.id),
            "designation": outil.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.caisse.id),
        })
        self.assertEqual(r.status_code, 302)
        outil.refresh_from_db()
        self.assertEqual(outil.parent_id, self.caisse.id)

    def test_refus_si_cycle_detecte(self):
        outil = Asset.objects.create(
            asset_type=self.asset_type, designation="Multimètre n°3",
            ship=self.ship, service=self.service, sector=self.sector, parent=self.caisse,
        )
        self.client.login(username="chef_a", password="pass")
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(self.caisse.id),
            "designation": self.caisse.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(outil.id),
        }, follow=True)
        self.caisse.refresh_from_db()
        self.assertIsNone(self.caisse.parent)
        messages_affiches = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("boucle" in m for m in messages_affiches))

    def test_refus_si_role_insuffisant(self):
        self.client.login(username="equipier_a", password="pass")
        outil = Asset.objects.create(
            asset_type=self.asset_type, designation="Multimètre n°4",
            ship=self.ship, service=self.service, sector=self.sector,
        )
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(outil.id),
            "designation": outil.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.caisse.id),
        })
        self.assertEqual(r.status_code, 403)
        outil.refresh_from_db()
        self.assertIsNone(outil.parent)

    def test_peut_gerer_parent_false_pour_un_equipier(self):
        self.client.login(username="equipier_a", password="pass")
        r = self.client.get("/assets/")
        self.assertFalse(r.context["peut_gerer_parent"])

    def test_options_proposees_incluent_le_secteur_pour_filtrage_perimetre(self):
        # Le filtrage fin par secteur est appliqué côté client (JS) sur ce
        # formulaire générique ; on vérifie que la donnée de secteur nécessaire
        # au filtrage est bien présente dans les options rendues.
        self.client.login(username="chef_a", password="pass")
        r = self.client.get("/assets/")
        self.assertContains(r, f'data-sector="{self.sector.id}"')

    def test_refus_si_parent_hors_secteur_a_la_creation(self):
        # Un CHEF_SERVICE légitime tente de POSTer directement un parent_id d'un autre
        # secteur, en contournant le menu déroulant filtré côté client (data-sector) :
        # le serveur doit revalider le périmètre et refuser, sans créer le matériel.
        self.client.login(username="chef_a", password="pass")
        r = self.client.post("/assets/", {
            "action": "create_asset",
            "asset_type_id": self.asset_type.id,
            "designation": "Multimètre intrus",
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.hors_secteur.id),
        }, follow=True)
        self.assertFalse(Asset.objects.filter(designation="Multimètre intrus").exists())
        messages_affiches = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("secteur" in m for m in messages_affiches))

    def test_refus_si_parent_hors_secteur_a_la_modification(self):
        # Idem à la modification : le POST direct d'un parent_id hors secteur ne doit
        # pas être accepté, même si le menu déroulant ne le proposait pas.
        outil = Asset.objects.create(
            asset_type=self.asset_type, designation="Multimètre n°5",
            ship=self.ship, service=self.service, sector=self.sector,
        )
        self.client.login(username="chef_a", password="pass")
        r = self.client.post("/assets/", {
            "action": "edit_asset",
            "pk": str(outil.id),
            "designation": outil.designation,
            "ship_id": self.ship.id,
            "service_id": self.service.id,
            "sector_id": self.sector.id,
            "parent_id": str(self.hors_secteur.id),
        }, follow=True)
        outil.refresh_from_db()
        self.assertIsNone(outil.parent)
        messages_affiches = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("secteur" in m for m in messages_affiches))
