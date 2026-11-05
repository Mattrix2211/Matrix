"""Démonstration métier approfondie : génération idempotente, cohérente, sans contournement des permissions."""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Q
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from logistics.models import Anomalie, AnomalieStatutLog, CorrectiveTicket, MouvementStock, PartLineItem, StockPiece
from maintenance.models import MaintenanceOccurrence
from notifications.models import Notification
from org.models import Ship
from programme.models import EvenementProgramme
from quarts.models import CreneauServiceGarde, EchangeService, ServiceGarde, peut_rediger_feuille_service

User = get_user_model()
GENERATEURS = ("seed_demo", "seed_demo_mer_quai", "seed_demo_dense", "seed_demo_metier")


class DemoMetierTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for commande in GENERATEURS:
            call_command(commande, stdout=StringIO())

    def _compteurs(self):
        return [m.objects.count() for m in (ServiceGarde, CreneauServiceGarde, EchangeService, EvenementProgramme, MaintenanceOccurrence, Anomalie,
                                            StockPiece, MouvementStock, PartLineItem, Notification, User)]

    def test_relance_sans_doublon(self):
        avant = self._compteurs()
        for commande in GENERATEURS:
            call_command(commande, stdout=StringIO())
        self.assertEqual(self._compteurs(), avant)

    def test_listes_de_services_a_tous_les_etats(self):
        etats = set(ServiceGarde.objects.values_list("statut", flat=True))
        self.assertTrue({"BROUILLON", "PROPOSEE", "PUBLIEE"} <= etats)
        self.assertTrue(ServiceGarde.objects.filter(application=ServiceGarde.APPLICATION_PREVISIONNELLE).exists())
        self.assertTrue({"DEMANDE", "ACCEPTE", "VALIDE", "REFUSE", "REJETE", "ANNULE"} <= set(EchangeService.objects.values_list("statut", flat=True)))

    def test_calendrier_sur_plusieurs_semaines_avec_annulation(self):
        evenements = EvenementProgramme.objects.order_by("debut")
        self.assertGreaterEqual((evenements.last().debut - evenements.first().debut).days, 35)
        self.assertTrue(EvenementProgramme.objects.filter(annule=True).exists())

    def test_maintenance_a_tous_les_etats_avec_fiches_detaillees(self):
        etats = set(MaintenanceOccurrence.objects.values_list("status", flat=True))
        self.assertTrue({"PLANNED", "ASSIGNED", "IN_PROGRESS", "WAITING_VALIDATION", "DONE", "OVERDUE", "CANCELLED"} <= etats)
        fiche = MaintenanceOccurrence.objects.filter(installation_maintenance__title="Contrôle et graissage du treuil").first().installation_maintenance
        version = fiche.version_validee
        self.assertTrue(version.etapes.exists() and version.preparations.exists())

    def test_anomalies_avec_historique_coherent(self):
        for anomalie in Anomalie.objects.filter(titre__startswith="Ventilateur de la cale arrière"):
            statuts = list(AnomalieStatutLog.objects.filter(anomalie=anomalie).order_by("pk").values_list("nouveau_statut", flat=True))
            self.assertEqual(statuts[0], "SIGNALEE")
            self.assertEqual(statuts[-1], anomalie.statut)

    def test_logistique_ruptures_seuils_et_commandes(self):
        self.assertTrue(StockPiece.objects.filter(quantite=0, quantite_minimale__gt=0).exists())
        self.assertTrue(PartLineItem.objects.filter(status="ORDERED").exists() and PartLineItem.objects.filter(status="TO_ORDER").exists())
        self.assertTrue(CorrectiveTicket.objects.filter(status="WAITING_PARTS", installation__reference="VENT-LM").exists())

    def test_aucune_double_affectation_de_services_a_quai_publies(self):
        publies = CreneauServiceGarde.objects.filter(service_garde__statut="PUBLIEE", marin__isnull=False)
        for creneau in publies:
            autre = publies.filter(marin=creneau.marin, debut__lt=creneau.fin, fin__gt=creneau.debut).exclude(pk=creneau.pk)
            self.assertFalse(autre.exists(), f"{creneau.marin} : {creneau} recouvre {autre.first()}")

    def test_journee_credible_d_equipier_a(self):
        a = User.objects.get(username="equipier_a")
        self.client.force_login(a)
        accueil = self.client.get("/")
        self.assertContains(accueil, "Mes tours de service")
        self.assertContains(self.client.get(reverse("quarts-index")), "Mon prochain tour")
        non_lues = Notification.objects.filter(user=a, is_read=False).count()
        self.assertTrue(0 < non_lues <= 20 and Notification.objects.filter(user=a, is_read=True).exists())
        self.assertTrue(Notification.objects.filter(user=a, level="danger").exists())

    def test_un_matelot_non_habilite_ne_redige_ni_ne_cree_de_feuille_de_service(self):
        ship = Ship.objects.get(name="Bretagne")
        a, bsc = User.objects.get(username="equipier_a"), User.objects.get(username="equipier_a2")
        self.assertFalse(peut_rediger_feuille_service(a, ship))
        self.assertTrue(peut_rediger_feuille_service(bsc, ship))
        self.client.force_login(a)
        jour = timezone.localdate().isoformat()
        reponse = self.client.post(reverse("feuille-service-detail", args=[ship.pk, jour]), {"action": "creer"})
        self.assertIn(reponse.status_code, (403, 404))

    def test_donnees_explicitement_fictives(self):
        self.assertFalse(User.objects.filter(email__regex=r"@(gmail|orange|defense)").exists())
        self.assertTrue(User.objects.filter(is_superuser=False).exclude(username="admin").exists())
