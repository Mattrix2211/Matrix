"""Droits d'écriture des API et écrans de structure, de formation et de quarts :
un grade élevé ne sort jamais de son bâtiment, un chef ne s'attribue pas de droit
de validation et les suppressions destructrices sont refusées ou tracées.
Comptes et données de seed_demo (Bretagne à double équipage A/B, Normandie)."""
from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AuditLog
from assets.models import Location
from matrix.core.role_thresholds import invalidate_cache
from org.models import RoleThresholdConfig, Sector, Section, Service, Ship
from quarts.models import ChefDeListe, Quart
from training.models import ReferentFormation, TrainingCourse, TrainingRecord, TrainingSession

# Tous les comptes de seed_demo qui n'ont pas le droit de modifier la structure.
SANS_DROIT_STRUCTURE = [
    "equipier_a", "marin_b", "chef_section_a", "chef_secteur_a", "chef_secteur_b", "chef_service_a",
    "coma_comanav", "coma_comaeq", "second_a", "cdt_a", "cdt_b", "terre_classe", "terre_securite",
    "equipier_nor", "chef_secteur_nor", "cdt_nor",
]


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.bre = Ship.objects.get(code="BRE")
        cls.nor = Ship.objects.get(code="NOR")
        cls.section_bre = Section.objects.get(sector__service__ship=cls.bre, name="Pompes")
        cls.secteur_bre = Sector.objects.get(service__ship=cls.bre, name="Moteurs")
        cls.service_bre = Service.objects.get(ship=cls.bre, name="Propulsion")
        cls.service_nor = Service.objects.get(ship=cls.nor, name="Propulsion")
        cls.lieu_bre = Location.objects.get(ship=cls.bre, name="Local machine")
        cls.lieu_nor = Location.objects.get(ship=cls.nor, name="Local machine")

    def appel(self, compte, methode, url, donnees=None):
        client = APIClient()
        client.force_login(User.objects.get(username=compte))
        return getattr(client, methode)(url, donnees, format="json")

    def traces(self, prefixe):
        return AuditLog.objects.filter(action__startswith=prefixe).count()

    def seuil(self, cle, role, navire):
        RoleThresholdConfig.objects.update_or_create(ship=navire, defaults={"thresholds": {cle: role}})
        invalidate_cache(navire.id)
        self.addCleanup(invalidate_cache, navire.id)


