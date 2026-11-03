"""Jeu de démonstration dense : isolé (refuse toute autre base), reproductible, idempotent, cohérent."""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from absences.models import Absence
from documentation.models import Document
from logistics.models import Anomalie, CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from matrix.core.management.commands.seed_demo_dense import doubles_affectations
from notifications.models import Notification
from postes.models import Poste
from programme.models import EvenementProgramme
from quarts.models import CreneauServiceGarde, EchangeService
from retex.models import Retex
from taches.models import Tache

User = get_user_model()


class RefusSurBaseQuelconqueTests(TestCase):
    def test_une_base_sans_donnees_de_demonstration_est_refusee(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo_dense", stdout=StringIO())
        self.assertEqual(Tache.objects.count(), 0)

    def test_des_mots_de_passe_non_fictifs_sont_refuses(self):
        call_command("seed_demo", stdout=StringIO())
        marin = User.objects.get(username="equipier_a")
        marin.set_password("un-vrai-mot-de-passe")
        marin.save()
        with self.assertRaises(CommandError):
            call_command("seed_demo_dense", stdout=StringIO())


class JeuDenseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.avant = {"taches": Tache.objects.count(), "anomalies": Anomalie.objects.count(), "tickets": CorrectiveTicket.objects.count()}
        sortie = StringIO()
        call_command("seed_demo_dense", stdout=sortie)
        cls.sortie = sortie.getvalue()

    def test_volumes_et_modules_alimentes(self):
        self.assertGreaterEqual(Tache.objects.count() - self.avant["taches"], 25)
        self.assertGreaterEqual(Anomalie.objects.count() - self.avant["anomalies"], 12)
        self.assertGreaterEqual(CorrectiveTicket.objects.count() - self.avant["tickets"], 8)
        self.assertGreaterEqual(MaintenanceOccurrence.objects.count(), 30)
        for modele, minimum in ((EvenementProgramme, 6), (Document, 6), (Retex, 5), (Poste, 5), (Absence, 6), (Notification, 30)):
            self.assertGreaterEqual(modele.objects.count(), minimum, modele.__name__)
        self.assertTrue(Tache.objects.filter(priorite="URGENTE").exists() and Tache.objects.filter(priorite="NORMALE").exists())
        self.assertEqual({t.statut for t in Tache.objects.all()} >= {"A_FAIRE", "EN_COURS", "BLOQUEE", "TERMINEE"}, True)

    def test_anomalies_liees_a_des_tickets_a_plusieurs_etats(self):
        liees = Anomalie.objects.exclude(ticket=None).select_related("ticket")
        self.assertGreaterEqual(liees.count(), 4)
        self.assertGreaterEqual(len({a.ticket.status for a in liees}), 3)
        for anomalie in liees:
            self.assertEqual(anomalie.ticket.asset or anomalie.ticket.installation, anomalie.asset or anomalie.installation)
            self.assertNotEqual(anomalie.statut, "SIGNALEE")

    def test_echanges_a_tous_les_etats_et_affectations_mises_a_jour(self):
        self.assertEqual(
            {e.statut for e in EchangeService.objects.all()},
            {EchangeService.STATUT_DEMANDE, EchangeService.STATUT_ACCEPTE, EchangeService.STATUT_VALIDE,
             EchangeService.STATUT_REFUSE, EchangeService.STATUT_REJETE, EchangeService.STATUT_ANNULE})
        valide = EchangeService.objects.get(statut=EchangeService.STATUT_VALIDE)
        self.assertEqual(valide.creneau_demandeur.marin, valide.cible)
        self.assertEqual(valide.creneau_cible.marin, valide.demandeur)
        for echange in EchangeService.objects.all():
            self.assertTrue(echange.evenements.exists())

    def test_aucune_double_affectation_mer_quai_pour_les_marins_ajoutes(self):
        ajoutes = {u.pk for u in User.objects.filter(username__startswith="m_")}
        self.assertEqual(len(ajoutes), 18)
        self.assertEqual(doubles_affectations(ajoutes), [])
        quai = CreneauServiceGarde.objects.filter(service_garde__nom__startswith="Service à quai — semaine")
        self.assertGreaterEqual(quai.count(), 15)

    def test_identites_fictives_sans_nom_de_role(self):
        for marin in User.objects.filter(username__startswith="m_"):
            self.assertFalse(any(m in (marin.get_full_name() + marin.username).lower() for m in ("coma", "chef", "cdt", "commandant", "equipier")))

    def test_idempotent(self):
        avant = Tache.objects.count()
        sortie = StringIO()
        call_command("seed_demo_dense", stdout=sortie)
        self.assertIn("déjà généré", sortie.getvalue())
        self.assertEqual(Tache.objects.count(), avant)

    def test_les_pages_chargees_restent_accessibles_a_plusieurs_profils(self):
        routes = ["home", "taches-index", "anomalie-list", "ticket-list", "maintenance-occurrences", "quarts-index", "echanges-index",
                  "programme-index", "documentation-index", "retex-index", "postes-index", "absences-index", "annonces-index",
                  "notifications-centre", "calendar-index"]
        for profil in ("equipier_a", "chef_secteur_a", "chef_service_a", "coma_comaeq", "cdt_a", "m_marchand"):
            self.client.force_login(User.objects.get(username=profil))
            for route in routes:
                self.assertEqual(self.client.get(reverse(route)).status_code, 200, f"{profil} {route}")
