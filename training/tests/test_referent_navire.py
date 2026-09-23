"""Tests du référent formation DU NAVIRE (ReferentFormationNavire) — à ne pas
confondre avec les référents PAR FORMATION désormais rattachés à un navire
(ReferentFormation, cf. test_referents.py). Un référent formation du navire
obtient l'autorité de validation sur TOUTES les formations du navire, dès
lors qu'il est désigné par un rôle de supervision globale (COMMANDANT et
au-dessus)."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship
from training.models import ReferentFormationNavire, TrainingCourse, TrainingRecord, peut_valider_formation


class ReferentFormationNavireModelTests(TestCase):
    """Tests unitaires de peut_valider_formation() étendue au référent navire."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Réf Nav", code="RNAV")
        # Catalogue global : les deux formations n'appartiennent à aucun
        # navire en particulier, seule l'autorité du référent (par navire)
        # détermine qui peut les valider.
        self.course = TrainingCourse.objects.create(title="Habilitation électrique")
        self.autre_course = TrainingCourse.objects.create(title="Maintenance moteur")

        self.referent_navire = User.objects.create_user(username="referent_navire", password="pass")
        UserProfile.objects.update_or_create(user=self.referent_navire, defaults={"role": "EQUIPIER"})
        ReferentFormationNavire.objects.create(ship=self.ship, user=self.referent_navire)

        self.marin_lambda = User.objects.create_user(username="marin_lambda", password="pass")
        UserProfile.objects.update_or_create(user=self.marin_lambda, defaults={"role": "EQUIPIER"})

        # Rechargés depuis la base pour repartir d'un profil non caché par le
        # signal de création automatique (accounts/models.py).
        self.referent_navire = User.objects.get(pk=self.referent_navire.pk)
        self.marin_lambda = User.objects.get(pk=self.marin_lambda.pk)

    def test_referent_navire_peut_valider_nimporte_quelle_formation_du_navire(self):
        self.assertTrue(peut_valider_formation(self.referent_navire, self.course, self.ship))
        self.assertTrue(peut_valider_formation(self.referent_navire, self.autre_course, self.ship))

    def test_marin_lambda_ne_peut_pas_valider(self):
        self.assertFalse(peut_valider_formation(self.marin_lambda, self.course, self.ship))

    def test_referent_navire_dun_autre_navire_ne_peut_pas_valider(self):
        autre_ship = Ship.objects.create(name="Autre navire", code="AUTR")
        ReferentFormationNavire.objects.create(ship=autre_ship, user=self.marin_lambda)
        self.marin_lambda = User.objects.get(pk=self.marin_lambda.pk)
        # Le référent d'un AUTRE navire n'a pas autorité sur self.ship.
        self.assertFalse(peut_valider_formation(self.marin_lambda, self.course, self.ship))

    def test_ship_none_refuse_sauf_supervision_globale(self):
        # Si le navire du marin concerné n'est pas résolvable, seule la
        # supervision globale (COMMANDANT+) donne autorité.
        self.assertFalse(peut_valider_formation(self.referent_navire, self.course, None))

    def test_un_seul_referent_par_navire(self):
        # OneToOneField sur ship : désigner un nouveau référent doit remplacer
        # l'ancien plutôt que d'en avoir plusieurs en parallèle.
        nouveau = User.objects.create_user(username="nouveau_referent", password="pass")
        ReferentFormationNavire.objects.filter(ship=self.ship).update(user=nouveau)
        self.assertEqual(ReferentFormationNavire.objects.filter(ship=self.ship).count(), 1)


