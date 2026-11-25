"""AC-15, AC-20 : gouvernance de l'administrateur général, superutilisateur Django distinct, catalogue de formations."""
import json

from django.contrib.auth import get_user_model

from accounts.models import UserProfile
from org.models import ModuleActivation, Ship
from training.models import TrainingCourse, TrainingRequirement

from .outils import MondeFictif

User = get_user_model()


class GouvernanceTests(MondeFictif):
    def setUp(self):
        self.general_seul = User.objects.create_user(username="general_seul", password="pass")
        UserProfile.objects.filter(user=self.general_seul).update(administrateur_general=True)
        self.general_commandant = User.objects.create_user(username="general_commandant", password="pass")
        UserProfile.objects.filter(user=self.general_commandant).update(
            administrateur_general=True, role="COMMANDANT", ship=self.navire)
        self.superutilisateur = User.objects.create_superuser("superutilisateur", password="pass", email="s@s.fr")

    def _poster(self, nom, donnees, url="/parametre/"):
        from django.test import Client
        client = Client()
        client.force_login(User.objects.get(username=nom))
        return client.post(url, donnees)

    def test_gouvernance_conservee_par_l_administrateur_general_sans_fonction(self):
        reponse = self._poster("general_seul", {"action": "add_ship", "name": "Unité neuve", "code": "NEU", "fuseau_horaire": "Europe/Paris"})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Ship.objects.filter(code="NEU").exists())
        api = self.client_de("general_seul")
        self.assertEqual(api.post("/api/org/ships/", data=json.dumps({"name": "Autre", "code": "AUT", "type_unite": "NAVIRE", "fuseau_horaire": "Europe/Paris"}),
                                  content_type="application/json").status_code, 201)

    def test_actes_metier_refuses_a_l_administrateur_general_sans_fonction(self):
        refus = self._poster("general_seul", {"action": "toggle_module", "cle_module": "logistics", "ship_id": self.navire.pk})
        self.assertEqual(refus.status_code, 403)
        self.assertFalse(ModuleActivation.objects.filter(ship=self.navire, module="logistics", active=False).exists())
        self.assertEqual(self.client_de("general_seul").get("/dashboard/comanav/").status_code, 403)
        passation = self.client_de("general_seul").get(f"/dashboard/passation/{self.synthese.pk}/")
        self.assertIn(passation.status_code, (302, 403, 404))

    def test_cumul_explicite_la_fonction_metier_attribuee_s_exerce_dans_son_perimetre(self):
        reponse = self._poster("general_commandant", {"action": "toggle_module", "cle_module": "logistics"})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(ModuleActivation.objects.filter(ship=self.navire, module="logistics", active=False).exists())
        # Le cumul ne donne pas plus : la fonction reste celle de commandant du bâtiment.
        self.assertEqual(self._poster("general_commandant", {"action": "toggle_module", "cle_module": "logistics", "ship_id": self.autre_navire.pk}).status_code, 302)
        self.assertFalse(ModuleActivation.objects.filter(ship=self.autre_navire).exists())

    def test_superutilisateur_django_sans_fonction_applicative(self):
        # Ni gouvernance, ni fonction métier dans les interfaces ordinaires ; l'administration Django reste son outil.
        self.assertEqual(self._poster("superutilisateur", {"action": "add_ship", "name": "X", "code": "SUX", "fuseau_horaire": "Europe/Paris"}).status_code, 403)
        self.assertFalse(Ship.objects.filter(code="SUX").exists())
        self.assertEqual(self.client_de("superutilisateur").get("/users/").status_code, 403)
        self.assertEqual(self.client_de("superutilisateur").post("/api/org/ships/", data="{}", content_type="application/json").status_code, 403)
        self.assertEqual(self.client_de("superutilisateur").get("/admin/").status_code, 200)

    def test_l_administrateur_general_designe_le_commandement_mais_pas_les_autres_autorites(self):
        client = self.client_de("general_seul")
        cible = self.equipier_b1
        patch = lambda role: client.patch(  # noqa: E731
            f"/api/accounts/profiles/{cible.profile.pk}/", data=json.dumps({"role": role}), content_type="application/json")
        self.assertEqual(patch("COMMANDANT_EN_SECOND").status_code, 200)
        self.assertEqual(patch("COMMANDANT").status_code, 200)
        self.assertEqual(patch("CHEF_SERVICE").status_code, 403)
        self.assertEqual(patch("ETAT_MAJOR").status_code, 403)
        self.assertEqual(UserProfile.objects.get(user=cible).role, "COMMANDANT")


