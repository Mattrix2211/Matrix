"""Compte rendu correctif (UX-3.10) : avec ou sans fiche, panne imprévue, pièces consommées, correction par un chef."""
import uuid

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, Roles, UserProfile
from assets.models import Asset, AssetType, ChecklistItemTemplate, ChecklistTemplate, Installation, InstallationMaintenance
from logistics.models import CorrectiveTicket, StockPiece
from maintenance import historique
from maintenance.models import CompteRenduCorrectif
from notifications.models import Notification
from org.models import Sector, Service, Ship
from threads.models import Message


def _marin(nom, ship, role=Roles.EQUIPIER, sector=None, service=None):
    user = User.objects.create_user(username=nom)
    UserProfile.objects.update_or_create(user=user, defaults={"ship": ship, "role": role, "sector": sector, "service": service})
    return user


class CorrectifTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire correctif", code="NC-1")
        self.service = Service.objects.create(ship=self.ship, name="Service correctif")
        self.sector = Sector.objects.create(service=self.service, name="Secteur correctif")
        self.marin = _marin("marin_c", self.ship)
        self.chef_section = _marin("section_c", self.ship, Roles.CHEF_SECTION, self.sector, self.service)
        self.chef = _marin("secteur_c", self.ship, Roles.CHEF_SECTEUR, self.sector, self.service)
        self.installation = Installation.objects.create(
            designation="Pompe correctif", ship=self.ship, service=self.service, sector=self.sector)
        self.piece = StockPiece.objects.create(
            reference="JNT-1", designation="Joint", quantite=10, ship=self.ship, service=self.service, sector=self.sector)
        self.url = reverse("correctif-nouveau")

    def donnees(self, **extra):
        return {"installation": str(self.installation.pk), "jeton": str(uuid.uuid4()), "constat": "Fuite à la pompe",
                "diagnostic": "Joint usé", "action": "Joint remplacé", "conformity": "CONFORME", **extra}

    def enregistrer(self, user=None, **extra):
        self.client.force_login(user or self.marin)
        return self.client.post(self.url, self.donnees(**extra))

    def test_panne_imprevue_sans_fiche_ouvre_le_ticket_et_notifie(self):
        r = self.enregistrer(debut="2026-03-01T08:00", fin="2026-03-01T09:30", estime="60")
        ticket = CorrectiveTicket.objects.get()
        self.assertRedirects(r, reverse("ticket-detail", args=[ticket.pk]))
        self.assertEqual((ticket.installation, ticket.description), (self.installation, "Fuite à la pompe"))
        self.assertEqual((ticket.diagnostic_final, ticket.solution), ("Joint usé", "Joint remplacé"))
        cr = CompteRenduCorrectif.objects.get()
        self.assertEqual((cr.ticket, cr.executed_by, cr.duree_estimee_min), (ticket, self.marin, 60))
        self.assertEqual(cr.saisie_origine["par"], self.marin.pk)
        self.assertIn(self.marin, ticket.assignees.all())
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__startswith="Compte rendu saisi").exists())
        entree = historique.frise(historique.sources_de(self.installation), self.chef)[0]
        self.assertEqual((entree["correctif"], entree["duree"], entree["estime"], entree["depassement"]), (True, "1 h 30", "1 h", True))
        self.client.force_login(self.marin)
        page = self.client.get(reverse("historique-installation", args=[self.installation.pk]))
        self.assertContains(page, "Joint remplacé")
        self.assertContains(page, "au-delà de l'estimé")

    def test_double_envoi_ne_cree_qu_un_ticket(self):
        donnees = self.donnees()
        self.client.force_login(self.marin)
        self.client.post(self.url, donnees)
        r = self.client.post(self.url, donnees)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(CorrectiveTicket.objects.count(), 1)
        self.assertEqual(CompteRenduCorrectif.objects.count(), 1)

    def test_entrees_invalides_sans_erreur_serveur(self):
        self.client.force_login(self.marin)
        cas = [
            ({"constat": ""}, "constat est à renseigner"),
            ({"conformity": ""}, "conformité finale est à déclarer"),
            ({"debut": "2026-03-02T10:00", "fin": "2026-03-01T10:00"}, "précède son début"),
            ({"debut": "0001-01-01T00:00"}, "illisible"),
            ({"estime": "abc"}, "nombre entier de minutes"),
            ({"constat": "x" * 5001}, "limité à 5000"),
            ({"estime": "99999999999999999999999"}, "nombre entier de minutes"),
        ]
        for extra, message in cas:
            r = self.client.post(self.url, self.donnees(**extra))
            self.assertContains(r, message, status_code=400)
        self.assertFalse(CorrectiveTicket.objects.exists())
        self.client.post(self.url, self.donnees(constat="Fuite\x00 pompe", gravite="99"))
        ticket = CorrectiveTicket.objects.get()
        self.assertEqual((ticket.description, ticket.severity), ("Fuite pompe", 3))

    def test_perimetre_et_identifiants_forges(self):
        etranger = _marin("etranger_c", Ship.objects.create(name="Autre", code="AU-1"))
        self.client.force_login(etranger)
        self.assertEqual(self.client.post(self.url, self.donnees()).status_code, 404)
        self.client.force_login(self.marin)
        for parametres in ("", "?installation=abc", f"?asset={uuid.uuid4()}", "?asset=%00"):
            self.assertEqual(self.client.get(self.url + parametres).status_code, 404, parametres)
        self.assertEqual(self.client.get(self.url + f"?installation={self.installation.pk}").status_code, 200)
        ticket = CorrectiveTicket.objects.create(installation=self.installation, description="Panne")
        self.client.force_login(etranger)
        self.assertEqual(self.client.get(reverse("correctif-compte-rendu", args=[ticket.pk])).status_code, 404)

    def test_equipier_non_assigne_n_ecrit_pas_sur_un_ticket_existant(self):
        ticket = CorrectiveTicket.objects.create(installation=self.installation, description="Panne")
        self.client.force_login(self.marin)
        url = reverse("correctif-compte-rendu", args=[ticket.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self.donnees()).status_code, 403)
        ticket.assignees.add(self.marin)
        self.assertContains(self.client.get(url), "Panne et réparation")

    def test_ticket_existant_prerempli_et_rex_synchronise(self):
        ticket = CorrectiveTicket.objects.create(
            installation=self.installation, description="Panne", diagnostic_final="Hypothèse", solution="")
        ticket.assignees.add(self.marin)
        self.client.force_login(self.marin)
        url = reverse("correctif-compte-rendu", args=[ticket.pk])
        self.assertContains(self.client.get(url), "Hypothèse")
        self.client.post(url, self.donnees(diagnostic="Roulement HS", action="Roulement changé"))
        ticket.refresh_from_db()
        self.assertEqual((ticket.diagnostic_final, ticket.solution), ("Roulement HS", "Roulement changé"))
        self.assertTrue(AuditLog.objects.filter(action="ticket_rex_via_compte_rendu").exists())
        self.assertEqual(CorrectiveTicket.objects.count(), 1)

    def test_pieces_consommees_par_un_chef_de_section(self):
        r = self.enregistrer(self.chef_section, piece_id=[str(self.piece.pk), ""], piece_qte=["3", ""])
        self.assertEqual(r.status_code, 302)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite, 7)
        cr = CompteRenduCorrectif.objects.get()
        self.assertEqual((cr.pieces[0]["reference"], cr.pieces[0]["quantite"]), ("JNT-1", 3))
        self.assertTrue(Message.objects.filter(is_system=True, body__contains="Prélèvement stock : 3 x JNT-1").exists())

    def test_pieces_stock_insuffisant_ou_illisible_ne_cree_rien(self):
        for extra, message in (
            ({"piece_id": [str(self.piece.pk)], "piece_qte": ["50"]}, "Stock insuffisant"),
            ({"piece_id": [str(self.piece.pk)], "piece_qte": ["x"]}, "illisible"),
            ({"piece_id": ["99999999999999999999"], "piece_qte": ["1"]}, "illisible"),
            ({"piece_id": ["424242"], "piece_qte": ["1"]}, "introuvable"),
        ):
            r = self.enregistrer(self.chef_section, **extra)
            self.assertContains(r, message, status_code=400)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite, 10)
        self.assertFalse(CorrectiveTicket.objects.exists())

    def test_pieces_hors_perimetre_et_droits(self):
        navire = Ship.objects.create(name="Autre navire", code="AN-2")
        service = Service.objects.create(ship=navire, name="S")
        autre = StockPiece.objects.create(
            reference="X", designation="Y", quantite=5, ship=navire, service=service, sector=Sector.objects.create(service=service, name="Z"))
        r = self.enregistrer(self.chef_section, piece_id=[str(autre.pk)], piece_qte=["1"])
        self.assertContains(r, "introuvable ou hors de votre périmètre", status_code=400)
        r = self.enregistrer(self.marin, piece_id=[str(self.piece.pk)], piece_qte=["1"])
        self.assertEqual(r.status_code, 403)
        autre.refresh_from_db()
        self.assertEqual(autre.quantite, 5)

    def test_avec_fiche_lignes_saisies_par_cle(self):
        fiche = InstallationMaintenance.objects.create(installation=self.installation, periodicity="1 an", title="Dépannage")
        version = ChecklistTemplate.objects.create(fiche=fiche, numero=1, name="Dépannage", sector=self.sector,
                                                   valide_le=timezone.now(), duree_estimee_min=45)
        controle = ChecklistItemTemplate.objects.create(template=version, label="Serrage", order=1)
        pression = ChecklistItemTemplate.objects.create(
            template=version, label="Pression", field_type="number", unit="bar", valeur_min=3, valeur_max=5, order=2)
        self.client.force_login(self.marin)
        page = self.client.get(self.url + f"?installation={self.installation.pk}&fiche={version.pk}")
        self.assertContains(page, "Serrage")
        self.assertContains(page, 'value="45"')
        r = self.client.post(self.url, self.donnees(fiche=str(version.pk), **{f"item_{controle.pk}": "conforme", f"item_{pression.pk}": "7"}))
        self.assertEqual(r.status_code, 302)
        cr = CompteRenduCorrectif.objects.get()
        self.assertEqual(cr.version_fiche, version)
        self.assertEqual(cr.measurements, {str(pression.cle): 7.0})
        entree = historique.frise(historique.sources_de(self.installation), self.chef)[0]
        self.assertTrue(entree["a_surveiller"])
        self.assertEqual(historique.series(historique.sources_de(self.installation))[0]["points"][0]["valeur"], 7.0)
        # Une fiche d'un autre équipement est refusée.
        autre = Installation.objects.create(designation="Autre", ship=self.ship, service=self.service, sector=self.sector)
        fiche_autre = InstallationMaintenance.objects.create(installation=autre, periodicity="1 an", title="Autre")
        version_autre = ChecklistTemplate.objects.create(fiche=fiche_autre, numero=1, name="Autre", sector=self.sector, valide_le=timezone.now())
        r = self.client.post(self.url, self.donnees(fiche=str(version_autre.pk)))
        self.assertEqual(r.status_code, 404)

    def test_correction_par_le_chef_de_secteur(self):
        self.enregistrer()
        cr = CompteRenduCorrectif.objects.get()
        url = reverse("correctif-compte-rendu", args=[cr.ticket_id])
        # Le marin qui renvoie son formulaire n'écrase rien.
        self.client.force_login(self.marin)
        r = self.client.post(url, self.donnees(diagnostic="Autre diagnostic", motif="Je change"))
        self.assertEqual(r.status_code, 302)
        cr.refresh_from_db()
        self.assertEqual(cr.diagnostic, "Joint usé")
        self.client.force_login(self.chef)
        r = self.client.post(url, self.donnees(diagnostic="Joint et bague usés"))
        self.assertContains(r, "motif de la modification est obligatoire", status_code=400)
        self.client.post(url, self.donnees(diagnostic="Joint et bague usés", motif="Complément d'expertise"))
        cr.refresh_from_db()
        self.assertEqual((cr.diagnostic, cr.executed_by), ("Joint et bague usés", self.marin))
        self.assertEqual(cr.saisie_origine["textes"]["Diagnostic"], "Joint usé")
        trace = cr.modifications.get()
        self.assertEqual((trace.auteur, trace.motif), (self.chef, "Complément d'expertise"))
        self.assertEqual(trace.modifications["Diagnostic"], {"avant": "Joint usé", "apres": "Joint et bague usés"})
        self.assertTrue(AuditLog.objects.filter(action="correctif_compte_rendu_modifie").exists())
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__startswith="Compte rendu modifié").exists())
        page = self.client.get(reverse("historique-installation", args=[self.installation.pk]))
        self.assertContains(page, "Complément d&#x27;expertise")
        self.assertContains(page, "Saisie d'origine")

    def test_materiel_et_menus(self):
        type_ = AssetType.objects.create(name="Treuil", category="Pont", sector=self.sector)
        asset = Asset.objects.create(asset_type=type_, ship=self.ship, service=self.service, sector=self.sector)
        self.client.force_login(self.marin)
        r = self.client.post(self.url, {"asset": str(asset.pk), "jeton": str(uuid.uuid4()), "constat": "Câble effiloché", "conformity": "A_SURVEILLER"})
        self.assertEqual(r.status_code, 302)
        ticket = CorrectiveTicket.objects.get()
        self.assertEqual(ticket.asset, asset)
        self.assertContains(self.client.get(reverse("ticket-detail", args=[ticket.pk])), "Compte rendu d&#x27;intervention")
        self.assertContains(self.client.get(reverse("asset-detail", args=[asset.pk])), "intervention corrective")
        self.assertContains(self.client.get(reverse("installation-detail", args=[self.installation.pk])), "Historique et relevés")
