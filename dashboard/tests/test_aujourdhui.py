"""Page « Aujourd'hui » : en-tête, « À faire » trié, brouillons, frise « Ma journée »."""
from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from matrix.core.models import Brouillon
from org.models import Sector, Service, Ship
from quarts.models import CreneauQuart, Quart
from training.models import TrainingCourse, TrainingSession


class AujourdhuiTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Frégate test", code="FT-AJ")
        self.service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=self.service, name="Propulsion")
        self.marin = User.objects.create_user(username="martin", password="pass", last_name="Martin")
        self.autre = User.objects.create_user(username="autre", password="pass")
        profil = self.marin.profile
        profil.grade, profil.ship, profil.service = "QM", self.navire, self.service
        profil.save()
        type_ = AssetType.objects.create(name="Pompe", category="Incendie", sector=self.secteur)
        self.asset = Asset.objects.create(asset_type=type_, ship=self.navire, service=self.service, sector=self.secteur)
        self.plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Contrôle", every_n_days=30)
        self.aujourdhui = timezone.localdate()
        self.url = reverse("home")
        self.client.login(username="martin", password="pass")

    def _occurrence(self, jours, statut="ASSIGNED", priorite=3, assigne=True):
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.aujourdhui + timedelta(days=jours),
            status=statut, priority=priorite,
        )
        if assigne:
            occ.assignees.add(self.marin)
        return occ

    def test_entete_personnel(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Bonjour QM Martin")
        self.assertContains(r, "Frégate test")
        self.assertContains(r, "Énergie")
        self.assertContains(r, "Aujourd&#x27;hui")

    def test_a_faire_trie_retard_puis_attente_puis_echeance(self):
        normale_tard = self._occurrence(5)
        normale_tot = self._occurrence(1)
        attente = self._occurrence(2, statut="WAITING_VALIDATION")
        retard = self._occurrence(-1, statut="OVERDUE")
        r = self.client.get(self.url)
        ordre = [e["objet"] for e in r.context["a_faire"]]
        self.assertEqual(ordre, [retard, attente, normale_tot, normale_tard])
        self.assertEqual([e["niveau"] for e in r.context["a_faire"]], ["danger", "attention", "", ""])

    def test_attente_de_validation_prime_sur_le_retard(self):
        attente = self._occurrence(-5, statut="WAITING_VALIDATION")
        r = self.client.get(self.url)
        entree = next(e for e in r.context["a_faire"] if e["objet"] == attente)
        self.assertEqual(entree["niveau"], "attention")
        self.assertEqual(entree["detail"], "En attente de validation")

    def test_a_faire_criticite_departage_a_echeance_egale(self):
        banale = self._occurrence(1, priorite=1)
        critique = self._occurrence(1, priorite=5)
        r = self.client.get(self.url)
        self.assertEqual([e["objet"] for e in r.context["a_faire"]], [critique, banale])

    def test_a_faire_exclut_ce_qui_ne_concerne_pas_le_marin_ou_termine(self):
        self._occurrence(1, assigne=False)
        self._occurrence(1, statut="DONE")
        autre = CorrectiveTicket.objects.create(asset=self.asset, description="x")
        autre.assignees.add(self.autre)
        r = self.client.get(self.url)
        self.assertEqual(r.context["a_faire"], [])
        self.assertContains(r, "Rien à faire pour le moment")

    def test_a_faire_contient_tickets_et_formation_du_jour(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite", severity=4)
        ticket.assignees.add(self.marin)
        cours = TrainingCourse.objects.create(title="Incendie")
        session = TrainingSession.objects.create(
            course=cours, scheduled_at=timezone.now().replace(hour=14, minute=0), status="PLANNED",
        )
        session.attendees.add(self.marin)
        r = self.client.get(self.url)
        objets = [e["objet"] for e in r.context["a_faire"]]
        self.assertIn(ticket, objets)
        self.assertContains(r, "Incendie")

    def test_brouillons_a_reprendre_personnels(self):
        Brouillon.objects.create(user=self.marin, cle="cr:1", libelle="Compte rendu pompe", url="/x/")
        Brouillon.objects.create(user=self.autre, cle="cr:2", libelle="Secret de l'autre", url="/y/")
        r = self.client.get(self.url)
        self.assertContains(r, "Compte rendu pompe")
        self.assertNotContains(r, "Secret de l'autre")

    def test_frise_quarts_publies_du_jour_uniquement(self):
        quart = Quart.objects.create(
            ship=self.navire, date_debut=self.aujourdhui, date_fin=self.aujourdhui, statut=Quart.STATUT_PUBLIEE,
        )
        brouillon = Quart.objects.create(
            ship=self.navire, date_debut=self.aujourdhui, date_fin=self.aujourdhui, statut=Quart.STATUT_BROUILLON,
        )
        debut = timezone.make_aware(datetime.combine(self.aujourdhui, time(8, 0)))
        CreneauQuart.objects.create(quart=quart, poste="Veille", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)
        CreneauQuart.objects.create(quart=brouillon, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)
        CreneauQuart.objects.create(quart=quart, poste="Machine", debut=debut, fin=debut + timedelta(hours=4), marin=self.autre)
        r = self.client.get(self.url)
        postes = [e["libelle"] for e in r.context["journee"]]
        self.assertEqual(len(postes), 1)
        self.assertIn("Veille", postes[0])

    def test_frise_vide_affiche_un_etat_vide(self):
        r = self.client.get(self.url)
        self.assertEqual(r.context["journee"], [])
        self.assertContains(r, "Rien de prévu aujourd'hui")

    def test_frise_trie_par_heure(self):
        cours = TrainingCourse.objects.create(title="Secourisme")
        tard = TrainingSession.objects.create(
            course=cours, scheduled_at=timezone.make_aware(datetime.combine(self.aujourdhui, time(14, 0))), status="PLANNED",
        )
        tot = TrainingSession.objects.create(
            course=cours, scheduled_at=timezone.make_aware(datetime.combine(self.aujourdhui, time(9, 0))), status="PLANNED",
        )
        tard.attendees.add(self.marin)
        tot.attendees.add(self.marin)
        r = self.client.get(self.url)
        heures = [e["heure"].hour for e in r.context["journee"]]
        self.assertEqual(heures, [9, 14])

    def test_ancienne_entree_de_navigation_renommee(self):
        r = self.client.get(self.url)
        self.assertNotContains(r, "Tableau de bord")