class StructureBatimentTests(Base):
    """F1 : la structure du bâtiment ne se modifie que par l'administration de l'unité."""

    def etat_structure(self):
        return (
            list(Ship.objects.order_by("pk").values_list("pk", "name", "archived", "double_equipage", "equipage_a_bord")),
            list(Service.objects.order_by("pk").values_list("pk", "name", "archived")),
            list(Sector.objects.order_by("pk").values_list("pk", "name", "archived")),
            list(Section.objects.order_by("pk").values_list("pk", "name", "archived")),
            list(Location.objects.order_by("pk").values_list("pk", "name", "parent_id")),
        )

    def requetes_interdites(self):
        return [
            ("patch", f"/api/org/ships/{self.bre.pk}/", {"archived": True}),
            ("patch", f"/api/org/ships/{self.bre.pk}/", {"name": "Pirate"}),
            ("patch", f"/api/org/ships/{self.bre.pk}/", {"double_equipage": False}),
            ("delete", f"/api/org/ships/{self.bre.pk}/", None),
            ("post", "/api/org/services/", {"ship": self.bre.pk, "name": "Intrus"}),
            ("patch", f"/api/org/services/{self.service_bre.pk}/", {"name": "Renommé"}),
            ("delete", f"/api/org/services/{self.service_bre.pk}/", None),
            ("post", "/api/org/sectors/", {"service": self.service_bre.pk, "name": "Intrus"}),
            ("patch", f"/api/org/sectors/{self.secteur_bre.pk}/", {"archived": True}),
            ("delete", f"/api/org/sectors/{self.secteur_bre.pk}/", None),
            ("post", "/api/org/sections/", {"sector": self.secteur_bre.pk, "name": "Intrus"}),
            ("patch", f"/api/org/sections/{self.section_bre.pk}/", {"name": "Renommée"}),
            ("delete", f"/api/org/sections/{self.section_bre.pk}/", None),
            ("post", "/api/assets/locations/", {"ship": self.bre.pk, "name": "Intrus"}),
            ("patch", f"/api/assets/locations/{self.lieu_bre.pk}/", {"name": "Renommé"}),
            ("delete", f"/api/assets/locations/{self.lieu_bre.pk}/", None),
        ]

    def test_aucun_compte_sans_droit_ne_modifie_la_structure(self):
        avant, traces = self.etat_structure(), self.traces("org.")
        for compte in SANS_DROIT_STRUCTURE:
            for methode, url, donnees in self.requetes_interdites():
                reponse = self.appel(compte, methode, url, donnees)
                self.assertIn(reponse.status_code, (403, 404), f"{compte} {methode} {url} -> {reponse.status_code}")
        self.assertEqual(self.etat_structure(), avant)
        self.assertEqual(self.traces("org."), traces)

    def test_rapport_f1_chef_de_section_ne_peut_ni_archiver_ni_supprimer(self):
        self.assertEqual(self.appel("chef_section_a", "patch", f"/api/org/ships/{self.bre.pk}/", {"archived": True}).status_code, 403)
        self.assertEqual(self.appel("chef_section_a", "delete", f"/api/org/sections/{self.section_bre.pk}/").status_code, 403)
        self.assertEqual(self.appel("chef_section_a", "delete", f"/api/assets/locations/{self.lieu_bre.pk}/").status_code, 403)
        self.bre.refresh_from_db()
        self.assertFalse(self.bre.archived)
        self.assertTrue(Section.objects.filter(pk=self.section_bre.pk).exists())

    def test_lecture_de_la_structure_reste_ouverte_au_batiment(self):
        reponse = self.appel("equipier_a", "get", "/api/org/sections/")
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(all(s["sector"] in {x.pk for x in Sector.objects.filter(service__ship=self.bre)} for s in reponse.json()))

    def test_admin_navire_modifie_sa_structure_avec_trace(self):
        reponse = self.appel("admin_navire", "patch", f"/api/org/sections/{self.section_bre.pk}/", {"name": "Pompes de cale"})
        self.assertEqual(reponse.status_code, 200)
        self.section_bre.refresh_from_db()
        self.assertEqual(self.section_bre.name, "Pompes de cale")
        trace = AuditLog.objects.get(action="org.modification")
        self.assertIn("Pompes de cale", trace.details)
        self.assertEqual(trace.actor.username, "admin_navire")

    def test_admin_navire_cree_et_supprime_avec_trace(self):
        cree = self.appel("admin_navire", "post", "/api/org/sections/", {"sector": self.secteur_bre.pk, "name": "Nouvelle"})
        self.assertEqual(cree.status_code, 201)
        self.assertEqual(self.appel("admin_navire", "delete", f"/api/org/sections/{cree.json()['id']}/").status_code, 204)
        self.assertEqual(
            list(AuditLog.objects.filter(action__startswith="org.").order_by("pk").values_list("action", flat=True)),
            ["org.creation", "org.suppression"],
        )

    def test_suppression_d_une_section_trace_les_marins_rattaches(self):
        section = Section.objects.get(sector__service__ship=self.bre, name="Moteurs bâbord")
        self.assertEqual(self.appel("admin_navire", "delete", f"/api/org/sections/{section.pk}/").status_code, 204)
        self.assertIn("marins rattachés: 4", AuditLog.objects.get(action="org.suppression").details)

    def test_admin_navire_ne_touche_pas_a_l_autre_batiment(self):
        avant = self.etat_structure()
        for methode, url, donnees in [
            ("patch", f"/api/org/ships/{self.nor.pk}/", {"archived": True}),
            ("patch", f"/api/org/services/{self.service_nor.pk}/", {"name": "X"}),
            ("delete", f"/api/org/services/{self.service_nor.pk}/", None),
            ("post", "/api/org/services/", {"ship": self.nor.pk, "name": "Intrus"}),
            ("patch", f"/api/assets/locations/{self.lieu_nor.pk}/", {"name": "X"}),
            ("delete", f"/api/assets/locations/{self.lieu_nor.pk}/", None),
        ]:
            self.assertIn(self.appel("admin_navire", methode, url, donnees).status_code, (400, 403, 404), url)
        self.assertEqual(self.etat_structure(), avant)

    def test_administrateur_general_agit_sur_toute_la_flotte(self):
        self.assertEqual(self.appel("admin", "patch", f"/api/org/services/{self.service_nor.pk}/", {"name": "Propulsion NOR"}).status_code, 200)
        self.assertEqual(self.appel("admin", "delete", f"/api/assets/locations/{self.lieu_nor.pk}/").status_code, 204)

    def test_seuil_configurable_par_unite(self):
        self.seuil("structure_navire_ecriture", "CHEF_SERVICE", self.bre)
        self.assertEqual(self.appel("chef_service_a", "patch", f"/api/org/sections/{self.section_bre.pk}/", {"name": "Reconfigurée"}).status_code, 200)
        self.assertEqual(self.appel("chef_section_a", "patch", f"/api/org/sections/{self.section_bre.pk}/", {"name": "Non"}).status_code, 403)

    def test_double_equipage_bascule_explicite_et_sans_droit_accidentel(self):
        url = f"/api/org/ships/{self.bre.pk}/"
        # Commandant et chef : refusés.
        for compte in ("cdt_a", "chef_service_a"):
            self.assertEqual(self.appel(compte, "patch", url, {"double_equipage": False}).status_code, 403)
        # L'équipage à bord ne change que par la relève.
        self.assertEqual(self.appel("admin_navire", "patch", url, {"equipage_a_bord": "B"}).status_code, 403)
        # L'équipage B (à terre) retrouverait l'écriture : refus tant qu'il est rattaché.
        refus = self.appel("admin_navire", "patch", url, {"double_equipage": False})
        self.assertEqual(refus.status_code, 400)
        self.bre.refresh_from_db()
        self.assertTrue(self.bre.double_equipage)
        self.assertEqual(self.traces("changement_equipage"), 0)
        # Une fois l'équipage à terre vidé, la bascule passe et elle est tracée.
        for marin in User.objects.filter(profile__ship=self.bre, profile__equipage="B"):
            marin.profile.equipage = ""
            marin.profile.save()
        self.assertEqual(self.appel("admin_navire", "patch", url, {"double_equipage": False}).status_code, 200)
        self.assertEqual(self.traces("changement_equipage"), 1)

    def test_activation_du_double_equipage_exige_un_equipage_a_bord(self):
        reponse = self.appel("admin", "patch", f"/api/org/ships/{self.nor.pk}/", {"double_equipage": True})
        self.assertEqual(reponse.status_code, 400)
        self.nor.refresh_from_db()
        self.assertFalse(self.nor.double_equipage)

    def test_amenagements_de_l_equipage_a_terre_restent_en_lecture_seule(self):
        self.assertEqual(self.appel("chef_secteur_b", "patch", f"/api/org/sections/{self.section_bre.pk}/", {"name": "X"}).status_code, 403)
        self.assertEqual(self.appel("chef_secteur_b", "delete", f"/api/org/sections/{self.section_bre.pk}/").status_code, 403)


