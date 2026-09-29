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
from org.models import Equipage, Sector, Service, Ship
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

    def test_message_sur_un_fil_hors_perimetre_refuse(self):
        r = self.client_a.post("/api/threads/messages/", {"thread": self.fil_b.pk, "body": "x"}, format="json")
        self.assertIn(r.status_code, (403, 404))
        self.assertFalse(Message.objects.filter(thread=self.fil_b).exists())

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

    def test_fil_sur_un_objet_hors_perimetre_refuse_et_annule(self):
        # Un chef de section (seuil d'écriture des fils) du navire A.
        _utilisateur("chef_section_a_sec", Roles.CHEF_SECTION, ship=self.ship_a, sector=self.sector_a)
        client = self._client("chef_section_a_sec")
        Thread.objects.all().delete()
        r = client.post(
            "/api/threads/threads/", {"content_type": self.ct.pk, "object_id": str(self.ticket_b.pk)}, format="json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Thread.objects.exists())
        r = client.post(
            "/api/threads/threads/", {"content_type": self.ct.pk, "object_id": str(self.ticket_a.pk)}, format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)

    def test_fil_ne_peut_pas_etre_rattache_a_un_autre_objet(self):
        _utilisateur("chef_section_a_sec", Roles.CHEF_SECTION, ship=self.ship_a, sector=self.sector_a)
        r = self._client("chef_section_a_sec").patch(
            f"/api/threads/threads/{self.fil_a.pk}/", {"object_id": str(self.ticket_b.pk)}, format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_piece_jointe_seulement_sur_son_propre_message(self):
        message_autre = Message.objects.create(thread=self.fil_a, author=self.autre, body="autre")
        fichier = SimpleUploadedFile("a.txt", b"contenu", content_type="text/plain")
        r = self.client_a.post(
            "/api/threads/attachments/", {"message": message_autre.pk, "file": fichier, "name": "a.txt"},
        )
        self.assertEqual(r.status_code, 403, r.content)
        self.assertFalse(Attachment.objects.exists())


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

    def test_ticket_sur_un_materiel_hors_perimetre_refuse(self):
        r = self.client_a.post(
            "/api/logistics/tickets/", {"asset": str(self.asset_b.pk), "description": "x"}, format="json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(CorrectiveTicket.objects.exists())

    def test_ticket_ne_peut_pas_etre_deplace_hors_perimetre(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset_a, description="x")
        r = self.client_a.patch(
            f"/api/logistics/tickets/{ticket.pk}/", {"asset": str(self.asset_b.pk), "valide_par": self.autre.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 403)
        ticket.refresh_from_db()
        self.assertEqual(ticket.asset, self.asset_a)

    def test_demande_de_pieces_demandeur_impose_et_ticket_dans_le_perimetre(self):
        ticket_a = CorrectiveTicket.objects.create(asset=self.asset_a, description="a")
        ticket_b = CorrectiveTicket.objects.create(asset=self.asset_b, description="b")
        r = self.client_a.post(
            "/api/logistics/part-requests/", {"ticket": str(ticket_a.pk), "requested_by": self.autre.pk}, format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        demande = PartRequest.objects.get(pk=r.data["id"])
        self.assertEqual((demande.requested_by, demande.created_by), (self.chef_section, self.chef_section))
        r = self.client_a.post("/api/logistics/part-requests/", {"ticket": str(ticket_b.pk)}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_ligne_de_pieces_sur_une_demande_hors_perimetre_refusee(self):
        ticket_b = CorrectiveTicket.objects.create(asset=self.asset_b, description="b")
        demande_b = PartRequest.objects.create(ticket=ticket_b)
        r = self.client_a.post(
            "/api/logistics/part-lines/",
            {"part_request": demande_b.pk, "reference": "R", "description": "d", "qty": 1}, format="json",
        )
        self.assertEqual(r.status_code, 403)


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

    def test_execution_signature_et_horodatages_non_forgeables(self):
        r = self.client_a.post(
            "/api/maintenance/executions/",
            {
                "occurrence": self.occ_a.pk, "conformity": "CONFORME", "valide_par": self.autre.pk,
                "executed_by": self.autre.pk, "completed_at": "2020-01-01T00:00:00Z",
                "date_validation": "2020-01-01T00:00:00Z",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        execution = MaintenanceExecution.objects.get(pk=r.data["id"])
        self.assertIsNone(execution.valide_par)
        self.assertIsNone(execution.date_validation)
        self.assertIsNone(execution.completed_at)
        self.assertEqual((execution.executed_by, execution.created_by), (self.chef_section, self.chef_section))

    def test_execution_sur_occurrence_hors_perimetre_refusee(self):
        r = self.client_a.post("/api/maintenance/executions/", {"occurrence": self.occ_b.pk}, format="json")
        self.assertEqual(r.status_code, 403)

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
        self.assertEqual(r.status_code, 403)

    def test_plan_sur_materiel_hors_perimetre_refuse(self):
        r = self.client_a.post(
            "/api/maintenance/plans/", {"scope": "ASSET", "asset": str(self.asset_b.pk), "name": "X"}, format="json",
        )
        self.assertEqual(r.status_code, 403)
        r = self.client_a.post(
            "/api/maintenance/plans/", {"scope": "ASSET", "asset": str(self.asset_a.pk), "name": "Y"}, format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(MaintenancePlan.objects.get(pk=r.data["id"]).created_by, self.chef_section)


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

    def test_reservations_d_une_session_non_modifiables_par_l_api(self):
        session = TrainingSession.objects.create(course=self.course, scheduled_at=timezone.now() + timedelta(days=5))
        r = self.client_cdt.patch(
            f"/api/training/sessions/{session.pk}/", {"reservations": [self.marin.pk], "location": "Salle"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        session.refresh_from_db()
        self.assertEqual(session.location, "Salle")
        self.assertEqual(session.reservations.count(), 0)

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
        self.equipage_a = Equipage.objects.create(ship=self.ship_a, nom="Bleu")
        self.equipage_b = Equipage.objects.create(ship=self.ship_b, nom="Rouge")
        self.profil = self.autre.profile

    def _patch(self, client, donnees):
        return client.patch(f"/api/accounts/profiles/{self.profil.pk}/", donnees, format="json")

    def test_admin_navire_ne_peut_pas_creer_un_master_admin(self):
        r = self._patch(self.client_admin, {"role": Roles.MASTER_ADMIN})
        self.assertEqual(r.status_code, 400)
        self.profil.refresh_from_db()
        self.assertEqual(self.profil.role, Roles.EQUIPIER)

    def test_equipage_d_un_autre_navire_refuse(self):
        r = self._patch(self.client_admin, {"role": Roles.EQUIPIER, "equipage": self.equipage_b.pk})
        self.assertEqual(r.status_code, 400)
        self.profil.refresh_from_db()
        self.assertIsNone(self.profil.equipage)

    def test_equipage_du_bon_navire_accepte(self):
        r = self._patch(self.client_admin, {"role": Roles.EQUIPIER, "equipage": self.equipage_a.pk})
        self.assertEqual(r.status_code, 200, r.content)
        self.profil.refresh_from_db()
        self.assertEqual(self.profil.equipage, self.equipage_a)

    def test_compte_lie_et_secteurs_autorises_non_modifiables(self):
        r = self._patch(
            self.client_admin,
            {"role": Roles.EQUIPIER, "user": {"username": "pirate"}, "allowed_sectors": [self.sector_b.pk]},
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.profil.refresh_from_db()
        self.assertEqual(self.profil.user, self.autre)
        self.assertEqual(self.profil.allowed_sectors.count(), 0)
        self.autre.refresh_from_db()
        self.assertEqual(self.autre.username, "autre_sec")


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
