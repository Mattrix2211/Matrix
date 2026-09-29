"""Double équipage, tranche 2 : synthèse de passation à la relève."""
from datetime import date, timedelta

from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from accounts.models import UserProfile
from assets.models import Installation
from logistics.models import Anomalie, CorrectiveTicket, StockPiece
from notifications.models import Notification, NotificationLevel
from org import passation
from org.models import Equipage, Sector, Section, Service, Ship, SynthesePassation
from org.tasks import appliquer_releves_planifiees
from org.tests.test_equipages import creer_marin


class PassationBase(TestCase):
    def setUp(self):
        cache.clear()
        self.navire = Ship.objects.create(name="FREMM P", code="FP", classe_navire="FREMM", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.navire, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.navire, nom="Rouge")
        self.navire.equipage_a_bord = self.bleu
        self.navire.save()
        self.service = Service.objects.create(ship=self.navire, name="Machine")
        self.secteur = Sector.objects.create(service=self.service, name="Propulsion")
        self.commandant = creer_marin("cdt", "COMMANDANT", self.navire, self.bleu)
        self.montant = creer_marin("montant", "EQUIPIER", self.navire, self.rouge)

    def _donnees_du_batiment(self):
        Anomalie.objects.create(titre="Fuite coursive", ship=self.navire, statut="SIGNALEE")
        Anomalie.objects.create(titre="Ancienne", ship=self.navire, statut="CLOTUREE")
        StockPiece.objects.create(
            reference="R1", designation="Joint", quantite=0, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        StockPiece.objects.create(
            reference="R2", designation="Filtre", quantite=9, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        installation = Installation.objects.create(
            designation="Pompe", ship=self.navire, service=self.service, sector=self.secteur,
        )
        CorrectiveTicket.objects.create(installation=installation, description="Fuite pompe", status="IN_REPAIR")
        CorrectiveTicket.objects.create(installation=installation, description="Réglé", status="CLOSED")


class ContenuTests(PassationBase):
    def test_contenu_du_batiment_seulement_elements_ouverts(self):
        self._donnees_du_batiment()
        autre = Ship.objects.create(name="Autre", code="AU")
        Anomalie.objects.create(titre="Ailleurs", ship=autre, statut="SIGNALEE")
        contenu = passation.construire_contenu(self.navire)
        self.assertEqual(contenu["anomalies"]["total"], 1)
        self.assertEqual(contenu["tickets"]["total"], 1)
        self.assertEqual(contenu["stock"]["total"], 1)
        self.assertEqual(contenu["stock"]["critiques"], 1)
        self.assertEqual(contenu["maintenances"]["total"], 0)


class ReleveImmediateTests(PassationBase):
    def _releve(self):
        creer_marin("admin", "ADMIN_NAVIRE", self.navire)
        self.client.login(username="admin", password="pass")
        return self.client.post(reverse("equipages"), {
            "action": "planifier_releve", "equipage_id": self.rouge.pk, "date": timezone.localdate().isoformat(),
        })

    def test_releve_immediate_produit_synthese_et_notifie_l_equipage_montant(self):
        self._donnees_du_batiment()
        self._releve()
        synthese = SynthesePassation.objects.get()
        self.assertEqual(synthese.equipage_montant, self.rouge)
        self.assertEqual(synthese.equipage_descendant, self.bleu)
        notif = Notification.objects.get(user=self.montant)
        self.assertEqual(notif.level, NotificationLevel.DANGER)
        self.assertEqual(notif.object_id, str(synthese.pk))
        self.assertFalse(Notification.objects.filter(user=self.commandant).exists())

    def test_synthese_figee_apres_evolution_du_batiment(self):
        self._donnees_du_batiment()
        self._releve()
        Anomalie.objects.all().delete()
        self.assertEqual(SynthesePassation.objects.get().contenu["anomalies"]["total"], 1)

    def test_pas_de_seconde_synthese_pour_la_meme_releve(self):
        synthese, creee = passation.generer_synthese(self.navire, self.rouge, self.bleu, timezone.localdate())
        _, encore = passation.generer_synthese(self.navire, self.rouge, self.bleu, timezone.localdate())
        self.assertTrue(creee)
        self.assertFalse(encore)
        self.assertEqual(SynthesePassation.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.montant).count(), 1)

    def test_echec_de_synthese_annule_la_bascule_immediate(self):
        with mock.patch.object(passation, "generer_synthese", side_effect=RuntimeError("panne simulée")):
            with self.assertRaises(RuntimeError):
                self._releve()
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, self.bleu)


