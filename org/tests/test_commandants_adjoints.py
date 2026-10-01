"""Niveau « commandant adjoint » (COMAEQ / COMOPS / COMANAV / COMAVIA) entre le
navire et les services : modèle, rétrocompatibilité, onglet de configuration
des Réglages (permissions, périmètre, audit) et validation API."""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from org.commandants_adjoints import commandant_adjoint_du_service
from org.models import CommandantAdjoint, Service, Ship


class ModeleCommandantAdjointTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="BRF Test", code="BRF-T")

    def test_service_sans_rattachement_tolere(self):
        service = Service.objects.create(ship=self.navire, name="Pont")
        self.assertIsNone(service.commandant_adjoint)
        self.assertIsNone(commandant_adjoint_du_service(service))

    def test_helper_renvoie_le_commandant_adjoint_du_service(self):
        comanav = CommandantAdjoint.objects.create(ship=self.navire, sigle="COMANAV")
        service = Service.objects.create(ship=self.navire, name="Flotteur", commandant_adjoint=comanav)
        self.assertEqual(commandant_adjoint_du_service(service), comanav)

    def test_sigle_affiche_et_signification(self):
        comops = CommandantAdjoint.objects.create(ship=self.navire, sigle="COMOPS")
        self.assertEqual(str(comops), "BRF Test / COMOPS")
        self.assertEqual(comops.signification, "Commandant adjoint opérations")

    def test_responsabilites_de_chaque_sigle(self):
        comops = CommandantAdjoint.objects.create(ship=self.navire, sigle="COMOPS")
        comanav = CommandantAdjoint.objects.create(ship=self.navire, sigle="COMANAV")
        self.assertIn("activité à la mer", comops.responsabilites)
        self.assertIn("conservation du bâtiment", comanav.responsabilites.lower())
        self.assertEqual(set(CommandantAdjoint.RESPONSABILITES), set(CommandantAdjoint.Sigle.values))

    def test_filtre_coma_du_service(self):
        from org.templatetags.org_extras import coma_du_service
        comanav = CommandantAdjoint.objects.create(ship=self.navire, sigle="COMANAV")
        service = Service.objects.create(ship=self.navire, name="Flotteur", commandant_adjoint=comanav)
        self.assertEqual(coma_du_service(service), comanav)
        self.assertIsNone(coma_du_service(None))

    def test_suppression_du_poste_detache_les_services(self):
        comaeq = CommandantAdjoint.objects.create(ship=self.navire, sigle="COMAEQ")
        service = Service.objects.create(ship=self.navire, name="Vie", commandant_adjoint=comaeq)
        comaeq.delete()
        service.refresh_from_db()
        self.assertIsNone(service.commandant_adjoint)

    def test_capacite_aviation_faux_par_defaut(self):
        self.assertFalse(self.navire.capacite_aviation)


class OngletCommandantsAdjointsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("settings")
        self.ship = Ship.objects.create(name="BRF Onglet", code="BRF-O")
        self.autre_ship = Ship.objects.create(name="FREMM Onglet", code="FRM-O")
        self.service = Service.objects.create(ship=self.ship, name="Machine")
        self.service_autre = Service.objects.create(ship=self.autre_ship, name="Machine autre")

    def _marin(self, username, role, ship=None):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship or self.ship})
        return user

    def _connecte(self, username, role, ship=None):
        user = self._marin(username, role, ship)
        self.client.login(username=username, password="pass")
        return user

    def _post(self, action, **donnees):
        return self.client.post(self.url, {"action": action, **donnees})

    def test_role_inferieur_au_seuil_refuse(self):
        self._connecte("chef_service", "CHEF_SERVICE")
        self.assertEqual(self.client.get(self.url, {"tab": "commandants_adjoints"}).status_code, 403)
        self.assertEqual(self._post("add_commandant_adjoint", sigle="COMAEQ").status_code, 403)
        self.assertFalse(CommandantAdjoint.objects.exists())

    def test_etat_major_refuse_par_defaut(self):
        self._connecte("etat_major", "ETAT_MAJOR")
        self.assertEqual(self._post("add_commandant_adjoint", sigle="COMAEQ").status_code, 403)

    def test_commandant_ajoute_un_poste_sur_son_navire_avec_audit(self):
        self._connecte("commandant", "COMMANDANT")
        reponse = self.client.get(self.url, {"tab": "commandants_adjoints"})
        self.assertEqual(reponse.status_code, 200)
        self._post("add_commandant_adjoint", sigle="COMAEQ", ship_id=self.autre_ship.id)
        self.assertTrue(CommandantAdjoint.objects.filter(ship=self.ship, sigle="COMAEQ").exists())
        self.assertFalse(CommandantAdjoint.objects.filter(ship=self.autre_ship).exists())
        self.assertTrue(AuditLog.objects.filter(action="add_commandant_adjoint", details__contains="COMAEQ").exists())

    def test_comavia_refuse_sans_capacite_aviation_puis_accepte(self):
        self._connecte("admin_navire", "ADMIN_NAVIRE")
        self._post("add_commandant_adjoint", sigle="COMAVIA")
        self.assertFalse(CommandantAdjoint.objects.filter(sigle="COMAVIA").exists())
        self._post("toggle_capacite_aviation")
        self.ship.refresh_from_db()
        self.assertTrue(self.ship.capacite_aviation)
        self._post("add_commandant_adjoint", sigle="COMAVIA")
        self.assertTrue(CommandantAdjoint.objects.filter(ship=self.ship, sigle="COMAVIA").exists())
        # Retrait de la capacité aviation refusé tant que le COMAVIA existe.
        self._post("toggle_capacite_aviation")
        self.ship.refresh_from_db()
        self.assertTrue(self.ship.capacite_aviation)

    def test_titulaire_doit_etre_etat_major_du_navire(self):
        self._connecte("commandant", "COMMANDANT")
        poste = CommandantAdjoint.objects.create(ship=self.ship, sigle="COMANAV")
        equipier = self._marin("equipier", "EQUIPIER")
        etat_major_autre = self._marin("em_autre", "ETAT_MAJOR", self.autre_ship)
        etat_major = self._marin("em", "ETAT_MAJOR")
        for refuse in (equipier, etat_major_autre):
            self._post("set_titulaire_commandant_adjoint", pk=poste.id, user_id=refuse.id)
            poste.refresh_from_db()
            self.assertIsNone(poste.titulaire)
        self._post("set_titulaire_commandant_adjoint", pk=poste.id, user_id=etat_major.id)
        poste.refresh_from_db()
        self.assertEqual(poste.titulaire, etat_major)
        self.assertTrue(AuditLog.objects.filter(action="set_titulaire_commandant_adjoint").exists())

    def test_rattachement_service_limite_au_navire(self):
        self._connecte("commandant", "COMMANDANT")
        poste = CommandantAdjoint.objects.create(ship=self.ship, sigle="COMANAV")
        poste_autre = CommandantAdjoint.objects.create(ship=self.autre_ship, sigle="COMANAV")
        self._post("set_service_commandant_adjoint", service_id=self.service.id, coma_id=poste_autre.id)
        self.service.refresh_from_db()
        self.assertIsNone(self.service.commandant_adjoint)
        self._post("set_service_commandant_adjoint", service_id=self.service_autre.id, coma_id=poste.id)
        self.service_autre.refresh_from_db()
        self.assertIsNone(self.service_autre.commandant_adjoint)
        self._post("set_service_commandant_adjoint", service_id=self.service.id, coma_id=poste.id)
        self.service.refresh_from_db()
        self.assertEqual(self.service.commandant_adjoint, poste)
        self._post("set_service_commandant_adjoint", service_id=self.service.id, coma_id="")
        self.service.refresh_from_db()
        self.assertIsNone(self.service.commandant_adjoint)
        self.assertEqual(AuditLog.objects.filter(action="set_service_commandant_adjoint").count(), 2)

    def test_suppression_ne_touche_pas_un_autre_navire(self):
        self._connecte("commandant", "COMMANDANT")
        poste_autre = CommandantAdjoint.objects.create(ship=self.autre_ship, sigle="COMOPS")
        self._post("delete_commandant_adjoint", pk=poste_autre.id)
        self.assertTrue(CommandantAdjoint.objects.filter(pk=poste_autre.id).exists())

    def test_sigles_affiches_sans_jargon_interdit(self):
        self._connecte("commandant", "COMMANDANT")
        CommandantAdjoint.objects.create(ship=self.ship, sigle="COMANAV")
        contenu = self.client.get(self.url, {"tab": "commandants_adjoints"}).content.decode()
        self.assertIn("COMANAV", contenu)
        self.assertNotIn("chef de groupement", contenu.lower())
        self.assertNotRegex(contenu, r"CAN")

    def test_aucun_commandant_adjoint_nu_dans_la_page(self):
        """« Commandant adjoint » ne s'affiche jamais seul : uniquement suivi
        de sa précision (équipage, opérations, navire, aviation) à côté du sigle."""
        import re
        self._connecte("commandant", "COMMANDANT")
        self.ship.capacite_aviation = True
        self.ship.save()
        for sigle in ("COMAEQ", "COMOPS", "COMANAV", "COMAVIA"):
            CommandantAdjoint.objects.create(ship=self.ship, sigle=sigle)
        contenu = self.client.get(self.url, {"tab": "commandants_adjoints"}).content.decode()
        nus = re.findall(
            r"commandants? adjoints?(?!\s+(?:équipage|opérations|navire|aviation|\(COMA))",
            contenu, flags=re.IGNORECASE,
        )
        self.assertEqual(nus, [])

    def test_superuser_choisit_le_navire(self):
        User.objects.create_superuser(username="root", password="pass", email="r@r.fr")
        self.client.login(username="root", password="pass")
        self._post("add_commandant_adjoint", sigle="COMOPS", ship_id=self.autre_ship.id)
        self.assertTrue(CommandantAdjoint.objects.filter(ship=self.autre_ship, sigle="COMOPS").exists())


class ServiceSerializerCommandantAdjointTests(TestCase):
    def test_commandant_adjoint_d_un_autre_navire_refuse(self):
        from org.serializers import ServiceSerializer
        navire = Ship.objects.create(name="A", code="A")
        autre = Ship.objects.create(name="B", code="B")
        poste = CommandantAdjoint.objects.create(ship=autre, sigle="COMOPS")
        serializer = ServiceSerializer(data={"ship": navire.id, "name": "SIC", "commandant_adjoint": poste.id})
        self.assertFalse(serializer.is_valid())
        self.assertIn("commandant_adjoint", serializer.errors)
