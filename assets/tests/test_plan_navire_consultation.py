"""[FEAT] Rendu du plan interactif : navigation entre ponts, code couleur par
état, clic vers la fiche du matériel.

Sous-tâche 3/3 (dernière) du plan visuel du navire : la sous-tâche 1 a livré
le modèle de données (Deck, positionnement précis sur Asset), la sous-tâche 2
l'éditeur réservé aux chefs. Cette sous-tâche livre la page de consultation,
ouverte à tous les rôles. Remplace l'ancien rendu par zones agrégées
(Zone.etat_materiel, supprimé) par un rendu épingle par épingle
(Asset.etat_plan), une épingle représentant désormais un seul matériel.
"""
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Deck
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


def _image_1x1_png():
    # PNG 1x1 minimal valide, même fixture que test_plan_navire_web.py.
    contenu = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de0000000c4944415478da6360606060000000050001a5f645400000000049454e44ae426082"
    )
    return SimpleUploadedFile("plan.png", contenu, content_type="image/png")


class AssetEtatPlanTests(TestCase):
    """Calcul de l'état d'un matériel pour l'affichage de son épingle
    (Asset.etat_plan)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)

    def _creer_asset(self, status="OK"):
        return Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector, status=status,
        )

    def test_materiel_ok_est_vert(self):
        materiel = self._creer_asset(status="OK")
        self.assertEqual(materiel.etat_plan, Asset.ETAT_OK)

    def test_materiel_hors_service_est_rouge(self):
        materiel = self._creer_asset(status="OUT_OF_SERVICE")
        self.assertEqual(materiel.etat_plan, Asset.ETAT_DANGER)

    def test_materiel_defectueux_est_rouge(self):
        materiel = self._creer_asset(status="FAULTY")
        self.assertEqual(materiel.etat_plan, Asset.ETAT_DANGER)

    def test_materiel_avec_controle_en_retard_est_orange(self):
        materiel = self._creer_asset(status="OK")
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=materiel, name="Contrôle annuel", every_n_days=365)
        MaintenanceOccurrence.objects.create(
            plan=plan, asset=materiel, scheduled_for=timezone.now().date(), status="OVERDUE",
        )
        self.assertEqual(materiel.etat_plan, Asset.ETAT_ATTENTION)

    def test_materiel_avec_ticket_correctif_ouvert_est_orange(self):
        # Asset.status n'est jamais remis à jour automatiquement à l'ouverture
        # d'un ticket correctif : un matériel resté "OK" avec un ticket en
        # cours doit quand même déclencher l'alerte (sinon faux sentiment de
        # sécurité sur le plan).
        materiel = self._creer_asset(status="OK")
        CorrectiveTicket.objects.create(asset=materiel, description="Fuite constatée", status="REPORTED")
        self.assertEqual(materiel.etat_plan, Asset.ETAT_ATTENTION)

    def test_materiel_avec_ticket_correctif_en_reparation_est_orange(self):
        materiel = self._creer_asset(status="OK")
        CorrectiveTicket.objects.create(asset=materiel, description="Réparation en cours", status="IN_REPAIR")
        self.assertEqual(materiel.etat_plan, Asset.ETAT_ATTENTION)

    def test_materiel_avec_ticket_correctif_ferme_ou_annule_reste_ok(self):
        materiel = self._creer_asset(status="OK")
        CorrectiveTicket.objects.create(asset=materiel, description="Panne résolue", status="CLOSED")
        CorrectiveTicket.objects.create(asset=materiel, description="Signalement annulé", status="CANCELLED")
        self.assertEqual(materiel.etat_plan, Asset.ETAT_OK)

    def test_danger_l_emporte_sur_le_controle_en_retard(self):
        materiel = self._creer_asset(status="OUT_OF_SERVICE")
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=materiel, name="Contrôle", every_n_days=365)
        MaintenanceOccurrence.objects.create(
            plan=plan, asset=materiel, scheduled_for=timezone.now().date(), status="OVERDUE",
        )
        self.assertEqual(materiel.etat_plan, Asset.ETAT_DANGER)


class PlanNavireConsultationAccesTests(TestCase):
    """La page de consultation est ouverte à tous les rôles (contrairement à
    l'éditeur, réservé CHEF_SERVICE+), mais reste bornée au navire de
    l'utilisateur."""

    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A", code="NAV-A")
        self.ship_b = Ship.objects.create(name="Navire B", code="NAV-B")
        self.pont_a = Deck.objects.create(ship=self.ship_a, name="Pont A", order=1)
        self.pont_b = Deck.objects.create(ship=self.ship_b, name="Pont B", order=1)

        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship_a}
        )

    def test_equipier_peut_consulter_le_plan_de_son_navire(self):
        self.client.login(username="equipier", password="pass")
        r = self.client.get(f"/assets/plan-navire/{self.pont_a.id}/")
        self.assertEqual(r.status_code, 200)

    def test_equipier_ne_peut_pas_consulter_le_plan_dun_autre_navire(self):
        self.client.login(username="equipier", password="pass")
        r = self.client.get(f"/assets/plan-navire/{self.pont_b.id}/")
        self.assertEqual(r.status_code, 403)

    def test_point_dentree_redirige_vers_le_premier_pont_par_ordre(self):
        Deck.objects.create(ship=self.ship_a, name="Pont B", order=2)
        pont_zero = Deck.objects.create(ship=self.ship_a, name="Pont zéro", order=0)
        self.client.login(username="equipier", password="pass")
        r = self.client.get("/assets/plan-navire/")
        self.assertRedirects(r, f"/assets/plan-navire/{pont_zero.id}/")

    def test_navire_sans_pont_configure_affiche_un_message_clair(self):
        ship_c = Ship.objects.create(name="Navire C", code="NAV-C")
        equipier_c = User.objects.create_user(username="equipier_c", password="pass")
        UserProfile.objects.update_or_create(
            user=equipier_c, defaults={"role": "EQUIPIER", "ship": ship_c}
        )
        self.client.login(username="equipier_c", password="pass")
        r = self.client.get("/assets/plan-navire/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Aucun pont n'est encore configuré")


