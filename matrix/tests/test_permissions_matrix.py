"""Matrice de tests de permissions par rôle x ressource (les 8 niveaux de rôle).

Tâche Notion « Matrice de tests de permissions par rôle × ressource » (Phase 0
- Assainissement) : construit une suite systématique couvrant, pour les
ressources principales du projet (Installation, Asset, InstallationMaintenance,
CorrectiveTicket, StockPiece, TrainingCourse, PersonalEvent, Zone), le seuil de
rôle minimal requis par action d'écriture (création, modification, suppression,
action métier sensible), en testant les 8 niveaux de rôle un par un — pas
seulement deux rôles de comparaison, ce que fait déjà
assets/tests/test_rbac_assets.py (repris ici comme modèle, cf. commentaire
Notion de la tâche). Objectif : qu'un changement futur de seuil (RoleLevel,
MAINTENANCE_WRITE_ACTIONS, etc.) fasse immédiatement échouer un test, plutôt
que d'être découvert en production.

Le scoping par périmètre (navire/service/secteur/section) est volontairement
hors périmètre de ce fichier : il est déjà couvert par les tests
*_scope_leak.py de chaque app. Ici, les 8 utilisateurs de test partagent tous
le même navire/service/secteur/section, pour isoler la seule variable RÔLE et
éviter qu'un refus soit dû au périmètre plutôt qu'au rôle.

La formation (TrainingCourse) dispose déjà d'une suite RBAC très fournie
(training/tests/, plus d'une quinzaine de fichiers) qui couvre en détail le
circuit d'approbation « formation bord » (Circuit C) et la désignation des
référents : seul le seuil générique d'écriture (RolePermission) est revérifié
ici sur les 8 rôles, pour compléter la matrice sans dupliquer cette
couverture déjà existante.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import GradeChoice, UserProfile
from assets.models import Asset, AssetFolder, AssetType, Deck, Installation, InstallationMaintenance
from calendar_app.models import PersonalEvent
from logistics.models import CorrectiveTicket, StockPiece
from matrix.core.role_thresholds import invalidate_cache
from matrix.core.roles import RoleLevel
from org.models import RoleThresholdConfig, Sector, Section, Service, Ship
from training.models import TrainingCourse

# Ordre croissant du niveau hiérarchique, du plus bas (Équipier) au plus haut
# (Administrateur général) — mêmes 8 niveaux que matrix/core/roles.py.
ROLES = list(RoleLevel)


class MatricePermissionsTestCase(TestCase):
    """Base commune à toute la matrice : un seul périmètre (navire/service/
    secteur/section) et un utilisateur par niveau de rôle, tous rattachés à
    ce même périmètre pour isoler la variable ROLE du scoping par périmètre."""

    @classmethod
    def setUpTestData(cls):
        cls.ship = Ship.objects.create(name="Porte-avions Matrice", code="PA-MTX")
        cls.service = Service.objects.create(name="Service Matrice", ship=cls.ship)
        cls.sector = Sector.objects.create(name="Secteur Matrice", service=cls.service)
        cls.section = Section.objects.create(name="Section Matrice", sector=cls.sector)
        cls.users = {}
        for role in ROLES:
            user = User.objects.create_user(username=f"mtx_{role.name.lower()}", password="pass")
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": role.name,
                    "ship": cls.ship,
                    "service": cls.service,
                    "sector": cls.sector,
                    "section": cls.section,
                },
            )
            cls.users[role] = user

    def client_pour(self, role, api=False):
        client = APIClient() if api else Client()
        client.login(username=f"mtx_{role.name.lower()}", password="pass")
        return client

    def assert_seuil(self, seuil, executer, api=False):
        """Pour chacun des 8 rôles, exécute `executer(client, role)` — qui doit
        renvoyer True si l'action a été acceptée, False si elle a été refusée
        — et vérifie que le résultat correspond au seuil de rôle attendu
        (autorisé si et seulement si role >= seuil)."""
        for role in ROLES:
            with self.subTest(role=role.name):
                client = self.client_pour(role, api=api)
                accepte = executer(client, role)
                attendu = role >= seuil
                self.assertEqual(
                    accepte, attendu,
                    f"Rôle {role.name} (niveau {role.value}) : accès attendu="
                    f"{attendu}, obtenu={accepte} (seuil requis : {seuil.name}).",
                )


class AssetMatriceTests(MatricePermissionsTestCase):
    """Matériel mobile (Asset) : création/modification réservées à
    CHEF_SECTION+, suppression réservée à CHEF_SERVICE+ par défaut —
    seuils configurables par navire (assets/web_views.py
    ::AssetListView.ACTION_VERS_SEUIL, matrix/core/role_thresholds.py)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=cls.sector)
        cls.asset = Asset.objects.create(
            asset_type=cls.asset_type, ship=cls.ship, service=cls.service, sector=cls.sector,
            section=cls.section, serial_number="SN-MTX", internal_id="INT-MTX",
        )

    def test_lecture_liste_ouverte_a_tout_role(self):
        """Lecture (liste) : ouverte à tout utilisateur connecté, quel que
        soit son rôle (RolePermission/ScopedQuerySetMixin ne restreignent la
        lecture que par périmètre, jamais par rôle)."""
        for role in ROLES:
            with self.subTest(role=role.name):
                r = self.client_pour(role).get("/assets/")
                self.assertEqual(r.status_code, 200)

    def test_lecture_detail_ouverte_a_tout_role(self):
        """Lecture (détail) : même constat que la liste — AssetDetailView
        n'ajoute aucune restriction de rôle sur le GET, seul le périmètre
        (ScopedQuerySetMixin) est vérifié."""
        for role in ROLES:
            with self.subTest(role=role.name):
                r = self.client_pour(role).get(f"/assets/{self.asset.id}/")
                self.assertEqual(r.status_code, 200)

    def test_creation_asset(self):
        def executer(client, role):
            r = client.post("/assets/", {
                "action": "create_asset",
                "internal_id": f"INT-{role.name}",
                "serial_number": f"SN-{role.name}",
                "designation": "Extincteur test",
                "ship_id": str(self.ship.id),
                "service_id": str(self.service.id),
                "sector_id": str(self.sector.id),
                "asset_type_id": str(self.asset_type.id),
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            return Asset.objects.filter(internal_id=f"INT-{role.name}").exists()
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer)

    def test_modification_asset(self):
        def executer(client, role):
            r = client.post("/assets/", {
                "action": "edit_asset",
                "pk": str(self.asset.id),
                "internal_id": self.asset.internal_id,
                "serial_number": self.asset.serial_number,
                "designation": f"Modifié par {role.name}",
                "ship_id": str(self.ship.id),
                "service_id": str(self.service.id),
                "sector_id": str(self.sector.id),
                "section_id": str(self.section.id),
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            self.asset.refresh_from_db()
            return self.asset.designation == f"Modifié par {role.name}"
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer)

    def test_suppression_asset(self):
        def executer(client, role):
            a = Asset.objects.create(
                asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
                section=self.section, serial_number=f"SN-DEL-{role.name}", internal_id=f"INT-DEL-{role.name}",
            )
            r = client.post("/assets/", {"action": "delete_asset", "pk": str(a.id)})
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            return not Asset.objects.filter(pk=a.id).exists()
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer)

    def test_suppression_asset_via_api_reservee_chef_service(self):
        """Régression du refus du Tech Lead : AssetViewSet (assets/views.py)
        utilisait le seuil générique d'écriture (CHEF_SECTION, RolePermission)
        pour DELETE, alors que le web (AssetListView.ACTION_VERS_SEUIL
        ['delete_asset']) exige CHEF_SERVICE — un chef de section bloqué à
        l'écran pouvait donc supprimer le même matériel en appelant
        directement l'API. role_threshold_action_delete='asset_gestion_avancee'
        aligne les deux chemins sur la même clé configurable."""
        def executer(client, role):
            a = Asset.objects.create(
                asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
                section=self.section, serial_number=f"SN-API-DEL-{role.name}", internal_id=f"INT-API-DEL-{role.name}",
            )
            r = client.delete(f"/api/assets/assets/{a.id}/")
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 204)
            return not Asset.objects.filter(pk=a.id).exists()
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer, api=True)


