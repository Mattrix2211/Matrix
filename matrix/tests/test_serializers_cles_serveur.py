"""Audit des serializers en `fields = "__all__"` (tâche Notion « [SEC] Audit des
serializers... ») : un utilisateur ne peut forger ni sa propre identité (auteur,
valideur, demandeur...) ni un périmètre (navire, équipage, objet d'un autre
bâtiment), à la création comme à la modification. Même correctif que
NotificationSerializer (notifications/tests/test_api_droits.py)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Roles, UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, PartRequest
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship
from threads.models import Attachment, Message, Thread
from training.models import ReferentFormation, TrainingCourse, TrainingRecord, TrainingSession


def _navire(nom, code):
    ship = Ship.objects.create(name=nom, code=code)
    service = Service.objects.create(ship=ship, name=f"Service {code}")
    sector = Sector.objects.create(service=service, name=f"Secteur {code}")
    type_actif = AssetType.objects.create(name=f"Type {code}", category="Cat", sector=sector)
    asset = Asset.objects.create(asset_type=type_actif, ship=ship, service=service, sector=sector)
    return ship, service, sector, type_actif, asset


def _utilisateur(nom, role, **profil):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, **profil})
    return user


class BaseApi(TestCase):
    def setUp(self):
        self.ship_a, self.service_a, self.sector_a, self.type_a, self.asset_a = _navire("Navire A", "SA")
        self.ship_b, self.service_b, self.sector_b, self.type_b, self.asset_b = _navire("Navire B", "SB")
        self.chef_a = _utilisateur("chef_a_sec", Roles.CHEF_SECTEUR, ship=self.ship_a, sector=self.sector_a)
        self.autre = _utilisateur("autre_sec", Roles.EQUIPIER, ship=self.ship_a, sector=self.sector_a)
        self.client_a = self._client("chef_a_sec")

    @staticmethod
    def _client(nom):
        client = APIClient()
        client.login(username=nom, password="pass")
        return client


class ThreadsCleServeurTests(BaseApi):
    def setUp(self):
        super().setUp()
        self.ticket_a = CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne A")
        self.ticket_b = CorrectiveTicket.objects.create(asset=self.asset_b, description="Panne B")
        self.ct = ContentType.objects.get_for_model(CorrectiveTicket)
        self.fil_a = Thread.objects.create(content_type=self.ct, object_id=str(self.ticket_a.pk))
        self.fil_b = Thread.objects.create(content_type=self.ct, object_id=str(self.ticket_b.pk))

    def test_auteur_toujours_l_utilisateur_connecte_et_is_system_ignore(self):
        r = self.client_a.post(
            "/api/threads/messages/",
            {"thread": self.fil_a.pk, "author": self.autre.pk, "body": "Texte", "is_system": True},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        message = Message.objects.get(pk=r.data["id"])
        self.assertEqual(message.author, self.chef_a)
        self.assertEqual(message.created_by, self.chef_a)
        self.assertFalse(message.is_system)

    def test_modification_ne_change_ni_auteur_ni_fil(self):
        message = Message.objects.create(thread=self.fil_a, author=self.chef_a, body="v1")
        r = self.client_a.patch(
            f"/api/threads/messages/{message.pk}/",
            {"body": "v2", "author": self.autre.pk, "is_system": True}, format="json",
        )
        self.assertEqual(r.status_code, 200)
        message.refresh_from_db()
        self.assertEqual((message.body, message.author, message.is_system), ("v2", self.chef_a, False))
        r = self.client_a.patch(f"/api/threads/messages/{message.pk}/", {"thread": self.fil_b.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_fil_ne_peut_pas_etre_rattache_a_un_autre_objet(self):
        _utilisateur("chef_section_a_sec", Roles.CHEF_SECTION, ship=self.ship_a, sector=self.sector_a)
        r = self._client("chef_section_a_sec").patch(
            f"/api/threads/threads/{self.fil_a.pk}/", {"object_id": str(self.ticket_b.pk)}, format="json",
        )
        self.assertEqual(r.status_code, 400)


class LogisticsCleServeurTests(BaseApi):
    def setUp(self):
        super().setUp()
        self.chef_section = _utilisateur("cs_log_sec", Roles.CHEF_SECTION, ship=self.ship_a, sector=self.sector_a)
        self.client_a = self._client("cs_log_sec")

    def test_ticket_valide_par_et_created_by_non_forgeables(self):
        r = self.client_a.post(
            "/api/logistics/tickets/",
            {
                "asset": str(self.asset_a.pk), "description": "Fuite", "valide_par": self.autre.pk,
                "date_validation": "2020-01-01T00:00:00Z", "created_by": self.autre.pk, "status": "CLOSED",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        ticket = CorrectiveTicket.objects.get(pk=r.data["id"])
        self.assertIsNone(ticket.valide_par)
        self.assertIsNone(ticket.date_validation)
        self.assertEqual(ticket.created_by, self.chef_section)
        self.assertEqual(ticket.status, "REPORTED")


class MaintenanceCleServeurTests(BaseApi):
    def setUp(self):
        super().setUp()
        self.chef_section = _utilisateur("cs_mnt_sec", Roles.CHEF_SECTION, ship=self.ship_a, sector=self.sector_a)
        self.client_a = self._client("cs_mnt_sec")
        self.plan_a = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_a, name="Plan A")
        self.plan_b = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_b, name="Plan B")
        self.occ_a = MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for=timezone.localdate(),
        )
        self.occ_b = MaintenanceOccurrence.objects.create(
            plan=self.plan_b, asset=self.asset_b, scheduled_for=timezone.localdate(),
        )

    def test_execution_modification_ne_change_pas_valide_par(self):
        execution = MaintenanceExecution.objects.create(occurrence=self.occ_a)
        r = self.client_a.patch(
            f"/api/maintenance/executions/{execution.pk}/", {"notes": "ok", "valide_par": self.autre.pk}, format="json",
        )
        self.assertEqual(r.status_code, 200)
        execution.refresh_from_db()
        self.assertEqual(execution.notes, "ok")
        self.assertIsNone(execution.valide_par)
        self.assertEqual(execution.updated_by, self.chef_section)

    def test_occurrence_sur_materiel_hors_perimetre_refusee(self):
        r = self.client_a.post(
            "/api/maintenance/occurrences/",
            {"plan": self.plan_b.pk, "asset": str(self.asset_b.pk), "scheduled_for": str(timezone.localdate())},
            format="json",
        )
        # Plan et matériel hors périmètre : refus de validation (400) ou de permission (403).
        self.assertIn(r.status_code, (400, 403))


class TrainingCleServeurTests(BaseApi):
    def setUp(self):
        super().setUp()
        self.commandant = _utilisateur("cdt_a_sec", Roles.COMMANDANT, ship=self.ship_a)
        self.marin = _utilisateur("marin_a_sec", Roles.EQUIPIER, ship=self.ship_a)
        self.autre_marin = _utilisateur("marin2_a_sec", Roles.EQUIPIER, ship=self.ship_a)
        self.course = TrainingCourse.objects.create(title="Formation")
        self.client_cdt = self._client("cdt_a_sec")

    def _payload(self, **extra):
        return {
            "user": self.marin.pk, "course": self.course.pk, "completed_at": str(timezone.localdate()),
            "expires_at": str(timezone.localdate() + timedelta(days=365)), **extra,
        }

    def test_enregistrement_valideur_impose_et_created_by_non_forgeable(self):
        r = self.client_cdt.post(
            "/api/training/records/",
            self._payload(validated_by=self.autre_marin.pk, created_by=self.autre_marin.pk), format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        record = TrainingRecord.objects.get(pk=r.data["id"])
        self.assertEqual((record.validated_by, record.created_by), (self.commandant, self.commandant))

    def test_enregistrement_ne_peut_pas_etre_reaffecte_a_un_autre_marin(self):
        record = TrainingRecord.objects.create(
            user=self.marin, course=self.course, completed_at=timezone.localdate(),
            expires_at=timezone.localdate() + timedelta(days=365),
        )
        r = self.client_cdt.patch(
            f"/api/training/records/{record.pk}/", {"user": self.autre_marin.pk}, format="json",
        )
        self.assertEqual(r.status_code, 400)
        record.refresh_from_db()
        self.assertEqual(record.user, self.marin)

    def test_referent_sur_un_autre_navire_toujours_refuse(self):
        r = self.client_a.post(
            "/api/training/referents/",
            {"course": self.course.pk, "ship": self.ship_b.pk, "user": self.autre.pk}, format="json",
        )
        self.assertIn(r.status_code, (403, 401))
        self.assertFalse(ReferentFormation.objects.exists())


class ProfilCleServeurTests(BaseApi):
    def setUp(self):
        super().setUp()
        self.admin_a = _utilisateur("admin_a_sec", Roles.ADMIN_NAVIRE, ship=self.ship_a)
        self.client_admin = self._client("admin_a_sec")
        self.profil = self.autre.profile

    def _patch(self, client, donnees):
        return client.patch(f"/api/accounts/profiles/{self.profil.pk}/", donnees, format="json")

    def test_code_d_equipage_accepte_pour_un_marin_de_son_navire(self):
        r = self._patch(self.client_admin, {"role": Roles.EQUIPIER, "equipage": "A"})
        self.assertEqual(r.status_code, 200, r.content)
        self.profil.refresh_from_db()
        self.assertEqual(self.profil.equipage, "A")


class AssetCleServeurTests(BaseApi):
    def setUp(self):
        super().setUp()
        self.chef_section = _utilisateur("chef_sect_a_sec", Roles.CHEF_SECTION, ship=self.ship_a, sector=self.sector_a)
        self.client_cs = self._client("chef_sect_a_sec")

    def _payload(self, ship, service, sector, type_actif):
        return {"ship": ship.pk, "service": service.pk, "sector": sector.pk, "asset_type": type_actif.pk}

    def test_creation_sur_un_autre_navire_refusee(self):
        r = self.client_cs.post(
            "/api/assets/assets/", self._payload(self.ship_b, self.service_b, self.sector_b, self.type_b), format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_creation_dans_le_perimetre_pose_created_by(self):
        r = self.client_cs.post(
            "/api/assets/assets/",
            {**self._payload(self.ship_a, self.service_a, self.sector_a, self.type_a), "created_by": self.autre.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Asset.objects.get(pk=r.data["id"]).created_by, self.chef_section)

    def test_deplacement_vers_un_autre_navire_refuse(self):
        r = self.client_cs.patch(
            f"/api/assets/assets/{self.asset_a.pk}/", {"ship": self.ship_b.pk}, format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.asset_a.refresh_from_db()
        self.assertEqual(self.asset_a.ship, self.ship_a)


class ReferencesHorsPerimetreTests(BaseApi):
    """Suite de l'audit : références croisées vers un autre bâtiment, auteurs
    forgeables sur les serializers restants, profil sans création par l'API."""

    def setUp(self):
        super().setUp()
        self.chef_section = _utilisateur("cs_ref_sec", Roles.CHEF_SECTION, ship=self.ship_a, sector=self.sector_a)
        self.client_cs = self._client("cs_ref_sec")

    def test_document_sur_materiel_hors_perimetre_refuse_et_auteur_impose(self):
        fichier = lambda: SimpleUploadedFile("d.pdf", b"%PDF-1.4 x", content_type="application/pdf")
        r = self.client_cs.post("/api/assets/asset-docs/", {"asset": str(self.asset_b.pk), "name": "d", "file": fichier()})
        self.assertIn(r.status_code, (400, 403), r.content)
        r = self.client_cs.post(
            "/api/assets/asset-docs/",
            {"asset": str(self.asset_a.pk), "name": "d", "file": fichier(), "created_by": self.autre.pk},
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.asset_a.documents.get().created_by, self.chef_section)

    def test_personnalisation_de_checklist_hors_perimetre_refusee(self):
        from assets.models import ChecklistTemplate
        modele_a = ChecklistTemplate.objects.create(name="M", sector=self.sector_a)
        modele_b = ChecklistTemplate.objects.create(name="M", sector=self.sector_b)
        url = "/api/assets/asset-checklist-overrides/"
        r = self.client_cs.post(url, {"asset": str(self.asset_b.pk), "template": modele_a.pk}, format="json")
        self.assertIn(r.status_code, (400, 403))
        r = self.client_cs.post(url, {"asset": str(self.asset_a.pk), "template": modele_b.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client_cs.post(url, {"asset": str(self.asset_a.pk), "template": modele_a.pk}, format="json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_parent_d_un_materiel_hors_perimetre_refuse(self):
        r = self.client_cs.patch(
            f"/api/assets/assets/{self.asset_a.pk}/", {"parent": str(self.asset_b.pk)}, format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.asset_a.refresh_from_db()
        self.assertIsNone(self.asset_a.parent)

    def test_type_d_un_plan_hors_perimetre_refuse(self):
        r = self.client_cs.post(
            "/api/maintenance/plans/", {"scope": "TYPE", "asset_type": self.type_b.pk, "name": "X"}, format="json",
        )
        self.assertIn(r.status_code, (400, 403), r.content)
        self.assertFalse(MaintenancePlan.objects.exists())

    def test_plan_d_une_occurrence_hors_perimetre_refuse(self):
        plan_b = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_b, name="Plan B")
        r = self.client_cs.post(
            "/api/maintenance/occurrences/",
            {"plan": plan_b.pk, "asset": str(self.asset_a.pk), "scheduled_for": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(MaintenanceOccurrence.objects.exists())

    def test_formation_created_by_et_updated_by_non_forgeables(self):
        r = self._client_chef_formation().post(
            "/api/training/courses/", {"title": "F", "created_by": self.autre.pk, "updated_by": self.autre.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        cours = TrainingCourse.objects.get(pk=r.data["id"])
        self.assertEqual((cours.created_by, cours.updated_by), (self.chef_section_form, self.chef_section_form))

    def _client_chef_formation(self):
        self.chef_section_form = _utilisateur("cs_form_sec", Roles.CHEF_SECTION, ship=self.ship_a, sector=self.sector_a)
        return self._client("cs_form_sec")

    def test_profil_non_creable_par_l_api(self):
        admin = _utilisateur("admin_ref_sec", Roles.ADMIN_NAVIRE, ship=self.ship_a)
        r = self._client("admin_ref_sec").post("/api/accounts/profiles/", {"role": Roles.EQUIPIER}, format="json")
        self.assertEqual(r.status_code, 405)
        self.assertIsNotNone(admin.profile)
