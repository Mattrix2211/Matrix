"""Tournée de matériel : fiche en tableau par catégorie et compte rendu en série."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from assets.models import Asset, AssetType, ChecklistItemTemplate, ChecklistTemplate, Deck
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


class TourneeTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire T", code="NT-TOUR")
        service = Service.objects.create(ship=self.ship, name="Service T")
        self.sector = Sector.objects.create(service=service, name="Secteur T")
        type_ = AssetType.objects.create(name="Extincteur", category="Sécurité", sector=self.sector)
        modele = ChecklistTemplate.objects.create(name="Contrôle extincteur", sector=self.sector)
        self.etat = ChecklistItemTemplate.objects.create(template=modele, label="Plombage", order=1)
        self.pression = ChecklistItemTemplate.objects.create(
            template=modele, label="Pression", field_type="number", unit="bar", valeur_min=10, valeur_max=15, order=2)
        pont_haut = Deck.objects.create(ship=self.ship, name="Pont haut", order=1)
        pont_bas = Deck.objects.create(ship=self.ship, name="Pont bas", order=2)
        self.occs = []
        for nom, pont in (("Ext C", pont_bas), ("Ext A", pont_haut), ("Ext B", pont_haut)):
            asset = Asset.objects.create(asset_type=type_, ship=self.ship, service=service, sector=self.sector,
                                         designation=nom, plan_deck=pont)
            plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Plan", checklist_template=modele)
            self.occs.append(MaintenanceOccurrence.objects.create(
                plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="PLANNED"))
        self.c, self.a, self.b = self.occs
        user = User.objects.create_user(username="chef_t", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "CHEF_SERVICE", "sector": self.sector, "ship": self.ship})
        self.client.login(username="chef_t", password="pass")
        self.ids = ",".join(str(o.pk) for o in self.occs)
        self.url = f"{reverse('tournee-saisie')}?ids={self.ids}"

    def _poster(self, lignes):
        donnees = {}
        for occ, valeurs in lignes.items():
            for col, v in valeurs.items():
                donnees[f"{occ.pk}__{col}"] = v
        return self.client.post(self.url, donnees)

    def test_fiche_un_tableau_trie_pont_puis_emplacement(self):
        r = self.client.get(f"{reverse('tournee-imprimer')}?ids={self.ids}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Fiche de tournée — Sécurité", count=1)
        contenu = r.content.decode()
        self.assertLess(contenu.index("Ext A"), contenu.index("Ext B"))
        self.assertLess(contenu.index("Ext B"), contenu.index("Ext C"))
        self.assertContains(r, "Pression")
        self.assertContains(r, "data:image/png;base64,")

    def test_grille_meme_ordre(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        contenu = r.content.decode()
        self.assertLess(contenu.index("Ext A"), contenu.index("Ext C"))
        self.assertContains(r, 'data-max="15"')

    def test_validation_cree_un_compte_rendu_par_equipement(self):
        r = self._poster({
            self.a: {f"i{self.etat.pk}": "conforme", f"i{self.pression.pk}": "12,5"},
            self.b: {f"i{self.etat.pk}": "non_conforme", f"i{self.pression.pk}": "9"},
            self.c: {"non_vu": "Local fermé"},
        })
        self.assertEqual(r.status_code, 302)
        ex_a = MaintenanceExecution.objects.get(occurrence=self.a)
        self.assertEqual(ex_a.measurements["Pression"], 12.5)
        self.assertEqual(ex_a.conformity, "CONFORME")
        self.a.refresh_from_db(); self.b.refresh_from_db(); self.c.refresh_from_db()
        self.assertEqual((self.a.status, self.b.status, self.c.status), ("DONE", "WAITING_VALIDATION", "PLANNED"))
        self.assertFalse(MaintenanceExecution.objects.filter(occurrence=self.c).exists())
        self.assertTrue(AuditLog.objects.filter(action="tournee_non_vu", details__contains="Local fermé").exists())
        self.assertEqual(AuditLog.objects.filter(action="tournee_compte_rendu").count(), 2)

    def test_erreur_dans_une_cellule_n_enregistre_rien(self):
        r = self._poster({
            self.a: {f"i{self.etat.pk}": "conforme", f"i{self.pression.pk}": "12"},
            self.b: {f"i{self.etat.pk}": "conforme", f"i{self.pression.pk}": "abc"},
        })
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "valeur numérique illisible", status_code=400)
        self.assertFalse(MaintenanceExecution.objects.exists())

    def test_non_vu_avec_controles_refuse(self):
        r = self._poster({self.a: {f"i{self.etat.pk}": "conforme", "non_vu": "Absent"}})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(MaintenanceExecution.objects.exists())

    def test_ligne_hors_perimetre_refusee(self):
        autre_ship = Ship.objects.create(name="Autre", code="AU-TOUR")
        service = Service.objects.create(ship=autre_ship, name="S autre")
        secteur = Sector.objects.create(service=service, name="Sec autre")
        asset = Asset.objects.create(asset_type=self.a.asset.asset_type, ship=autre_ship, service=service, sector=secteur)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="P", checklist_template=self.a.plan.checklist_template)
        occ = MaintenanceOccurrence.objects.create(plan=plan, asset=asset, scheduled_for=timezone.localdate())
        r = self._poster({self.a: {f"i{self.etat.pk}": "conforme"}, occ: {f"i{self.etat.pk}": "conforme"}})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(MaintenanceExecution.objects.exists())

    def test_equipage_a_terre_refuse_l_ecriture(self):
        self.ship.double_equipage = True
        self.ship.equipage_a_bord = "A"
        self.ship.save()
        UserProfile.objects.filter(user__username="chef_t").update(equipage="B")
        self.assertEqual(self._poster({self.a: {f"i{self.etat.pk}": "conforme"}}).status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertFalse(MaintenanceExecution.objects.exists())