class PlanNavireConsultationRenduTests(TestCase):
    """Rendu de la page : navigation par onglets, épingle affichée, lien
    direct vers la fiche du matériel."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.asset_type = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)
        self.pont = Deck.objects.create(ship=self.ship, name="Pont A", order=1, image=_image_1x1_png())
        self.materiel = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            internal_id="EXT-AVANT", plan_deck=self.pont, position_x=25, position_y=40,
        )
        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "ship": self.ship}
        )
        self.client.login(username="equipier", password="pass")

    def test_page_affiche_les_onglets_et_le_materiel_positionne(self):
        Deck.objects.create(ship=self.ship, name="Pont B", order=2)
        r = self.client.get(f"/assets/plan-navire/{self.pont.id}/")
        self.assertContains(r, "Pont A")
        self.assertContains(r, "Pont B")
        self.assertContains(r, "EXT-AVANT")

    def test_clic_sur_une_epingle_pointe_directement_vers_la_fiche_materiel(self):
        r = self.client.get(f"/assets/plan-navire/{self.pont.id}/")
        self.assertContains(r, f"/assets/{self.materiel.id}/")

    def test_materiel_non_positionne_napparait_pas_sur_le_plan(self):
        Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            internal_id="EXT-NON-POSITIONNE",
        )
        r = self.client.get(f"/assets/plan-navire/{self.pont.id}/")
        self.assertNotContains(r, "EXT-NON-POSITIONNE")

    def test_position_non_entiere_rendue_avec_point_decimal_et_non_virgule(self):
        # Avec LANGUAGE_CODE="fr", Django localise les décimaux dans les
        # templates ("33.5" -> "33,5"), ce qui rend le style CSS inline
        # invalide (une virgule n'est pas un séparateur décimal CSS valide) et
        # empêche l'épingle de s'afficher à la bonne position. La quasi-
        # totalité des positions réelles sont non-entières (clic libre côté
        # JS), donc ce cas doit être couvert avec une valeur non-entière.
        Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
            internal_id="EXT-PRECIS", plan_deck=self.pont, position_x=33.5, position_y=66.25,
        )
        r = self.client.get(f"/assets/plan-navire/{self.pont.id}/")
        self.assertContains(r, "left:33.5%; top:66.25%;")
        self.assertNotContains(r, "left:33,5%")
        self.assertNotContains(r, "top:66,25%")
