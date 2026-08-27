"""Correction Tech Lead n°1 (tâche Notion « Circuit C ») — l'API REST
(TrainingCourseViewSet) ne doit exposer les formations « gérées par le bord »
encore WAITING_VALIDATION/REFUSED qu'à leur proposeur et à leurs validateurs
compétents (même règle de périmètre que côté web), et ne doit jamais
permettre l'écriture directe de gere_par_le_bord/statut_validation — ces deux
champs restent exclusivement pilotés par le Circuit C côté web
(training/web_views.py).

Correction Tech Lead n°2 (même tâche) : la lecture seule de
gere_par_le_bord/statut_validation ne suffisait pas — TOUS LES AUTRES champs
(title, description, category...) d'une formation « bord » restaient
librement modifiables via PATCH/PUT/DELETE par n'importe quel CHEF_SECTION,
y compris d'un navire totalement hors périmètre, sans que
peut_modifier_formation_bord/formation_bord_en_service (déjà correctes côté
web) ne soient jamais consultées. PermissionEcritureCircuitBordAPITests
ci-dessous reproduit exactement le scénario du Tech Lead."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Sector, Section, Service, Ship
from training.models import TrainingCourse, TrainingRecord


def _construire_bord(prefixe):
    ship = Ship.objects.create(name=f"Navire {prefixe}", code=prefixe[:8])
    service = Service.objects.create(ship=ship, name=f"Service {prefixe}")
    sector = Sector.objects.create(service=service, name=f"Secteur {prefixe}")
    section = Section.objects.create(sector=sector, name=f"Section {prefixe}")
    return ship, service, sector, section


class FuiteVisibiliteAPITests(TestCase):
    """Une formation bord WAITING_VALIDATION/REFUSED ne doit apparaître, via
    l'API, que pour son proposeur, ses validateurs compétents (même
    périmètre organisationnel que côté web), ou la supervision globale —
    jamais pour un marin normal, y compris d'un autre navire."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("APIVIS")
        self.chef_secteur = User.objects.create_user(username="api_chef_secteur", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.chef_service = User.objects.create_user(username="api_chef_service", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service, defaults={"role": "CHEF_SERVICE", "service": self.service},
        )
        autre_ship, autre_service, _, _ = _construire_bord("APIHORS")
        self.marin_normal = User.objects.create_user(username="api_marin_normal", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_normal, defaults={"role": "EQUIPIER", "service": autre_service},
        )
        self.chef_service_hors = User.objects.create_user(username="api_chef_service_hors", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service_hors, defaults={"role": "CHEF_SERVICE", "service": autre_service},
        )
        self.commandant = User.objects.create_user(username="api_commandant", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant, defaults={"role": "COMMANDANT", "ship": Ship.objects.create(name="Navire CMD", code="APICMD")},
        )
        self.en_attente = TrainingCourse.objects.create(
            title="Formation API en attente", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )
        self.refusee = TrainingCourse.objects.create(
            title="Formation API refusée", gere_par_le_bord=True, statut_validation="REFUSED",
            created_by=self.chef_secteur, updated_by=self.chef_secteur,
        )
        self.active = TrainingCourse.objects.create(title="Formation API active")

    def _login(self, user):
        client = APIClient()
        client.login(username=user.username, password="pass")
        return client

    def _titres_visibles(self, user):
        r = self._login(user).get("/api/training/courses/")
        self.assertEqual(r.status_code, 200)
        return {item["title"] for item in r.json()}

    def test_marin_normal_ne_voit_pas_les_formations_en_attente_ou_refusees(self):
        titres = self._titres_visibles(self.marin_normal)
        self.assertIn("Formation API active", titres)
        self.assertNotIn("Formation API en attente", titres)
        self.assertNotIn("Formation API refusée", titres)

    def test_chef_service_hors_perimetre_ne_voit_rien_en_attente(self):
        titres = self._titres_visibles(self.chef_service_hors)
        self.assertNotIn("Formation API en attente", titres)
        self.assertNotIn("Formation API refusée", titres)

    def test_proposeur_voit_ses_propres_propositions(self):
        titres = self._titres_visibles(self.chef_secteur)
        self.assertIn("Formation API en attente", titres)
        self.assertIn("Formation API refusée", titres)

    def test_validateur_du_perimetre_voit_la_proposition_en_attente_mais_pas_la_refusee(self):
        titres = self._titres_visibles(self.chef_service)
        self.assertIn("Formation API en attente", titres)
        self.assertNotIn("Formation API refusée", titres)

    def test_supervision_globale_voit_tout(self):
        titres = self._titres_visibles(self.commandant)
        self.assertIn("Formation API en attente", titres)
        self.assertIn("Formation API refusée", titres)

    def test_recuperation_directe_par_pk_refusee_pour_un_marin_hors_perimetre(self):
        r = self._login(self.marin_normal).get(f"/api/training/courses/{self.en_attente.id}/")
        self.assertEqual(r.status_code, 404)


class FuiteEcritureAPITests(TestCase):
    """Un CHEF_SECTION (seuil d'écriture générique de TrainingCourseViewSet,
    RolePermission.min_level_write) ne doit pas pouvoir contourner le Circuit
    C en posant directement statut_validation="ACTIVE" ou gere_par_le_bord
    via l'API : ces deux champs sont désormais en lecture seule côté
    serializer, quel que soit le rôle de l'appelant."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("APIECR")
        self.chef_section = User.objects.create_user(username="api_chef_section", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section, defaults={"role": "CHEF_SECTION", "section": self.section},
        )

    def _login(self, user):
        client = APIClient()
        client.login(username=user.username, password="pass")
        return client

    def test_creation_ignore_gere_par_le_bord_et_statut_force(self):
        r = self._login(self.chef_section).post("/api/training/courses/", {
            "title": "Formation créée via API",
            "gere_par_le_bord": True,
            "statut_validation": "ACTIVE",
        })
        self.assertEqual(r.status_code, 201)
        course = TrainingCourse.objects.get(title="Formation créée via API")
        self.assertFalse(course.gere_par_le_bord)
        self.assertEqual(course.statut_validation, "ACTIVE")

    def test_patch_ne_peut_pas_activer_une_formation_en_attente(self):
        course = TrainingCourse.objects.create(
            title="Formation API à contourner", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
            created_by=self.chef_section, updated_by=self.chef_section,
        )
        r = self._login(self.chef_section).patch(
            f"/api/training/courses/{course.id}/", {"statut_validation": "ACTIVE"}, format="json",
        )
        self.assertEqual(r.status_code, 200)
        course.refresh_from_db()
        self.assertEqual(course.statut_validation, "WAITING_VALIDATION")


class PermissionEcritureCircuitBordAPITests(TestCase):
    """Deuxième refus du Tech Lead : reproduit précisément le scénario signalé
    — un CHEF_SECTION d'un navire B modifie via PATCH le CONTENU (title,
    description, category...) d'une formation « bord » ACTIVE et déjà en
    service (TrainingRecord associé) d'un navire A, sans aucun rapport avec
    ce navire A. La correction réutilise peut_modifier_formation_bord et
    formation_bord_en_service (training/web_views.py) dans
    TrainingCourseViewSet.perform_update/perform_destroy — mêmes fonctions
    que le circuit web, aucune règle dupliquée."""

    def setUp(self):
        # Navire A : propriétaire réel de la formation bord.
        self.ship_a, self.service_a, self.sector_a, self.section_a = _construire_bord("BORDA")
        self.chef_secteur_a = User.objects.create_user(username="api_chef_secteur_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_secteur_a, defaults={"role": "CHEF_SECTEUR", "sector": self.sector_a},
        )
        self.chef_service_a = User.objects.create_user(username="api_chef_service_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_service_a, defaults={"role": "CHEF_SERVICE", "service": self.service_a},
        )
        marin_a = User.objects.create_user(username="api_marin_a", password="pass")
        UserProfile.objects.update_or_create(
            user=marin_a, defaults={"role": "EQUIPIER", "service": self.service_a},
        )

        # Navire B : totalement hors périmètre de la formation ci-dessus.
        self.ship_b, self.service_b, self.sector_b, self.section_b = _construire_bord("BORDB")
        self.chef_section_b = User.objects.create_user(username="api_chef_section_b", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section_b, defaults={"role": "CHEF_SECTION", "section": self.section_b},
        )

        aujourdhui = timezone.localdate()
        # Formation bord ACTIVE, déjà validée par le chef de service du
        # navire A, ET déjà en service (un marin l'a suivie et obtenue).
        self.course_active = TrainingCourse.objects.create(
            title="Sécurité incendie bord A", description="Contenu d'origine", gere_par_le_bord=True,
            statut_validation="ACTIVE", created_by=self.chef_secteur_a, updated_by=self.chef_secteur_a,
        )
        TrainingRecord.objects.create(
            user=marin_a, course=self.course_active,
            completed_at=aujourdhui, expires_at=aujourdhui + timezone.timedelta(days=365),
        )
        # Formation bord encore en attente de validation (pas « en service »)
        # du même navire A — sert à isoler le contrôle de périmètre du
        # contrôle « en service » dans les tests ci-dessous.
        self.course_en_attente = TrainingCourse.objects.create(
            title="Habilitation bord A en attente", gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
            created_by=self.chef_secteur_a, updated_by=self.chef_secteur_a,
        )

    def _login(self, user):
        client = APIClient()
        client.login(username=user.username, password="pass")
        return client

    def test_chef_section_hors_perimetre_ne_peut_pas_patcher_une_formation_bord_active_en_service(self):
        """Scénario exact reproduit par le Tech Lead : PATCH title/description
        par un CHEF_SECTION d'un autre navire, sur une formation ACTIVE avec
        TrainingRecord associé — doit être bloqué, avec un message clair."""
        r = self._login(self.chef_section_b).patch(
            f"/api/training/courses/{self.course_active.id}/",
            {"title": "Détournée par le navire B", "description": "Contenu détourné"},
            format="json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn("périmètre", r.json()["detail"])
        self.course_active.refresh_from_db()
        self.assertEqual(self.course_active.title, "Sécurité incendie bord A")
        self.assertEqual(self.course_active.description, "Contenu d'origine")

    def test_chef_section_hors_perimetre_ne_peut_pas_supprimer_une_formation_bord(self):
        r = self._login(self.chef_section_b).delete(f"/api/training/courses/{self.course_active.id}/")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(TrainingCourse.objects.filter(pk=self.course_active.id).exists())

    def test_chef_section_hors_perimetre_ne_voit_meme_pas_une_formation_pas_encore_en_service(self):
        """Une formation bord WAITING_VALIDATION hors périmètre reste
        invisible (fuite de lecture, déjà corrigée — cf.
        FuiteVisibiliteAPITests) : le PATCH échoue donc en 404 (objet
        introuvable dans get_queryset), pas en 403 — la formation ACTIVE
        déjà en service (test précédent) reste, elle, visible de tous
        (catalogue général), d'où le 403 dans ce cas-là uniquement."""
        r = self._login(self.chef_section_b).patch(
            f"/api/training/courses/{self.course_en_attente.id}/", {"title": "Détournée"}, format="json",
        )
        self.assertEqual(r.status_code, 404)
        self.course_en_attente.refresh_from_db()
        self.assertEqual(self.course_en_attente.title, "Habilitation bord A en attente")

    def test_meme_perimetre_ne_peut_pas_non_plus_modifier_une_formation_deja_en_service(self):
        """Même un chef de secteur DU MÊME PÉRIMÈTRE que le proposeur
        d'origine ne peut pas muter en place une formation ACTIVE déjà
        utilisée (validations, sessions, prérequis) : le contrôle « en
        service » s'applique indépendamment du contrôle de périmètre."""
        r = self._login(self.chef_secteur_a).patch(
            f"/api/training/courses/{self.course_active.id}/", {"title": "Nouvelle version"}, format="json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn("déjà active et utilisée", r.json()["detail"])
        self.course_active.refresh_from_db()
        self.assertEqual(self.course_active.title, "Sécurité incendie bord A")

    def test_chef_service_du_perimetre_peut_modifier_et_active_une_formation_en_attente(self):
        """Un CHEF_SERVICE de son propre périmètre peut modifier une
        formation bord pas encore en service — son propre rôle vaut l'accord
        requis, elle devient immédiatement ACTIVE (même règle que côté web)."""
        r = self._login(self.chef_service_a).patch(
            f"/api/training/courses/{self.course_en_attente.id}/",
            {"title": "Habilitation bord A corrigée"}, format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.course_en_attente.refresh_from_db()
        self.assertEqual(self.course_en_attente.title, "Habilitation bord A corrigée")
        self.assertEqual(self.course_en_attente.statut_validation, "ACTIVE")

    def test_chef_secteur_proposeur_modifie_une_formation_en_attente_reste_en_attente(self):
        """Le proposeur d'origine (CHEF_SECTEUR, sous le seuil CHEF_SERVICE)
        peut corriger sa propre proposition, mais elle reste WAITING_VALIDATION
        — son propre rôle ne vaut pas l'accord requis."""
        r = self._login(self.chef_secteur_a).patch(
            f"/api/training/courses/{self.course_en_attente.id}/",
            {"title": "Habilitation bord A retouchée"}, format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.course_en_attente.refresh_from_db()
        self.assertEqual(self.course_en_attente.title, "Habilitation bord A retouchée")
        self.assertEqual(self.course_en_attente.statut_validation, "WAITING_VALIDATION")

    def test_formation_organisme_reste_modifiable_normalement_par_un_chef_section_quelconque(self):
        """Non-régression : une formation « organisme » (gere_par_le_bord=False)
        n'est concernée par aucun de ces garde-fous, un CHEF_SECTION quelconque
        peut continuer à la modifier (seuil générique RolePermission)."""
        organisme = TrainingCourse.objects.create(title="Formation organisme classique")
        r = self._login(self.chef_section_b).patch(
            f"/api/training/courses/{organisme.id}/", {"title": "Formation organisme modifiée"}, format="json",
        )
        self.assertEqual(r.status_code, 200)
        organisme.refresh_from_db()
        self.assertEqual(organisme.title, "Formation organisme modifiée")