class VueGestionReferentNavireTests(TestCase):
    """Désignation/retrait du référent formation du navire depuis la page
    formations.html, réservée aux rôles de supervision globale (COMMANDANT+),
    candidats limités aux utilisateurs visibles sur le navire du demandeur."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Web Réf Nav", code="WRNAV")
        self.autre_ship = Ship.objects.create(name="Autre navire web", code="AWNAV")

        self.commandant = User.objects.create_user(username="cdt_ref_nav", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant, defaults={"role": "COMMANDANT", "ship": self.ship}
        )

        self.chef_secteur = User.objects.create_user(username="chef_ref_nav", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "ship": self.ship}
        )

        self.marin_du_navire = User.objects.create_user(username="marin_du_navire", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_du_navire, defaults={"role": "EQUIPIER", "ship": self.ship}
        )

        self.marin_autre_navire = User.objects.create_user(username="marin_autre_navire", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_autre_navire, defaults={"role": "EQUIPIER", "ship": self.autre_ship}
        )

    def test_commandant_peut_designer_un_referent_du_navire(self):
        self.client.login(username="cdt_ref_nav", password="pass")
        r = self.client.post("/formations/", {
            "action": "set_referent_navire",
            "referent_navire_id": self.marin_du_navire.id,
        })
        self.assertEqual(r.status_code, 302)
        referent = ReferentFormationNavire.objects.get(ship=self.ship)
        self.assertEqual(referent.user, self.marin_du_navire)

    def test_designer_un_nouveau_referent_remplace_lancien(self):
        ReferentFormationNavire.objects.create(ship=self.ship, user=self.marin_du_navire)
        self.client.login(username="cdt_ref_nav", password="pass")
        r = self.client.post("/formations/", {
            "action": "set_referent_navire",
            "referent_navire_id": self.chef_secteur.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ReferentFormationNavire.objects.filter(ship=self.ship).count(), 1)
        self.assertEqual(ReferentFormationNavire.objects.get(ship=self.ship).user, self.chef_secteur)

    def test_marin_hors_navire_est_refuse(self):
        self.client.login(username="cdt_ref_nav", password="pass")
        r = self.client.post("/formations/", {
            "action": "set_referent_navire",
            "referent_navire_id": self.marin_autre_navire.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(ReferentFormationNavire.objects.filter(ship=self.ship).exists())

    def test_chef_secteur_ne_peut_pas_designer_de_referent_navire(self):
        # Sous le seuil COMMANDANT : refusé, même chef d'un secteur du navire.
        self.client.login(username="chef_ref_nav", password="pass")
        r = self.client.post("/formations/", {
            "action": "set_referent_navire",
            "referent_navire_id": self.marin_du_navire.id,
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(ReferentFormationNavire.objects.filter(ship=self.ship).exists())

    def test_commandant_peut_retirer_le_referent_navire(self):
        ReferentFormationNavire.objects.create(ship=self.ship, user=self.marin_du_navire)
        self.client.login(username="cdt_ref_nav", password="pass")
        r = self.client.post("/formations/", {"action": "retirer_referent_navire"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(ReferentFormationNavire.objects.filter(ship=self.ship).exists())

    def test_page_formations_affiche_le_referent_navire(self):
        ReferentFormationNavire.objects.create(ship=self.ship, user=self.marin_du_navire)
        self.client.login(username="cdt_ref_nav", password="pass")
        r = self.client.get("/formations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "marin_du_navire")


class ValidationWebReferentNavireTests(TestCase):
    """Un référent formation du navire (ReferentFormationNavire), même de rang
    EQUIPIER, doit pouvoir valider une formation via l'interface web
    (ValiderFormationView), pour un marin de SON navire."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Val Réf Nav", code="VRNAV")
        self.course = TrainingCourse.objects.create(title="Équipier de sécurité incendie", validity_days=365)

        self.referent_navire = User.objects.create_user(username="ref_nav_valide", password="pass")
        UserProfile.objects.update_or_create(
            user=self.referent_navire, defaults={"role": "EQUIPIER", "ship": self.ship},
        )
        ReferentFormationNavire.objects.create(ship=self.ship, user=self.referent_navire)

        self.marin = User.objects.create_user(username="marin_ref_nav_valide", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship},
        )

        # Rechargé depuis la base pour repartir d'un profil non caché par le
        # signal de création automatique (accounts/models.py).
        self.referent_navire = User.objects.get(pk=self.referent_navire.pk)

    def test_referent_navire_equipier_voit_le_bouton_valider(self):
        self.client.login(username="ref_nav_valide", password="pass")
        r = self.client.get("/formations/")
        self.assertTrue(r.context["peut_valider"])
        self.assertContains(r, "validerFormationModal")

    def test_referent_navire_equipier_peut_valider_une_formation(self):
        self.client.login(username="ref_nav_valide", password="pass")
        r = self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        self.assertEqual(r.status_code, 302)
        record = TrainingRecord.objects.get(user=self.marin, course=self.course)
        self.assertEqual(record.validated_by, self.referent_navire)

    def test_referent_navire_ne_peut_pas_valider_pour_un_marin_dun_autre_navire(self):
        # L'autorité du référent navire est bornée à SON navire (le navire du
        # marin CIBLÉ compte, pas celui de l'appelant).
        autre_ship = Ship.objects.create(name="Autre navire val", code="AVAL")
        marin_autre_navire = User.objects.create_user(username="marin_autre_navire_val", password="pass")
        UserProfile.objects.update_or_create(
            user=marin_autre_navire, defaults={"role": "EQUIPIER", "ship": autre_ship},
        )
        self.client.login(username="ref_nav_valide", password="pass")
        r = self.client.post("/formations/valider/", {
            "marin_id": marin_autre_navire.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(user=marin_autre_navire, course=self.course).exists())