class InstallationMatriceTests(MatricePermissionsTestCase):
    """Installation fixe : création/modification réservées à CHEF_SECTION+,
    suppression réservée à CHEF_SERVICE+ par défaut — seuils configurables
    par navire (assets/web_views.py::InstallationListView.ACTION_VERS_SEUIL,
    matrix/core/role_thresholds.py)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.installation = Installation.objects.create(
            designation="Groupe électrogène", ship=cls.ship, service=cls.service, sector=cls.sector,
            section=cls.section,
        )

    def test_lecture_liste_ouverte_a_tout_role(self):
        """Lecture (liste) : ouverte à tout utilisateur connecté, même
        constat que pour AssetListView (seul le périmètre est filtré)."""
        for role in ROLES:
            with self.subTest(role=role.name):
                r = self.client_pour(role).get("/installations/")
                self.assertEqual(r.status_code, 200)

    def test_lecture_detail_ouverte_a_tout_role(self):
        """Lecture (détail) : InstallationDetailView n'ajoute aucune
        restriction de rôle sur le GET, seul le périmètre est vérifié."""
        for role in ROLES:
            with self.subTest(role=role.name):
                r = self.client_pour(role).get(f"/installations/{self.installation.id}/")
                self.assertEqual(r.status_code, 200)

    def test_creation_installation(self):
        def executer(client, role):
            r = client.post("/installations/", {
                "action": "create_installation",
                "designation": f"Pompe {role.name}",
                "ship_id": str(self.ship.id),
                "service_id": str(self.service.id),
                "sector_id": str(self.sector.id),
                "section_id": str(self.section.id),
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            return Installation.objects.filter(designation=f"Pompe {role.name}").exists()
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer)

    def test_modification_installation(self):
        def executer(client, role):
            r = client.post("/installations/", {
                "action": "edit_installation",
                "pk": str(self.installation.id),
                "designation": f"Groupe électrogène ({role.name})",
                "ship_id": str(self.ship.id),
                "service_id": str(self.service.id),
                "sector_id": str(self.sector.id),
                "section_id": str(self.section.id),
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            self.installation.refresh_from_db()
            return self.installation.designation == f"Groupe électrogène ({role.name})"
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer)

    def test_suppression_installation(self):
        def executer(client, role):
            it = Installation.objects.create(
                designation=f"À supprimer ({role.name})", ship=self.ship, service=self.service, sector=self.sector,
                section=self.section,
            )
            r = client.post("/installations/", {"action": "delete_installation", "pk": str(it.id)})
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            return not Installation.objects.filter(pk=it.id).exists()
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer)


class InstallationMaintenanceMatriceTests(MatricePermissionsTestCase):
    """Tâche d'entretien d'une installation : écriture réservée à CHEF_SERVICE+
    (assets/web_views.py::InstallationDetailView.MAINTENANCE_WRITE_ACTIONS),
    seuil plus élevé que la fiche d'installation elle-même — création,
    modification et suppression testées, aux trois mêmes seuil (l'action
    métier « sensible » de ce sous-domaine, la remise en service protégée par
    signature, porte sur le ticket correctif et non sur cette tâche
    d'entretien, cf. CorrectiveTicketMatriceTests ci-dessous)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.installation = Installation.objects.create(
            designation="Pompe A", ship=cls.ship, service=cls.service, sector=cls.sector,
            section=cls.section,
        )

    def test_creation_maintenance(self):
        def executer(client, role):
            r = client.post(f"/installations/{self.installation.id}/", {
                "action": "add_maintenance", "title": f"Graissage {role.name}", "tab": "entretien",
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            return InstallationMaintenance.objects.filter(title=f"Graissage {role.name}").exists()
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer)

    def test_modification_maintenance(self):
        def executer(client, role):
            m = InstallationMaintenance.objects.create(
                installation=self.installation, title=f"Avant modif {role.name}", periodicity="M",
            )
            r = client.post(f"/installations/{self.installation.id}/", {
                "action": "edit_maintenance", "maintenance_id": str(m.id),
                "title": f"Modifié par {role.name}", "tab": "entretien",
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            m.refresh_from_db()
            return m.title == f"Modifié par {role.name}"
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer)

    def test_suppression_maintenance(self):
        def executer(client, role):
            m = InstallationMaintenance.objects.create(
                installation=self.installation, title=f"À supprimer {role.name}", periodicity="M",
            )
            r = client.post(f"/installations/{self.installation.id}/", {
                "action": "delete_maintenance", "maintenance_id": str(m.id), "tab": "entretien",
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            return not InstallationMaintenance.objects.filter(pk=m.id).exists()
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer)


class CorrectiveTicketMatriceTests(MatricePermissionsTestCase):
    """Ticket correctif : signalement ouvert à tout marin connecté (EQUIPIER
    compris), transitions de statut réservées à CHEF_SECTION+, remise en
    service protégée en plus par une signature (mot de passe), quel que soit
    le rôle de l'appelant (logistics/web_views.py)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.asset_type = AssetType.objects.create(name="Groupe", category="Propulsion", sector=cls.sector)
        cls.asset = Asset.objects.create(
            asset_type=cls.asset_type, ship=cls.ship, service=cls.service, sector=cls.sector,
            section=cls.section, serial_number="SN-TCK", internal_id="INT-TCK",
        )

    def test_signalement_ouvert_a_tout_role(self):
        """Signalement d'une anomalie : accessible à tout marin connecté, y
        compris un simple ÉQUIPIER (TicketCreateView, docstring explicite)."""
        def executer(client, role):
            r = client.post(f"/logistics/tickets/creer/{self.asset.id}/", {
                "description": f"Anomalie constatée par {role.name}", "severity": 3,
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            return CorrectiveTicket.objects.filter(description=f"Anomalie constatée par {role.name}").exists()
        self.assert_seuil(RoleLevel.EQUIPIER, executer)

    def test_lecture_detail_ouverte_a_tout_role_dans_le_perimetre(self):
        """Lecture (détail) : TicketDetailView ne restreint que par périmètre
        (build_scope_q sur l'actif du ticket), pas par rôle ni par
        assignation — contrairement à la liste par défaut ("mes tickets")."""
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Ticket consultable")
        for role in ROLES:
            with self.subTest(role=role.name):
                r = self.client_pour(role).get(f"/logistics/tickets/{ticket.id}/")
                self.assertEqual(r.status_code, 200)

    def test_transition_statut_reservee_chef_section(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Panne test")

        def executer(client, role):
            r = client.post(f"/logistics/tickets/{ticket.id}/transition/", {"status": "DIAGNOSED"})
            return r.status_code != 403
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer)

    def test_remise_en_service_exige_une_signature_quel_que_soit_le_role(self):
        """Action métier sensible : la remise en service (RETURNED_TO_SERVICE)
        exige le mot de passe de l'appelant, en plus du seuil CHEF_SECTION déjà
        vérifié ci-dessus — un CHEF_SERVICE avec un mot de passe erroné ne doit
        ni changer le statut ni enregistrer de signature."""
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Panne à réparer")
        chef = self.users[RoleLevel.CHEF_SERVICE]
        client = self.client_pour(RoleLevel.CHEF_SERVICE)

        r = client.post(f"/logistics/tickets/{ticket.id}/transition/", {
            "status": "RETURNED_TO_SERVICE", "mot_de_passe": "mauvais_mot_de_passe",
        })
        self.assertEqual(r.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "REPORTED")
        self.assertIsNone(ticket.valide_par)

        r = client.post(f"/logistics/tickets/{ticket.id}/transition/", {
            "status": "RETURNED_TO_SERVICE", "mot_de_passe": "pass",
        })
        self.assertEqual(r.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "RETURNED_TO_SERVICE")
        self.assertEqual(ticket.valide_par, chef)
        self.assertIsNotNone(ticket.date_validation)

    def test_suppression_ticket_interdite_via_api_quel_que_soit_le_role(self):
        """Régression du refus du Tech Lead : CorrectiveTicketViewSet héritait de
        ModelViewSet sans aucune restriction de méthode ni override de destroy(),
        si bien que `DELETE /api/logistics/tickets/{id}/` supprimait réellement le
        ticket dès le seuil générique CHEF_SECTION atteint — contournant tout le
        cycle de statuts et le REX obligatoire à CLOSED. Un ticket correctif ne
        doit jamais pouvoir disparaître, quel que soit le rôle appelant : seul le
        cycle de statuts (transition()) fait foi (SuppressionInterditeMixin,
        matrix/core/mixins.py)."""
        for role in ROLES:
            with self.subTest(role=role.name):
                ticket = CorrectiveTicket.objects.create(
                    asset=self.asset, description=f"Ticket {role.name}",
                )
                client = self.client_pour(role, api=True)
                r = client.delete(f"/api/logistics/tickets/{ticket.id}/")
                # 403 pour un rôle sous le seuil d'écriture générique (RolePermission
                # tranche AVANT même la résolution de la méthode HTTP), 405 au-delà
                # (DELETE retiré de http_method_names) : dans tous les cas, jamais
                # supprimé — c'est le seul point qui compte ici.
                self.assertIn(r.status_code, (403, 405))
                self.assertTrue(CorrectiveTicket.objects.filter(pk=ticket.id).exists())


class StockPieceMatriceTests(MatricePermissionsTestCase):
    """Stock de pièces : lecture ouverte à tout rôle, création/modification
    réservées à CHEF_SECTION+ (logistics/web_views.py::StockPieceListView,
    même seuil que les autres actions d'écriture du module logistique). Pas
    de suppression exposée pour cette ressource (le stock se corrige par
    quantité, pas par suppression de fiche) : action non applicable, donc
    non testée ici."""

    def test_lecture_ouverte_a_tout_role(self):
        for role in ROLES:
            with self.subTest(role=role.name):
                r = self.client_pour(role).get("/logistics/stock/")
                self.assertEqual(r.status_code, 200)

    def test_creation_piece(self):
        def executer(client, role):
            r = client.post("/logistics/stock/", {
                "action": "create_piece",
                "reference": f"REF-{role.name}",
                "designation": "Joint torique",
                "sector_id": str(self.sector.id),
                "quantite": 10,
                "quantite_minimale": 2,
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            return StockPiece.objects.filter(reference=f"REF-{role.name}").exists()
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer)

    def test_modification_piece(self):
        def executer(client, role):
            # section=self.section obligatoire : le périmètre des 8 utilisateurs
            # de test est scopé jusqu'à la section (scope_filters_for_user prend
            # le niveau le plus précis renseigné sur le profil) — une pièce sans
            # section ne serait pas retrouvée par get_queryset() dans la vue.
            piece = StockPiece.objects.create(
                reference=f"REF-MOD-{role.name}", designation="Avant modification",
                sector=self.sector, service=self.service, ship=self.ship, section=self.section,
                quantite=5, quantite_minimale=1,
            )
            r = client.post("/logistics/stock/", {
                "action": "edit_piece",
                "pk": str(piece.id),
                "reference": piece.reference,
                "designation": f"Modifié par {role.name}",
                "sector_id": str(self.sector.id),
                "section_id": str(self.section.id),
                "quantite": 5,
                "quantite_minimale": 1,
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            piece.refresh_from_db()
            return piece.designation == f"Modifié par {role.name}"
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer)


class PlanNaviePositionMatriceTests(MatricePermissionsTestCase):
    """Positionnement précis du matériel sur le plan visuel du navire
    (épingle x/y, cf. Asset.plan_deck/position_x/position_y) : configuration
    (placement, repositionnement, retrait) réservée à CHEF_SERVICE+ (assets/
    web_views.py::_peut_configurer_plan_navire), au même seuil que
    l'ancien système de zones qu'elle remplace. La consultation
    (PlanNavireVueDeckView) est en revanche ouverte à tous les rôles, seul le
    périmètre navire est vérifié."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.deck = Deck.objects.create(ship=cls.ship, name="Pont principal", order=1)
        cls.asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=cls.sector)

    def test_lecture_ouverte_a_tout_role(self):
        for role in ROLES:
            with self.subTest(role=role.name):
                r = self.client_pour(role).get(f"/assets/plan-navire/{self.deck.id}/")
                self.assertEqual(r.status_code, 200)

    def test_placement_dune_epingle(self):
        def executer(client, role):
            materiel = Asset.objects.create(
                asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
                internal_id=f"EPINGLE-{role.name}",
            )
            r = client.post(f"/assets/plan/{self.deck.id}/", {
                "action": "place_pin", "asset_id": str(materiel.id), "x": "10", "y": "20",
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            materiel.refresh_from_db()
            return materiel.plan_deck_id == self.deck.id and materiel.position_x == 10 and materiel.position_y == 20
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer)

    def test_repositionnement_dune_epingle(self):
        def executer(client, role):
            materiel = Asset.objects.create(
                asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
                internal_id=f"REPOS-{role.name}", plan_deck=self.deck, position_x=10, position_y=10,
            )
            r = client.post(f"/assets/plan/{self.deck.id}/", {
                "action": "place_pin", "asset_id": str(materiel.id), "x": "60", "y": "70",
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            materiel.refresh_from_db()
            return materiel.position_x == 60 and materiel.position_y == 70
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer)

    def test_retrait_dune_epingle(self):
        def executer(client, role):
            materiel = Asset.objects.create(
                asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
                internal_id=f"RETRAIT-{role.name}", plan_deck=self.deck, position_x=10, position_y=10,
            )
            r = client.post(f"/assets/plan/{self.deck.id}/", {
                "action": "remove_pin", "asset_id": str(materiel.id),
            })
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 302)
            materiel.refresh_from_db()
            return materiel.plan_deck_id is None and materiel.position_x is None
        self.assert_seuil(RoleLevel.CHEF_SERVICE, executer)


class TrainingCourseMatriceTests(MatricePermissionsTestCase):
    """Formation (catalogue général, non gérée par un bord) : lecture (liste
    et détail) ouverte à tout rôle (catalogue global, RolePermission laisse
    passer les méthodes sûres sans condition), création/modification soumises
    au seuil générique d'écriture CHEF_SECTION+ (RolePermission par défaut,
    training/views.py::TrainingCourseViewSet). L'action métier sensible de ce
    domaine — la validation d'une formation pour un marin (TrainingRecord) —
    n'est pas régie par ce seuil générique mais par le contrôle par référent
    (peut_valider_formation), déjà testé sur les 8 rôles dans
    training/tests/test_validation_formation.py (cf. docstring de module
    ci-dessus) : non dupliqué ici. Pas de suppression testée : le circuit
    d'approbation (Circuit C) interdit déjà toute suppression directe d'une
    formation gérée par un bord, hors périmètre de cette matrice générique."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.course = TrainingCourse.objects.create(title="Formation générique", validity_days=365)

    def test_lecture_ouverte_a_tout_role(self):
        for role in ROLES:
            with self.subTest(role=role.name):
                client = self.client_pour(role, api=True)
                r_liste = client.get("/api/training/courses/")
                self.assertEqual(r_liste.status_code, 200)
                r_detail = client.get(f"/api/training/courses/{self.course.id}/")
                self.assertEqual(r_detail.status_code, 200)

    def test_creation_formation_generique(self):
        def executer(client, role):
            r = client.post(
                "/api/training/courses/",
                {"title": f"Formation créée par {role.name}"},
                format="json",
            )
            if r.status_code == 403:
                return False
            self.assertEqual(r.status_code, 201)
            return TrainingCourse.objects.filter(title=f"Formation créée par {role.name}").exists()
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer, api=True)

    def test_modification_formation_generique(self):
        def executer(client, role):
            r = client.patch(
                f"/api/training/courses/{self.course.id}/",
                {"title": f"Titre modifié par {role.name}"},
                format="json",
            )
            return r.status_code != 403
        self.assert_seuil(RoleLevel.CHEF_SECTION, executer, api=True)


class PersonalEventMatriceTests(MatricePermissionsTestCase):
    """Événement personnel du calendrier : espace personnel (principe n°3
    CLAUDE.md), l'accès en écriture ne dépend jamais du rôle mais uniquement
    de la propriété de l'objet — même un MASTER_ADMIN ne peut pas modifier
    l'agenda personnel d'un autre marin (calendar_app/views.py, filtre
    `owner=request.user` sans dérogation de rôle)."""

    def test_lecture_calendrier_ouverte_a_tout_role(self):
        """Lecture : le calendrier central est accessible à tout rôle sans
        restriction (CalendarView, docstring explicite — vue globale par
        défaut, cf. citation ci-dessus)."""
        for role in ROLES:
            with self.subTest(role=role.name):
                r = self.client_pour(role).get("/calendar/")
                self.assertEqual(r.status_code, 200)

    def test_tout_role_peut_gerer_son_propre_evenement(self):
        for role in ROLES:
            with self.subTest(role=role.name):
                client = self.client_pour(role)

                r = client.post("/calendar/personnel/enregistrer/", {
                    "title": "RDV médical", "starts_at": "2026-10-01T09:00",
                })
                self.assertEqual(r.status_code, 302)
                evenement = PersonalEvent.objects.get(owner=self.users[role], title="RDV médical")

                r = client.post("/calendar/personnel/enregistrer/", {
                    "id": str(evenement.id), "title": "RDV médical modifié", "starts_at": "2026-10-01T10:00",
                })
                self.assertEqual(r.status_code, 302)
                evenement.refresh_from_db()
                self.assertEqual(evenement.title, "RDV médical modifié")

                r = client.post(f"/calendar/personnel/{evenement.id}/supprimer/")
                self.assertEqual(r.status_code, 302)
                self.assertFalse(PersonalEvent.objects.filter(pk=evenement.id).exists())

    def test_aucun_role_ne_peut_toucher_levenement_dun_autre(self):
        proprietaire = self.users[RoleLevel.EQUIPIER]
        evenement = PersonalEvent.objects.create(
            owner=proprietaire, title="Événement privé",
            starts_at=timezone.now(), ends_at=timezone.now() + timedelta(hours=1),
        )
        for role in ROLES:
            if role == RoleLevel.EQUIPIER:
                continue  # c'est le propriétaire lui-même, cas déjà couvert ci-dessus
            with self.subTest(role=role.name):
                client = self.client_pour(role)
                r = client.post("/calendar/personnel/enregistrer/", {
                    "id": str(evenement.id), "title": "Piraté", "starts_at": "2026-10-01T10:00",
                })
                self.assertEqual(r.status_code, 404)
                r = client.post(f"/calendar/personnel/{evenement.id}/supprimer/")
                self.assertEqual(r.status_code, 404)
        evenement.refresh_from_db()
        self.assertEqual(evenement.title, "Événement privé")


class SeuilRoleConfigurableTests(MatricePermissionsTestCase):
    """Tâche Notion « Seuils de rôle configurables par navire » : prouve
    qu'un changement de RoleThresholdConfig modifie RÉELLEMENT le
    comportement de l'API/du web, pas seulement que la configuration existe
    en base — sur les trois familles de seuils configurables (portée navire
    côté API DRF, portée navire côté web, portée GLOBALE flotte)."""

    def tearDown(self):
        # Invalide le cache des seuils entre chaque test (une configuration
        # créée dans un test ne doit jamais fuiter sur le suivant).
        invalidate_cache(self.ship.id)
        invalidate_cache(None)
        super().tearDown()

    def test_seuil_navire_api_delete_asset_abaisse_a_chef_section(self):
        """Par défaut, la suppression d'un matériel via l'API (asset_gestion_avancee)
        exige CHEF_SERVICE (AssetViewSet.role_threshold_action_delete). Un
        ADMIN_NAVIRE abaisse ce seuil à CHEF_SECTION pour son navire : un
        CHEF_SECTION peut désormais supprimer via l'API, alors qu'il en était
        incapable avant la reconfiguration."""
        asset_type = AssetType.objects.create(name="Touret", category="Manutention", sector=self.sector)
        chef_section = self.client_pour(RoleLevel.CHEF_SECTION, api=True)

        # Avant configuration : seuil par défaut CHEF_SERVICE, refusé à CHEF_SECTION.
        asset = Asset.objects.create(
            asset_type=asset_type, ship=self.ship, service=self.service, sector=self.sector,
            section=self.section, serial_number="SN-AVANT", internal_id="INT-AVANT",
        )
        r = chef_section.delete(f"/api/assets/assets/{asset.id}/")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Asset.objects.filter(pk=asset.id).exists())

        # Reconfiguration du navire : asset_gestion_avancee abaissé à CHEF_SECTION.
        RoleThresholdConfig.objects.create(
            ship=self.ship, thresholds={"asset_gestion_avancee": "CHEF_SECTION"},
        )
        invalidate_cache(self.ship.id)

        # Après configuration : le même rôle, sur le même navire, réussit désormais.
        r = chef_section.delete(f"/api/assets/assets/{asset.id}/")
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Asset.objects.filter(pk=asset.id).exists())

    def test_seuil_navire_web_asset_ecriture_simple_releve_a_chef_service(self):
        """Par défaut, la création d'un matériel côté web (asset_ecriture_simple)
        exige CHEF_SECTION. Un ADMIN_NAVIRE relève ce seuil à CHEF_SERVICE
        pour son navire : un CHEF_SECTION, auparavant autorisé, se retrouve
        refusé sur ce même navire après la reconfiguration."""
        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.sector)
        chef_section = self.client_pour(RoleLevel.CHEF_SECTION)

        payload = {
            "action": "create_asset", "internal_id": "INT-RELEVE", "serial_number": "SN-RELEVE",
            "designation": "Matériel test", "ship_id": str(self.ship.id), "service_id": str(self.service.id),
            "sector_id": str(self.sector.id), "asset_type_id": str(asset_type.id),
        }

        # Avant configuration : seuil par défaut CHEF_SECTION, autorisé.
        r = chef_section.post("/assets/", payload)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Asset.objects.filter(internal_id="INT-RELEVE").exists())

        # Reconfiguration du navire : asset_ecriture_simple relevé à CHEF_SERVICE.
        RoleThresholdConfig.objects.create(
            ship=self.ship, thresholds={"asset_ecriture_simple": "CHEF_SERVICE"},
        )
        invalidate_cache(self.ship.id)

        # Après configuration : le même rôle, sur le même navire, est refusé.
        payload["internal_id"] = "INT-RELEVE-2"
        payload["serial_number"] = "SN-RELEVE-2"
        r = chef_section.post("/assets/", payload)
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Asset.objects.filter(internal_id="INT-RELEVE-2").exists())

    def test_seuil_navire_web_asset_ecriture_simple_abaisse_a_equipier(self):
        """Régression du refus du Tech Lead : create_folder/create_asset dans
        AssetListView.post() (assets/web_views.py) appelaient en plus, de façon
        redondante, l'ancienne fonction _peut_gerer_materiel codée en dur sur
        CHEF_SECTION — si bien qu'abaisser asset_ecriture_simple sous ce seuil
        via RoleThresholdConfig restait sans effet réel : le contrôle en tête
        de post() laissait passer, mais l'appel redondant bloquait quand même.
        Ce test ABAISSE le seuil (contrairement aux deux tests précédents qui
        ne font que le relever) et prouve qu'un ÉQUIPIER, normalement
        insuffisant, peut désormais créer un dossier et un matériel."""
        asset_type = AssetType.objects.create(name="Multimètre", category="Mesure", sector=self.sector)
        equipier = self.client_pour(RoleLevel.EQUIPIER)

        # Avant configuration : seuil par défaut CHEF_SECTION, refusé à l'ÉQUIPIER.
        r = equipier.post("/assets/", {"action": "create_folder", "name": "Dossier avant"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(AssetFolder.objects.filter(name="Dossier avant").exists())

        # Reconfiguration du navire : asset_ecriture_simple abaissé à EQUIPIER.
        RoleThresholdConfig.objects.create(
            ship=self.ship, thresholds={"asset_ecriture_simple": "EQUIPIER"},
        )
        invalidate_cache(self.ship.id)

        # Après configuration : le même ÉQUIPIER, sur le même navire, réussit désormais.
        r = equipier.post("/assets/", {"action": "create_folder", "name": "Dossier après"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(AssetFolder.objects.filter(name="Dossier après").exists())

        r = equipier.post("/assets/", {
            "action": "create_asset", "internal_id": "INT-EQUIPIER", "serial_number": "SN-EQUIPIER",
            "designation": "Matériel créé par équipier", "ship_id": str(self.ship.id),
            "service_id": str(self.service.id), "sector_id": str(self.sector.id),
            "asset_type_id": str(asset_type.id),
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Asset.objects.filter(internal_id="INT-EQUIPIER").exists())

    def test_seuil_navire_web_installation_ecriture_simple_abaisse_a_equipier(self):
        """Même régression que ci-dessus, côté InstallationListView.post() :
        create_installation appelait aussi _peut_gerer_materiel en plus du
        contrôle configurable en tête de post(), rendant installation_ecriture_simple
        sans effet réel une fois abaissé sous CHEF_SECTION."""
        equipier = self.client_pour(RoleLevel.EQUIPIER)
        payload = {
            "action": "create_installation", "designation": "Pompe créée par équipier",
            "ship_id": str(self.ship.id), "service_id": str(self.service.id),
            "sector_id": str(self.sector.id), "section_id": str(self.section.id),
        }

        # Avant configuration : seuil par défaut CHEF_SECTION, refusé à l'ÉQUIPIER.
        r = equipier.post("/installations/", payload)
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Installation.objects.filter(designation="Pompe créée par équipier").exists())

        # Reconfiguration du navire : installation_ecriture_simple abaissé à EQUIPIER.
        RoleThresholdConfig.objects.create(
            ship=self.ship, thresholds={"installation_ecriture_simple": "EQUIPIER"},
        )
        invalidate_cache(self.ship.id)

        # Après configuration : le même ÉQUIPIER, sur le même navire, réussit désormais.
        r = equipier.post("/installations/", payload)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Installation.objects.filter(designation="Pompe créée par équipier").exists())

    def test_seuil_global_referentiel_ne_depend_pas_du_navire(self):
        """referentiel_global_ecriture (grades/spécialités, référentiel commun à
        toute la flotte) est de portée GLOBALE : sa reconfiguration (ship=None)
        s'applique quel que soit le navire de l'appelant, sans qu'il soit
        nécessaire de créer une RoleThresholdConfig par navire."""
        chef_section = self.client_pour(RoleLevel.CHEF_SECTION, api=True)

        # Avant configuration : seuil par défaut MASTER_ADMIN, refusé à CHEF_SECTION.
        r = chef_section.post("/api/accounts/grades/", {"name": "Grade avant"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(GradeChoice.objects.filter(name="Grade avant").exists())

        # Reconfiguration GLOBALE (ship=None) : abaisse referentiel_global_ecriture à CHEF_SECTION.
        RoleThresholdConfig.objects.create(
            ship=None, thresholds={"referentiel_global_ecriture": "CHEF_SECTION"},
        )
        invalidate_cache(None)

        r = chef_section.post("/api/accounts/grades/", {"name": "Grade après"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(GradeChoice.objects.filter(name="Grade après").exists())