class CatalogueFormationsTests(MondeFictif):
    def setUp(self):
        self.general = User.objects.create_user(username="general_form", password="pass")
        UserProfile.objects.filter(user=self.general).update(administrateur_general=True)

    def _api(self, nom, methode, url, donnees=None):
        client = self.client_de(nom)
        return getattr(client, methode)(url, data=json.dumps(donnees or {}), content_type="application/json")

    def test_le_referentiel_commun_n_est_modifiable_que_par_l_administrateur_general(self):
        for nom in ("admin_navire", "bsc_admin", "cdt_admin", "cdt_b", "second_b", "chef_service_b"):
            reponse = self._api(nom, "post", "/api/training/courses/", {"title": f"Pirate {nom}", "validity_days": 10})
            self.assertEqual(reponse.status_code, 403, nom)
            web = self.client_de(nom).post("/formations/", {"action": "create_course", "title": f"Pirate web {nom}"})
            self.assertEqual(web.status_code, 403, nom)
        self.assertFalse(TrainingCourse.objects.filter(title__startswith="Pirate").exists())
        ok = self._api("general_form", "post", "/api/training/courses/", {"title": "Catalogue commun", "validity_days": 10})
        self.assertEqual(ok.status_code, 201)
        cours = TrainingCourse.objects.get(title="Catalogue commun")
        self.assertEqual(self._api("admin_navire", "patch", f"/api/training/courses/{cours.pk}/", {"title": "Piraté"}).status_code, 403)
        self.assertEqual(self._api("admin_navire", "delete", f"/api/training/courses/{cours.pk}/").status_code, 403)
        self.assertEqual(self._api("general_form", "patch", f"/api/training/courses/{cours.pk}/", {"title": "Renommé"}).status_code, 200)
        cours.refresh_from_db()
        self.assertEqual(cours.title, "Renommé")

    def test_exigences_communes_administrateur_general_et_locales_commandement(self):
        cours = TrainingCourse.objects.create(title="Cours", validity_days=30)
        commune = {"course": cours.pk, "applies_to_role": "EQUIPIER"}
        locale = {"course": cours.pk, "applies_to_role": "EQUIPIER", "applies_to_ship": self.navire.pk}
        for nom in ("admin_navire", "cdt_b", "chef_service_b"):
            self.assertEqual(self._api(nom, "post", "/api/training/requirements/", commune).status_code, 403, nom)
        self.assertEqual(self._api("general_form", "post", "/api/training/requirements/", commune).status_code, 201)
        self.assertEqual(self._api("general_form", "post", "/api/training/requirements/", locale).status_code, 403)
        self.assertEqual(self._api("admin_navire", "post", "/api/training/requirements/", locale).status_code, 403)
        self.assertEqual(self._api("chef_service_b", "post", "/api/training/requirements/", locale).status_code, 403)
        self.assertEqual(self._api("cdt_b", "post", "/api/training/requirements/", locale).status_code, 201)
        self.assertEqual(self._api("cdt_abe", "post", "/api/training/requirements/", locale).status_code, 403)  # autre bâtiment
        self.assertEqual(TrainingRequirement.objects.count(), 2)

    def test_l_administrateur_technique_garde_l_administration_technique_du_module(self):
        # Le module reste lisible et son administration technique inchangée ; seule l'écriture du référentiel commun disparaît.
        self.assertEqual(self.client_de("admin_navire").get("/formations/").status_code, 200)
