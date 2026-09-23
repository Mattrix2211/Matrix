"""Tests du scoping formation par référents (T-SEC), désormais PAR NAVIRE
(ReferentFormation(course, ship, user), cf. tâche Notion « Formation unique
et portable entre navires ») — seuls les référents désignés d'une formation
précise POUR LE NAVIRE DU MARIN CONCERNÉ (ou un rôle de supervision globale,
COMMANDANT et au-dessus) peuvent créer/modifier un TrainingRecord ou gérer
les présences (attendees) d'une TrainingSession, via l'API DRF comme via le
web. Le navire de référence est TOUJOURS celui du marin concerné par
l'action, jamais celui de l'appelant. La lecture (statut de qualification,
arbre de compétences) reste ouverte à tout utilisateur connecté."""
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Ship
from training.models import (
    ReferentFormation,
    TrainingCourse,
    TrainingRecord,
    TrainingSession,
    peut_valider_formation,
)


def _demain(jours):
    return timezone.localdate() + timedelta(days=jours)


class PeutValiderFormationTests(TestCase):
    """Tests unitaires de la fonction de contrôle d'accès elle-même."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Réf", code="REF")
        self.course = TrainingCourse.objects.create(title="Habilitation électrique")

        self.referent = User.objects.create_user(username="referent", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.referent)

        self.chef_non_referent = User.objects.create_user(username="chef_non_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_non_referent, defaults={"role": "CHEF_SECTEUR"})

        self.commandant = User.objects.create_user(username="commandant", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

        # Le signal de création automatique du profil (accounts/models.py)
        # met en cache un profil EQUIPIER par défaut sur l'instance User créée
        # dans ce même process ; on recharge chaque utilisateur depuis la base
        # pour repartir d'un profil non caché, comme le ferait une requête
        # HTTP réelle (nouvelle instance à chaque requête).
        self.referent = User.objects.get(pk=self.referent.pk)
        self.chef_non_referent = User.objects.get(pk=self.chef_non_referent.pk)
        self.commandant = User.objects.get(pk=self.commandant.pk)

    def test_referent_peut_valider_pour_son_navire(self):
        self.assertTrue(peut_valider_formation(self.referent, self.course, self.ship))

    def test_referent_ne_peut_pas_valider_pour_un_autre_navire(self):
        autre_navire = Ship.objects.create(name="Autre navire réf", code="AREF")
        self.assertFalse(peut_valider_formation(self.referent, self.course, autre_navire))

    def test_chef_non_referent_ne_peut_pas_valider_meme_de_rang_superieur(self):
        self.assertFalse(peut_valider_formation(self.chef_non_referent, self.course, self.ship))

    def test_role_supervision_globale_passe_outre(self):
        self.assertTrue(peut_valider_formation(self.commandant, self.course, self.ship))


class APIRecordScopingTests(TestCase):
    """L'API DRF (TrainingRecordViewSet) applique la même règle que le web :
    pas de contournement possible via l'API. Le référent est désigné POUR LE
    NAVIRE DU MARIN CIBLÉ (self.marin.ship)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire API", code="API")
        self.course = TrainingCourse.objects.create(title="Habilitation électrique", validity_days=365)

        self.marin = User.objects.create_user(username="api_marin", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.referent = User.objects.create_user(username="api_referent", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.referent)

        self.chef_non_referent = User.objects.create_user(username="api_chef_non_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_non_referent, defaults={"role": "CHEF_SECTEUR"})

        self.commandant = User.objects.create_user(username="api_commandant", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

    def _payload(self):
        return {
            "user": self.marin.id,
            "course": self.course.id,
            "completed_at": str(timezone.localdate()),
            "expires_at": str(_demain(365)),
        }

    def test_referent_peut_creer_un_enregistrement(self):
        self.client.login(username="api_referent", password="pass")
        r = self.client.post("/api/training/records/", data=self._payload(), content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_chef_non_referent_ne_peut_pas_creer_un_enregistrement(self):
        self.client.login(username="api_chef_non_ref", password="pass")
        r = self.client.post("/api/training/records/", data=self._payload(), content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(user=self.marin, course=self.course).exists())

    def test_supervision_globale_peut_creer_un_enregistrement(self):
        self.client.login(username="api_commandant", password="pass")
        r = self.client.post("/api/training/records/", data=self._payload(), content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_referent_dun_autre_navire_ne_peut_pas_creer_un_enregistrement(self):
        # Référent désigné pour un AUTRE navire que celui du marin ciblé :
        # aucune autorité sur ce marin.
        autre_navire = Ship.objects.create(name="Autre navire API", code="AAPI")
        referent_autre_navire = User.objects.create_user(username="api_referent_autre", password="pass")
        UserProfile.objects.update_or_create(user=referent_autre_navire, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.course, ship=autre_navire, user=referent_autre_navire)
        self.client.login(username="api_referent_autre", password="pass")
        r = self.client.post("/api/training/records/", data=self._payload(), content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_lecture_ouverte_a_tous_meme_sans_etre_referent(self):
        TrainingRecord.objects.create(
            user=self.marin, course=self.course,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        self.client.login(username="api_chef_non_ref", password="pass")
        r = self.client.get("/api/training/records/")
        self.assertEqual(r.status_code, 200)

    def test_non_referent_ne_peut_pas_modifier_un_enregistrement_existant(self):
        record = TrainingRecord.objects.create(
            user=self.marin, course=self.course,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        self.client.login(username="api_chef_non_ref", password="pass")
        r = self.client.patch(
            f"/api/training/records/{record.id}/",
            data=json.dumps({"expires_at": str(_demain(400))}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_referent_peut_modifier_un_enregistrement_existant(self):
        record = TrainingRecord.objects.create(
            user=self.marin, course=self.course,
            completed_at=timezone.localdate(), expires_at=_demain(365),
        )
        self.client.login(username="api_referent", password="pass")
        r = self.client.patch(
            f"/api/training/records/{record.id}/",
            data=json.dumps({"expires_at": str(_demain(400))}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)


class APISessionAttendeesScopingTests(TestCase):
    """Gestion des présences (attendees) d'une session : réservée aux
    référents de la formation concernée POUR LE NAVIRE DE CHAQUE MARIN
    AJOUTÉ — quel que soit leur rang, un référent est désigné pour sa
    compétence, pas pour sa position hiérarchique, et peut donc être
    EQUIPIER. Le reste de la planification (date, lieu...) reste soumis au
    seuil générique CHEF_SECTION."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Session", code="SES")
        self.course = TrainingCourse.objects.create(title="Habilitation électrique", validity_days=365)
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=5)
        )

        self.marin = User.objects.create_user(username="ses_marin", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.referent = User.objects.create_user(username="ses_referent", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.referent)

        self.chef_non_referent = User.objects.create_user(username="ses_chef_non_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_non_referent, defaults={"role": "CHEF_SERVICE"})

        self.commandant = User.objects.create_user(username="ses_commandant", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

        # Le signal de création automatique du profil (accounts/models.py)
        # met en cache un profil EQUIPIER par défaut sur l'instance User créée
        # dans ce même process ; on recharge chaque utilisateur depuis la base
        # pour repartir d'un profil non caché, comme le ferait une requête
        # HTTP réelle (nouvelle instance à chaque requête).
        self.referent = User.objects.get(pk=self.referent.pk)
        self.chef_non_referent = User.objects.get(pk=self.chef_non_referent.pk)
        self.commandant = User.objects.get(pk=self.commandant.pk)

    def test_referent_equipier_peut_ajouter_un_participant(self):
        # Cas central du correctif : un référent désigné pour sa compétence,
        # même de rang EQUIPIER (donc sous le seuil générique CHEF_SECTION),
        # doit pouvoir gérer les présences de sa propre formation, pour un
        # marin de SON navire.
        self.client.login(username="ses_referent", password="pass")
        r = self.client.patch(
            f"/api/training/sessions/{self.session.id}/",
            data=json.dumps({"attendees": [self.marin.id]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn(self.marin, self.session.attendees.all())

    def test_referent_ne_peut_pas_ajouter_un_marin_dun_autre_navire(self):
        autre_navire = Ship.objects.create(name="Autre navire session", code="ASES")
        marin_autre_navire = User.objects.create_user(username="ses_marin_autre", password="pass")
        UserProfile.objects.update_or_create(
            user=marin_autre_navire, defaults={"role": "EQUIPIER", "ship": autre_navire}
        )
        self.client.login(username="ses_referent", password="pass")
        r = self.client.patch(
            f"/api/training/sessions/{self.session.id}/",
            data=json.dumps({"attendees": [marin_autre_navire.id]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.session.attendees.count(), 0)

    def test_chef_non_referent_ne_peut_pas_gerer_les_presences(self):
        self.client.login(username="ses_chef_non_ref", password="pass")
        r = self.client.patch(
            f"/api/training/sessions/{self.session.id}/",
            data=json.dumps({"attendees": [self.marin.id]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.session.attendees.count(), 0)

    def test_chef_non_referent_peut_modifier_le_planning_sans_toucher_les_presences(self):
        self.client.login(username="ses_chef_non_ref", password="pass")
        r = self.client.patch(
            f"/api/training/sessions/{self.session.id}/",
            data=json.dumps({"location": "Salle machines"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)

    def test_referent_equipier_ne_peut_pas_modifier_le_planning(self):
        # Le statut de référent ne donne aucun droit sur la planification
        # générale (date, lieu...) : c'est le seuil générique CHEF_SECTION
        # qui tranche ce champ, indépendamment de la gestion des présences.
        self.client.login(username="ses_referent", password="pass")
        r = self.client.patch(
            f"/api/training/sessions/{self.session.id}/",
            data=json.dumps({"location": "Salle machines"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_supervision_globale_peut_gerer_les_presences(self):
        self.client.login(username="ses_commandant", password="pass")
        r = self.client.patch(
            f"/api/training/sessions/{self.session.id}/",
            data=json.dumps({"attendees": [self.marin.id]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)


class APIReferentFormationScopingTests(TestCase):
    """Scoping par navire de l'écriture sur /api/training/referents/
    (ReferentFormationViewSet) : un chef ne peut désigner un référent QUE
    pour son propre navire (navire_de(request.user)), jamais pour un autre
    navire fourni dans le payload — faille de sécurité corrigée (le
    `ship` posté n'était auparavant pas confronté au navire de l'appelant).
    Seul un rôle de supervision globale (COMMANDANT et au-dessus) peut agir
    sur n'importe quel navire, même logique que
    training/web_views.py::update_prerequisites."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Chef A", code="CHA")
        self.autre_ship = Ship.objects.create(name="Navire Chef B", code="CHB")
        self.course = TrainingCourse.objects.create(title="Amarrage niveau 1")

        self.chef = User.objects.create_user(username="chef_api_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION", "ship": self.ship})

        self.marin = User.objects.create_user(username="marin_api_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.commandant = User.objects.create_user(username="commandant_api_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

    def test_chef_peut_designer_un_referent_sur_son_propre_navire(self):
        self.client.login(username="chef_api_ref", password="pass")
        r = self.client.post(
            "/api/training/referents/",
            data={"course": self.course.id, "ship": self.ship.id, "user": self.marin.id},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(
            ReferentFormation.objects.filter(course=self.course, ship=self.ship, user=self.marin).exists()
        )

    def test_chef_ne_peut_pas_designer_un_referent_sur_un_autre_navire(self):
        # Cas central de la faille : le chef tente d'imposer le navire de SON
        # choix (autre_ship) dans le payload, plutôt que celui de son propre
        # rattachement (self.ship).
        self.client.login(username="chef_api_ref", password="pass")
        r = self.client.post(
            "/api/training/referents/",
            data={"course": self.course.id, "ship": self.autre_ship.id, "user": self.marin.id},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403, r.content)
        self.assertFalse(ReferentFormation.objects.filter(ship=self.autre_ship).exists())

    def test_chef_ne_peut_pas_modifier_un_referent_dun_autre_navire(self):
        referent_existant = ReferentFormation.objects.create(
            course=self.course, ship=self.autre_ship, user=self.marin
        )
        self.client.login(username="chef_api_ref", password="pass")
        r = self.client.patch(
            f"/api/training/referents/{referent_existant.id}/",
            data=json.dumps({"user": self.chef.id}),
            content_type="application/json",
        )
        # 404, pas 403 : depuis la correction de ReferentFormationViewSet.get_queryset()
        # (audit sécurité scoping API), un référent d'un autre navire est
        # filtré du queryset AVANT même le contrôle d'objet ci-dessous — il
        # n'existe donc plus pour cet appelant, même règle que partout
        # ailleurs dans le projet (cf. maintenance/logistics/tests/test_scope_leak.py).
        self.assertEqual(r.status_code, 404, r.content)

    def test_chef_ne_peut_pas_supprimer_un_referent_dun_autre_navire(self):
        referent_existant = ReferentFormation.objects.create(
            course=self.course, ship=self.autre_ship, user=self.marin
        )
        self.client.login(username="chef_api_ref", password="pass")
        r = self.client.delete(f"/api/training/referents/{referent_existant.id}/")
        # 404, pas 403 : même raison que ci-dessus.
        self.assertEqual(r.status_code, 404, r.content)
        self.assertTrue(ReferentFormation.objects.filter(pk=referent_existant.id).exists())

    def test_supervision_globale_peut_designer_un_referent_sur_nimporte_quel_navire(self):
        self.client.login(username="commandant_api_ref", password="pass")
        r = self.client.post(
            "/api/training/referents/",
            data={"course": self.course.id, "ship": self.autre_ship.id, "user": self.marin.id},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(
            ReferentFormation.objects.filter(course=self.course, ship=self.autre_ship, user=self.marin).exists()
        )


class APIReferentFormationLectureScopingTests(TestCase):
    """Vérifie la faille corrigée sur ReferentFormationViewSet.get_queryset() :
    avant correction, seule l'ÉCRITURE était scopée au navire de l'appelant
    (ReferentFormationPermission ci-dessus) — la LECTURE (GET liste/détail)
    n'appliquait AUCUN filtre de périmètre, alors que la même information
    est déjà scopée au navire de l'appelant côté web (cf.
    test_referent_dun_autre_navire_non_affiche ci-dessous)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Lecture A", code="LCA")
        self.autre_ship = Ship.objects.create(name="Navire Lecture B", code="LCB")
        self.course = TrainingCourse.objects.create(title="Amarrage niveau 2")

        self.marin = User.objects.create_user(username="marin_lecture_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.chef = User.objects.create_user(username="chef_lecture_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION", "ship": self.ship})

        self.marin_autre_navire = User.objects.create_user(username="marin_lecture_autre", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_autre_navire, defaults={"role": "EQUIPIER", "ship": self.autre_ship}
        )

        self.referent_a = ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.marin)
        self.referent_b = ReferentFormation.objects.create(
            course=self.course, ship=self.autre_ship, user=self.marin_autre_navire
        )

        self.commandant = User.objects.create_user(username="commandant_lecture_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

    def test_liste_des_referents_ne_contient_pas_ceux_dun_autre_navire(self):
        self.client.login(username="chef_lecture_ref", password="pass")
        r = self.client.get("/api/training/referents/")
        self.assertEqual(r.status_code, 200)
        ids = {ref["id"] for ref in r.json()}
        self.assertIn(self.referent_a.id, ids)
        self.assertNotIn(self.referent_b.id, ids)

    def test_ne_peut_pas_lire_un_referent_dun_autre_navire_par_pk(self):
        self.client.login(username="chef_lecture_ref", password="pass")
        r = self.client.get(f"/api/training/referents/{self.referent_b.id}/")
        self.assertEqual(r.status_code, 404)

    def test_supervision_globale_voit_les_referents_de_toute_la_flotte(self):
        self.client.login(username="commandant_lecture_ref", password="pass")
        r = self.client.get("/api/training/referents/")
        self.assertEqual(r.status_code, 200)
        ids = {ref["id"] for ref in r.json()}
        self.assertIn(self.referent_a.id, ids)
        self.assertIn(self.referent_b.id, ids)


class VueGestionReferentsTests(TestCase):
    """Désignation des référents depuis la modale web de formations.html,
    réservée au même seuil que la gestion des prérequis (CHEF_SECTION),
    TOUJOURS scopée au navire de L'APPELANT (ReferentFormation) : un chef ne
    désigne des référents que pour son propre navire, jamais pour un autre
    navire proposant la même formation globale."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Web Réf", code="WREF")
        self.autre_ship = Ship.objects.create(name="Autre navire web réf", code="AWREF")
        self.course = TrainingCourse.objects.create(title="Amarrage niveau 1")

        self.chef = User.objects.create_user(username="chef_ref_web", password="pass")
        UserProfile.objects.update_or_create(user=self.chef, defaults={"role": "CHEF_SECTION", "ship": self.ship})

        self.marin_navire = User.objects.create_user(username="marin_navire_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.marin_navire, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.marin_autre_navire = User.objects.create_user(username="marin_autre_navire_ref", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_autre_navire, defaults={"role": "EQUIPIER", "ship": self.autre_ship}
        )

    def test_chef_peut_designer_un_referent_de_son_navire(self):
        self.client.login(username="chef_ref_web", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.course.id,
            "referents": [self.marin_navire.id],
        })
        self.assertEqual(r.status_code, 302)
        referent = ReferentFormation.objects.get(course=self.course, ship=self.ship)
        self.assertEqual(referent.user, self.marin_navire)

    def test_referent_dun_autre_navire_est_ignore(self):
        self.client.login(username="chef_ref_web", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.course.id,
            "referents": [self.marin_autre_navire.id],
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(ReferentFormation.objects.filter(course=self.course).exists())

    def test_equipier_ne_peut_pas_designer_de_referent(self):
        self.client.login(username="marin_navire_ref", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.course.id,
            "referents": [self.marin_navire.id],
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(ReferentFormation.objects.filter(course=self.course).exists())

    def test_liste_formations_affiche_les_referents_de_mon_navire(self):
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.marin_navire)
        self.client.login(username="chef_ref_web", password="pass")
        r = self.client.get("/formations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "marin_navire_ref")

    def test_referent_dun_autre_navire_non_affiche(self):
        # Un référent désigné pour un AUTRE navire n'apparaît pas sur la
        # fiche formation consultée depuis ce navire-ci.
        ReferentFormation.objects.create(course=self.course, ship=self.autre_ship, user=self.marin_autre_navire)
        self.client.login(username="chef_ref_web", password="pass")
        r = self.client.get("/formations/")
        self.assertNotContains(r, "marin_autre_navire_ref")


class ValidationWebReferentFormationTests(TestCase):
    """Un référent d'UNE formation précise (ReferentFormation), même de rang
    EQUIPIER, doit pouvoir la valider via l'interface web (ValiderFormationView)
    pour un marin de SON navire."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Val Réf", code="VREF")
        self.course = TrainingCourse.objects.create(title="Habilitation électrique", validity_days=365)

        self.marin = User.objects.create_user(username="marin_ref_valide", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship})

        self.referent = User.objects.create_user(username="ref_valide_web", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        ReferentFormation.objects.create(course=self.course, ship=self.ship, user=self.referent)

        # Rechargé depuis la base pour repartir d'un profil non caché par le
        # signal de création automatique (accounts/models.py).
        self.referent = User.objects.get(pk=self.referent.pk)

    def test_referent_equipier_voit_le_bouton_valider(self):
        self.client.login(username="ref_valide_web", password="pass")
        r = self.client.get("/formations/")
        self.assertTrue(r.context["peut_valider"])

    def test_referent_equipier_peut_valider_sa_formation_pour_le_navire_concerne(self):
        self.client.login(username="ref_valide_web", password="pass")
        r = self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        self.assertEqual(r.status_code, 302)
        record = TrainingRecord.objects.get(user=self.marin, course=self.course)
        self.assertEqual(record.validated_by, self.referent)
