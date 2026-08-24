"""Tests du scoping formation par référents (T-SEC) : seuls les référents
désignés d'une formation précise (TrainingCourse.referents) — ou un rôle de
supervision globale (COMMANDANT et au-dessus) — peuvent créer/modifier un
TrainingRecord ou gérer les présences (attendees) d'une TrainingSession, via
l'API DRF comme via le web. La lecture (statut de qualification, arbre de
compétences) reste ouverte à tout utilisateur connecté, sans restriction liée
aux référents."""
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from training.models import TrainingCourse, TrainingRecord, TrainingSession, peut_valider_formation


def _demain(jours):
    return timezone.localdate() + timedelta(days=jours)


class PeutValiderFormationTests(TestCase):
    """Tests unitaires de la fonction de contrôle d'accès elle-même."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Réf", code="REF")
        service = Service.objects.create(ship=ship, name="Technique")
        self.sector = Sector.objects.create(service=service, name="Électricité")
        self.course = TrainingCourse.objects.create(sector=self.sector, title="Habilitation électrique")

        self.referent = User.objects.create_user(username="referent", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        self.course.referents.add(self.referent)

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

    def test_referent_peut_valider(self):
        self.assertTrue(peut_valider_formation(self.referent, self.course))

    def test_chef_non_referent_ne_peut_pas_valider_meme_de_rang_superieur(self):
        self.assertFalse(peut_valider_formation(self.chef_non_referent, self.course))

    def test_role_supervision_globale_passe_outre(self):
        self.assertTrue(peut_valider_formation(self.commandant, self.course))


class APIRecordScopingTests(TestCase):
    """L'API DRF (TrainingRecordViewSet) applique la même règle que le web :
    pas de contournement possible via l'API."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire API", code="API")
        service = Service.objects.create(ship=ship, name="Technique")
        self.sector = Sector.objects.create(service=service, name="Électricité")
        self.course = TrainingCourse.objects.create(
            sector=self.sector, title="Habilitation électrique", validity_days=365
        )

        self.referent = User.objects.create_user(username="api_referent", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        self.course.referents.add(self.referent)

        self.chef_non_referent = User.objects.create_user(username="api_chef_non_ref", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_non_referent, defaults={"role": "CHEF_SECTEUR", "sector": self.sector}
        )

        self.commandant = User.objects.create_user(username="api_commandant", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

        self.marin = User.objects.create_user(username="api_marin", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})

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
        # Même de rang supérieur et dans le bon secteur : sans être référent,
        # la tentative est rejetée proprement.
        self.client.login(username="api_chef_non_ref", password="pass")
        r = self.client.post("/api/training/records/", data=self._payload(), content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(TrainingRecord.objects.filter(user=self.marin, course=self.course).exists())

    def test_supervision_globale_peut_creer_un_enregistrement(self):
        self.client.login(username="api_commandant", password="pass")
        r = self.client.post("/api/training/records/", data=self._payload(), content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)

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
    référents de la formation concernée — quel que soit leur rang, un
    référent est désigné pour sa compétence, pas pour sa position
    hiérarchique, et peut donc être EQUIPIER (même profil que dans
    APIRecordScopingTests). Le reste de la planification (date, lieu...)
    reste soumis au seuil générique CHEF_SECTION, y compris pour le
    référent lui-même s'il n'a pas ce rang."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Session", code="SES")
        service = Service.objects.create(ship=ship, name="Technique")
        self.sector = Sector.objects.create(service=service, name="Électricité")
        self.course = TrainingCourse.objects.create(
            sector=self.sector, title="Habilitation électrique", validity_days=365
        )
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=5)
        )

        self.referent = User.objects.create_user(username="ses_referent", password="pass")
        UserProfile.objects.update_or_create(user=self.referent, defaults={"role": "EQUIPIER"})
        self.course.referents.add(self.referent)

        self.chef_non_referent = User.objects.create_user(username="ses_chef_non_ref", password="pass")
        UserProfile.objects.update_or_create(user=self.chef_non_referent, defaults={"role": "CHEF_SERVICE"})

        self.commandant = User.objects.create_user(username="ses_commandant", password="pass")
        UserProfile.objects.update_or_create(user=self.commandant, defaults={"role": "COMMANDANT"})

        self.marin = User.objects.create_user(username="ses_marin", password="pass")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER"})

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
        # doit pouvoir gérer les présences de sa propre formation.
        self.client.login(username="ses_referent", password="pass")
        r = self.client.patch(
            f"/api/training/sessions/{self.session.id}/",
            data=json.dumps({"attendees": [self.marin.id]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn(self.marin, self.session.attendees.all())

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


class VueGestionReferentsTests(TestCase):
    """Désignation des référents depuis la modale web de formations.html,
    réservée au même seuil que la gestion des prérequis (CHEF_SECTION),
    candidats limités aux utilisateurs visibles dans le secteur de la
    formation."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Web Réf", code="WREF")
        service = Service.objects.create(ship=ship, name="Pont")
        self.sector = Sector.objects.create(service=service, name="Manœuvre")
        self.autre_sector = Sector.objects.create(service=service, name="Autre secteur")
        self.course = TrainingCourse.objects.create(sector=self.sector, title="Amarrage niveau 1")

        self.chef = User.objects.create_user(username="chef_ref_web", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTION", "sector": self.sector}
        )

        self.marin_secteur = User.objects.create_user(username="marin_secteur", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_secteur, defaults={"role": "EQUIPIER", "sector": self.sector}
        )

        self.marin_hors_secteur = User.objects.create_user(username="marin_hors_secteur", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_hors_secteur, defaults={"role": "EQUIPIER", "sector": self.autre_sector}
        )

    def test_chef_peut_designer_un_referent_du_secteur(self):
        self.client.login(username="chef_ref_web", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.course.id,
            "referents": [self.marin_secteur.id],
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(self.course.referents.all()), [self.marin_secteur])

    def test_referent_hors_secteur_est_ignore(self):
        self.client.login(username="chef_ref_web", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.course.id,
            "referents": [self.marin_hors_secteur.id],
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.course.referents.count(), 0)

    def test_equipier_ne_peut_pas_designer_de_referent(self):
        self.client.login(username="marin_secteur", password="pass")
        r = self.client.post("/formations/", {
            "action": "update_prerequisites",
            "pk": self.course.id,
            "referents": [self.marin_secteur.id],
        })
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.course.referents.count(), 0)

    def test_liste_formations_affiche_les_referents(self):
        self.course.referents.add(self.marin_secteur)
        self.client.login(username="chef_ref_web", password="pass")
        r = self.client.get("/formations/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "marin_secteur")


class ValidationWebReferentFormationTests(TestCase):
    """Un référent d'UNE formation précise (TrainingCourse.referents), même de
    rang EQUIPIER et rattaché à un secteur différent de celui de la formation,
    doit pouvoir la valider via l'interface web (ValiderFormationView) —
    régression corrigée : le contrôle web restait strictement CHEF_SECTION+,
    sans jamais tenir compte du statut de référent (déjà pris en compte côté
    API par TrainingRecordPermission)."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Val Réf", code="VREF")
        service = Service.objects.create(ship=ship, name="Technique")
        self.sector = Sector.objects.create(service=service, name="Électricité")
        self.autre_sector = Sector.objects.create(service=service, name="Pont")
        self.course = TrainingCourse.objects.create(
            sector=self.sector, title="Habilitation électrique", validity_days=365,
        )

        # Le référent est rattaché à un AUTRE secteur que celui de sa
        # formation : cas explicitement prévu par le modèle (un référent est
        # choisi pour sa compétence, pas pour son secteur de rattachement).
        self.referent = User.objects.create_user(username="ref_valide_web", password="pass")
        UserProfile.objects.update_or_create(
            user=self.referent, defaults={"role": "EQUIPIER", "sector": self.autre_sector},
        )
        self.course.referents.add(self.referent)

        self.marin = User.objects.create_user(username="marin_ref_valide", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "sector": self.sector},
        )

        # Rechargé depuis la base pour repartir d'un profil non caché par le
        # signal de création automatique (accounts/models.py).
        self.referent = User.objects.get(pk=self.referent.pk)

    def test_referent_equipier_voit_le_bouton_valider(self):
        self.client.login(username="ref_valide_web", password="pass")
        r = self.client.get("/formations/")
        self.assertTrue(r.context["peut_valider"])

    def test_referent_equipier_peut_valider_sa_formation_hors_de_son_secteur(self):
        self.client.login(username="ref_valide_web", password="pass")
        r = self.client.post("/formations/valider/", {
            "marin_id": self.marin.id,
            "course_id": self.course.id,
            "completed_at": "2026-01-15",
        })
        self.assertEqual(r.status_code, 302)
        record = TrainingRecord.objects.get(user=self.marin, course=self.course)
        self.assertEqual(record.validated_by, self.referent)