class FormationTests(Base):
    """F2 et F3 : référents formation et validations."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cours = TrainingCourse.objects.get(title="Lutte contre l'incendie")
        cls.autre_cours = TrainingCourse.objects.exclude(pk=cls.cours.pk).first()
        cls.equipier = User.objects.get(username="equipier_a")

    def test_rapport_f2_un_chef_ne_se_designe_pas_referent(self):
        chef = User.objects.get(username="chef_section_a")
        avant = ReferentFormation.objects.count()
        reponse = self.appel("chef_section_a", "post", "/api/training/referents/", {"course": self.cours.pk, "ship": self.bre.pk, "user": chef.pk})
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(ReferentFormation.objects.count(), avant)
        self.assertEqual(self.traces("training."), 0)

    def test_aucun_sous_commandement_ne_designe_de_referent(self):
        cible = User.objects.get(username="equipier_a2")
        for compte in ("equipier_a", "chef_section_a", "chef_secteur_a", "chef_service_a", "coma_comanav", "second_a", "cdt_b", "terre_classe"):
            reponse = self.appel(compte, "post", "/api/training/referents/", {"course": self.cours.pk, "ship": self.bre.pk, "user": cible.pk})
            self.assertEqual(reponse.status_code, 403, compte)
        self.assertFalse(ReferentFormation.objects.filter(user=cible).exists())

    def test_un_referent_ne_se_designe_pas_lui_meme_ni_un_autre_referent(self):
        # chef_secteur_a est référent de la formation d'incendie dans la démo.
        reponse = self.appel("chef_secteur_a", "post", "/api/training/referents/", {"course": self.autre_cours.pk, "ship": self.bre.pk, "user": User.objects.get(username="chef_secteur_a").pk})
        self.assertEqual(reponse.status_code, 403)

    def test_le_commandant_designe_un_referent_de_son_batiment_avec_trace(self):
        reponse = self.appel("cdt_a", "post", "/api/training/referents/", {"course": self.cours.pk, "ship": self.bre.pk, "user": self.equipier.pk})
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(self.traces("training.creation"), 1)
        # Le référent valide ensuite un marin de son bâtiment.
        valide = self.appel("equipier_a", "post", "/api/training/records/", {
            "user": User.objects.get(username="equipier_a2").pk, "course": self.cours.pk,
            "completed_at": "2026-01-10", "expires_at": "2027-01-10",
        })
        self.assertEqual(valide.status_code, 201)
        self.assertEqual(self.traces("training.creation"), 2)

    def test_pas_de_referent_sur_un_marin_d_un_autre_batiment(self):
        reponse = self.appel("cdt_a", "post", "/api/training/referents/", {"course": self.cours.pk, "ship": self.bre.pk, "user": User.objects.get(username="equipier_nor").pk})
        self.assertEqual(reponse.status_code, 400)

    def test_rapport_f3_un_commandant_ne_designe_pas_de_referent_sur_l_autre_batiment(self):
        avant = ReferentFormation.objects.count()
        for cible, navire in (("equipier_a", self.bre), ("equipier_nor", self.bre), ("equipier_a", self.nor)):
            reponse = self.appel("cdt_nor", "post", "/api/training/referents/", {
                "course": self.cours.pk, "ship": navire.pk, "user": User.objects.get(username=cible).pk})
            self.assertIn(reponse.status_code, (400, 403), (cible, navire))
        self.assertEqual(ReferentFormation.objects.count(), avant)

    def test_le_commandant_normandie_designe_chez_lui(self):
        reponse = self.appel("cdt_nor", "post", "/api/training/referents/", {
            "course": self.cours.pk, "ship": self.nor.pk, "user": User.objects.get(username="equipier_nor").pk})
        self.assertEqual(reponse.status_code, 201)

    def test_un_commandant_ne_voit_ni_ne_retire_les_referents_de_l_autre_batiment(self):
        referent = ReferentFormation.objects.get(ship=self.bre)
        liste = self.appel("cdt_nor", "get", "/api/training/referents/").json()
        self.assertNotIn(referent.pk, [r["id"] for r in liste])
        self.assertEqual(self.appel("cdt_nor", "delete", f"/api/training/referents/{referent.pk}/").status_code, 404)
        self.assertTrue(ReferentFormation.objects.filter(pk=referent.pk).exists())

    def test_retrait_et_modification_des_referents(self):
        referent = ReferentFormation.objects.get(ship=self.bre)
        self.assertEqual(self.appel("chef_service_a", "delete", f"/api/training/referents/{referent.pk}/").status_code, 403)
        self.assertEqual(self.appel("chef_secteur_a", "patch", f"/api/training/referents/{referent.pk}/", {"user": self.equipier.pk}).status_code, 403)
        self.assertEqual(self.appel("cdt_a", "delete", f"/api/training/referents/{referent.pk}/").status_code, 204)
        self.assertEqual(self.traces("training.suppression"), 1)

    def test_validation_refusee_a_un_chef_non_referent_et_au_commandant_voisin(self):
        avant = TrainingRecord.objects.count()
        donnees = {"user": self.equipier.pk, "course": self.autre_cours.pk, "completed_at": "2026-01-10", "expires_at": "2027-01-10"}
        for compte in ("chef_section_a", "chef_service_a", "second_a", "coma_comanav", "cdt_nor", "terre_classe"):
            self.assertEqual(self.appel(compte, "post", "/api/training/records/", donnees).status_code, 403, compte)
        self.assertEqual(TrainingRecord.objects.count(), avant)

    def test_commandant_et_administrateur_valident_leur_batiment(self):
        donnees = {"user": self.equipier.pk, "course": self.autre_cours.pk, "completed_at": "2026-01-10", "expires_at": "2027-01-10"}
        self.assertEqual(self.appel("cdt_a", "post", "/api/training/records/", donnees).status_code, 201)

    def test_referent_designe_valide_son_marin_par_le_web(self):
        """Parcours de la démo : le référent (chef_secteur_a) valide via l'écran."""
        self.client.force_login(User.objects.get(username="chef_secteur_a"))
        avant = TrainingRecord.objects.filter(course=self.cours, user=self.equipier).count()
        reponse = self.client.post("/formations/valider/", {
            "marin_id": self.equipier.pk, "course_id": self.cours.pk, "completed_at": date.today().isoformat()})
        self.assertIn(reponse.status_code, (200, 302))
        self.assertEqual(TrainingRecord.objects.filter(course=self.cours, user=self.equipier).count(), avant + 1)

    def test_commandant_voisin_ne_valide_pas_par_le_web(self):
        self.client.force_login(User.objects.get(username="cdt_nor"))
        avant = TrainingRecord.objects.count()
        self.client.post("/formations/valider/", {
            "marin_id": self.equipier.pk, "course_id": self.cours.pk, "completed_at": date.today().isoformat()})
        self.assertEqual(TrainingRecord.objects.count(), avant)

    def test_web_un_chef_de_section_ne_designe_pas_de_referent(self):
        self.client.force_login(User.objects.get(username="chef_section_a"))
        chef = User.objects.get(username="chef_section_a")
        avant = list(ReferentFormation.objects.order_by("pk").values_list("pk", flat=True))
        reponse = self.client.post("/formations/", {"action": "update_prerequisites", "pk": self.autre_cours.pk, "referents": [chef.pk]})
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(list(ReferentFormation.objects.order_by("pk").values_list("pk", flat=True)), avant)

    def test_web_le_commandant_designe_mais_jamais_lui_meme(self):
        self.client.force_login(User.objects.get(username="cdt_a"))
        cdt = User.objects.get(username="cdt_a")
        self.client.post("/formations/", {"action": "update_prerequisites", "pk": self.autre_cours.pk, "referents": [cdt.pk, self.equipier.pk]})
        self.assertEqual(
            list(ReferentFormation.objects.filter(course=self.autre_cours, ship=self.bre).values_list("user__username", flat=True)),
            ["equipier_a"],
        )
        self.assertEqual(self.traces("training.referents"), 1)

    def test_suppression_de_formation_et_de_session(self):
        # Formation utilisée (validations) : jamais supprimée, même par l'administration.
        utilisee = TrainingRecord.objects.first().course
        nb = TrainingRecord.objects.count()
        self.assertEqual(self.appel("chef_section_a", "delete", f"/api/training/courses/{utilisee.pk}/").status_code, 403)
        self.assertEqual(self.appel("admin_navire", "delete", f"/api/training/courses/{utilisee.pk}/").status_code, 400)
        self.assertEqual(self.appel("admin", "delete", f"/api/training/courses/{utilisee.pk}/").status_code, 400)
        self.assertEqual(TrainingRecord.objects.count(), nb)
        # Formation vierge : l'administration la supprime, avec trace.
        vierge = TrainingCourse.objects.create(title="Vierge", category="Test")
        self.assertEqual(self.appel("admin_navire", "delete", f"/api/training/courses/{vierge.pk}/").status_code, 204)
        self.assertEqual(self.traces("training.suppression"), 1)

    def test_creation_de_formation_reservee_a_l_administration(self):
        self.assertEqual(self.appel("chef_section_a", "post", "/api/training/courses/", {"title": "Pirate", "validity_days": 10}).status_code, 403)
        self.assertEqual(self.appel("cdt_a", "post", "/api/training/courses/", {"title": "Pirate", "validity_days": 10}).status_code, 403)
        self.assertEqual(self.appel("admin_navire", "post", "/api/training/courses/", {"title": "Légitime", "validity_days": 10}).status_code, 201)

    def test_session_avec_presences_non_supprimable(self):
        session = TrainingSession.objects.filter(attendees__isnull=False).first()
        if session is None:
            session = TrainingSession.objects.first()
            session.attendees.add(self.equipier)
        self.assertEqual(self.appel("admin", "delete", f"/api/training/sessions/{session.pk}/").status_code, 400)
        self.assertTrue(TrainingSession.objects.filter(pk=session.pk).exists())

    def test_exigence_de_formation_hors_batiment_refusee_au_commandant(self):
        reponse = self.appel("cdt_nor", "post", "/api/training/requirements/", {"course": self.cours.pk, "applies_to_ship": self.bre.pk})
        self.assertEqual(reponse.status_code, 403)
        reponse = self.appel("cdt_nor", "post", "/api/training/requirements/", {"course": self.cours.pk})
        self.assertEqual(reponse.status_code, 403)
        reponse = self.appel("cdt_nor", "post", "/api/training/requirements/", {"course": self.cours.pk, "applies_to_ship": self.nor.pk})
        self.assertEqual(reponse.status_code, 201)