class ReleveePlanifieeTests(PassationBase):
    def _planifier(self, jour):
        self.navire.equipage_releve, self.navire.date_releve = self.rouge, jour
        self.navire.save()

    def test_tache_bascule_la_releve_echue_une_seule_fois(self):
        self._planifier(timezone.localdate() - timedelta(days=1))
        self.assertEqual(appliquer_releves_planifiees()["releves"], 1)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, self.rouge)
        self.assertIsNone(self.navire.equipage_releve)
        self.assertEqual(SynthesePassation.objects.count(), 1)
        self.assertEqual(appliquer_releves_planifiees()["releves"], 0)
        self.assertEqual(SynthesePassation.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.montant).count(), 1)

    def test_echec_de_synthese_laisse_la_releve_intacte_et_traite_le_navire_suivant(self):
        second = Ship.objects.create(name="FREMM Q", code="FQ", classe_navire="FREMM", double_equipage=True)
        or_ = Equipage.objects.create(ship=second, nom="Or")
        argent = Equipage.objects.create(ship=second, nom="Argent")
        second.equipage_a_bord, second.equipage_releve = or_, argent
        second.date_releve = timezone.localdate() - timedelta(days=1)
        second.save()
        self._planifier(timezone.localdate() - timedelta(days=1))
        vraie = passation.generer_synthese

        def generer_avec_panne(ship, *args, **kwargs):
            if ship.pk == self.navire.pk:
                raise RuntimeError("panne simulée")
            return vraie(ship, *args, **kwargs)

        with mock.patch.object(passation, "generer_synthese", side_effect=generer_avec_panne):
            with self.assertLogs("org.passation", level="ERROR"):
                self.assertEqual(passation.appliquer_releves_echues(), 1)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, self.bleu)
        self.assertEqual(self.navire.equipage_releve, self.rouge)
        self.assertFalse(SynthesePassation.objects.filter(ship=self.navire).exists())
        second.refresh_from_db()
        self.assertEqual(second.equipage_a_bord, argent)
        self.assertTrue(SynthesePassation.objects.filter(ship=second).exists())

    def test_releve_a_venir_non_appliquee(self):
        self._planifier(timezone.localdate() + timedelta(days=3))
        self.assertEqual(appliquer_releves_planifiees()["releves"], 0)
        self.assertFalse(SynthesePassation.objects.exists())
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, self.bleu)


class ConsultationTests(PassationBase):
    def setUp(self):
        super().setUp()
        self.synthese, _ = passation.generer_synthese(self.navire, self.rouge, self.bleu, timezone.localdate())

    def test_membre_du_navire_consulte_liste_et_detail(self):
        self.client.login(username="montant", password="pass")
        self.assertContains(self.client.get(reverse("passations")), "FREMM P")
        self.assertEqual(self.client.get(reverse("passation_detail", args=[self.synthese.pk])).status_code, 200)

    def test_marin_d_un_autre_navire_ne_voit_rien(self):
        autre = Ship.objects.create(name="Autre", code="AU")
        creer_marin("etranger", "COMMANDANT", autre)
        self.client.login(username="etranger", password="pass")
        self.assertNotContains(self.client.get(reverse("passations")), "FREMM P")
        self.assertEqual(self.client.get(reverse("passation_detail", args=[self.synthese.pk])).status_code, 404)

    def test_page_equipages_affiche_les_passations(self):
        self.client.login(username="cdt", password="pass")
        self.assertContains(self.client.get(reverse("equipages")), "Passations de relève")