class ListesDeQuartsTests(Base):
    """F3 : un commandant n'administre pas les listes d'un autre bâtiment."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.brouillon = Quart.objects.get(nom="Quarts machine — semaine prochaine")

    def poster(self, compte, url, donnees):
        self.client.force_login(User.objects.get(username=compte))
        return self.client.post(url, donnees)

    def test_rapport_f3_cdt_nor_ne_propose_ni_ne_publie_une_liste_bretagne(self):
        url = f"/quarts/quart/{self.brouillon.pk}/"
        self.poster("cdt_nor", url, {"action": "proposer"})
        self.brouillon.refresh_from_db()
        self.assertEqual(self.brouillon.statut, Quart.STATUT_BROUILLON)
        Quart.objects.filter(pk=self.brouillon.pk).update(statut=Quart.STATUT_PROPOSEE)
        self.poster("cdt_nor", url, {"action": "publier"})
        self.brouillon.refresh_from_db()
        self.assertEqual(self.brouillon.statut, Quart.STATUT_PROPOSEE)

    def test_le_commandant_du_batiment_publie(self):
        Quart.objects.filter(pk=self.brouillon.pk).update(statut=Quart.STATUT_PROPOSEE)
        self.poster("cdt_a", f"/quarts/quart/{self.brouillon.pk}/", {"action": "publier"})
        self.brouillon.refresh_from_db()
        self.assertEqual(self.brouillon.statut, Quart.STATUT_PUBLIEE)

    def test_parcours_chef_de_liste_puis_chef_de_service(self):
        url = f"/quarts/quart/{self.brouillon.pk}/"
        self.poster("chef_secteur_a", url, {"action": "proposer"})
        self.brouillon.refresh_from_db()
        self.assertEqual(self.brouillon.statut, Quart.STATUT_PROPOSEE)
        self.poster("chef_service_a", url, {"action": "publier"})
        self.brouillon.refresh_from_db()
        self.assertEqual(self.brouillon.statut, Quart.STATUT_PUBLIEE)

    def test_chef_de_section_et_equipier_ne_publient_pas(self):
        Quart.objects.filter(pk=self.brouillon.pk).update(statut=Quart.STATUT_PROPOSEE)
        for compte in ("chef_section_a", "equipier_a", "second_a", "terre_classe"):
            self.poster(compte, f"/quarts/quart/{self.brouillon.pk}/", {"action": "publier"})
        self.brouillon.refresh_from_db()
        self.assertEqual(self.brouillon.statut, Quart.STATUT_PROPOSEE)

    def test_cdt_nor_ne_cree_pas_de_liste_sur_la_bretagne(self):
        avant = Quart.objects.count()
        for perimetre in (f"ship:{self.bre.pk}", f"service:{self.service_bre.pk}", f"sector:{self.secteur_bre.pk}"):
            reponse = self.poster("cdt_nor", "/quarts/", {
                "action": "creer_quart", "perimetre": perimetre, "date_debut": "2026-11-01", "date_fin": "2026-11-07", "nom": "Intrus"})
            self.assertEqual(reponse.status_code, 403, perimetre)
        self.assertEqual(Quart.objects.count(), avant)

    def test_cdt_nor_cree_une_liste_chez_lui(self):
        reponse = self.poster("cdt_nor", "/quarts/", {
            "action": "creer_quart", "perimetre": f"ship:{self.nor.pk}", "date_debut": "2026-11-01", "date_fin": "2026-11-07", "nom": "Chez moi"})
        self.assertNotEqual(reponse.status_code, 403)

    def test_cdt_nor_ne_designe_pas_de_chef_de_liste_sur_la_bretagne(self):
        avant = ChefDeListe.objects.count()
        for perimetre in (f"service:{self.service_bre.pk}", f"ship:{self.bre.pk}"):
            reponse = self.poster("cdt_nor", "/quarts/reglages/", {
                "action": "designer", "perimetre": perimetre, "user_id": User.objects.get(username="equipier_nor").pk})
            self.assertEqual(reponse.status_code, 403, perimetre)
        self.assertEqual(ChefDeListe.objects.count(), avant)

    def test_cdt_nor_ne_retire_pas_un_chef_de_liste_bretagne(self):
        cdl = ChefDeListe.objects.get(sector=self.secteur_bre)
        self.poster("cdt_nor", "/quarts/reglages/", {"action": "retirer", "pk": cdl.pk})
        self.assertTrue(ChefDeListe.objects.filter(pk=cdl.pk).exists())

    def test_le_commandant_du_batiment_designe_un_chef_de_liste(self):
        reponse = self.poster("cdt_a", "/quarts/reglages/", {
            "action": "designer", "perimetre": f"service:{self.service_bre.pk}", "user_id": User.objects.get(username="equipier_a").pk})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(ChefDeListe.objects.filter(user__username="equipier_a", service=self.service_bre).exists())

    def test_le_commandant_voisin_ne_gere_pas_les_creneaux(self):
        nb = self.brouillon.creneaux.count()
        reponse = self.poster("cdt_nor", f"/quarts/quart/{self.brouillon.pk}/", {"action": "supprimer_creneau", "creneau": self.brouillon.creneaux.first().pk})
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(self.brouillon.creneaux.count(), nb)
