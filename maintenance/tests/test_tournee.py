"""Tournée de matériel : fiche en tableau par catégorie et compte rendu en série."""
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from threads.models import Message
from notifications.models import Notification
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

    def _messages(self, r):
        return [str(m) for m in get_messages(r.wsgi_request)]

    def test_utilisateur_non_assigne_sous_le_seuil_refuse(self):
        simple = User.objects.create_user(username="equipier_t", password="pass")
        UserProfile.objects.update_or_create(user=simple, defaults={"role": "EQUIPIER", "sector": self.sector, "ship": self.ship})
        self.client.login(username="equipier_t", password="pass")
        r = self._poster({self.a: {f"i{self.etat.pk}": "conforme"}, self.b: {f"i{self.etat.pk}": "conforme"}})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(MaintenanceExecution.objects.exists())
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_identifiants_invalides_ou_enormes_donnent_404(self):
        for ids in ("abc", "-1", "9" * 40, ",,", ""):
            for nom in ("tournee-saisie", "tournee-imprimer"):
                self.assertEqual(self.client.get(f"{reverse(nom)}?ids={ids}").status_code, 404, (nom, ids))
        beaucoup = ",".join(str(n) for n in range(10000, 12000))
        self.assertEqual(self.client.get(f"{reverse('tournee-saisie')}?ids={beaucoup}").status_code, 404)

    def test_double_envoi_n_ecrit_qu_une_fois(self):
        lignes = {self.a: {f"i{self.etat.pk}": "conforme"}, self.b: {f"i{self.etat.pk}": "non_conforme"}}
        self._poster(lignes)
        avant = (AuditLog.objects.count(), Message.objects.count(), Notification.objects.count(),
                 MaintenanceExecution.objects.count())
        r = self._poster(lignes)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(any("déjà enregistrée" in m for m in self._messages(r)))
        self.assertEqual(avant, (AuditLog.objects.count(), Message.objects.count(), Notification.objects.count(),
                                 MaintenanceExecution.objects.count()))

    def test_double_envoi_non_vu_sans_doublon(self):
        self._poster({self.c: {"non_vu": "Local fermé"}})
        self._poster({self.c: {"non_vu": "Local fermé"}})
        self.assertEqual(AuditLog.objects.filter(action="tournee_non_vu").count(), 1)
        self.assertEqual(Message.objects.filter(body__contains="Local fermé").count(), 1)

    def test_occurrence_en_validation_en_lecture_seule(self):
        self._poster({self.b: {f"i{self.etat.pk}": "non_conforme"}})
        self.b.refresh_from_db()
        self.assertEqual(self.b.status, "WAITING_VALIDATION")
        r = self.client.get(self.url)
        self.assertContains(r, "Déjà enregistrées")
        self.assertContains(r, reverse("occurrence-execute", args=[self.b.pk]))
        self.assertNotContains(r, f'name="{self.b.pk}__')
        avant = AuditLog.objects.count()
        r = self._poster({self.b: {f"i{self.etat.pk}": "conforme", f"i{self.pression.pk}": "12"}})
        self.b.refresh_from_db()
        self.assertEqual(self.b.status, "WAITING_VALIDATION")
        self.assertEqual(MaintenanceExecution.objects.get(occurrence=self.b).conformity, "NON_CONFORME")
        self.assertEqual(AuditLog.objects.count(), avant)

    def test_execution_terminee_en_lecture_seule(self):
        MaintenanceExecution.objects.create(occurrence=self.a, completed_at=timezone.now(), conformity="CONFORME")
        r = self.client.get(self.url)
        self.assertNotContains(r, f'name="{self.a.pk}__')
        self._poster({self.a: {f"i{self.etat.pk}": "non_conforme"}})
        self.assertEqual(MaintenanceExecution.objects.get(occurrence=self.a).conformity, "CONFORME")

    def test_virgule_decimale_acceptee(self):
        self._poster({self.a: {f"i{self.etat.pk}": "conforme", f"i{self.pression.pk}": "12,75"}})
        self.assertEqual(MaintenanceExecution.objects.get(occurrence=self.a).measurements["Pression"], 12.75)

    def test_valeur_hors_plage_est_a_surveiller(self):
        self._poster({self.a: {f"i{self.etat.pk}": "conforme", f"i{self.pression.pk}": "99"}})
        self.assertEqual(MaintenanceExecution.objects.get(occurrence=self.a).conformity, "A_SURVEILLER")

    def test_html_dans_motif_et_observation_echappe(self):
        piege = "<script>alert(1)</script>"
        r = self._poster({self.a: {f"i{self.etat.pk}": "conforme", f"i{self.pression.pk}": "12", "observation": piege},
                          self.c: {f"i{self.etat.pk}": "conforme", "non_vu": piege}})
        self.assertEqual(r.status_code, 400)
        self.assertNotContains(r, piege, status_code=400)
        self.assertContains(r, "&lt;script&gt;", status_code=400)
        self._poster({self.c: {"non_vu": piege}})
        self.assertNotContains(self.client.get(reverse("occurrence-execute", args=[self.c.pk])), piege)

    def test_compte_rendu_individuel_refuse_equipage_a_terre(self):
        self.ship.double_equipage = True
        self.ship.equipage_a_bord = "A"
        self.ship.save()
        UserProfile.objects.filter(user__username="chef_t").update(equipage="B")
        r = self.client.post(reverse("occurrence-execute", args=[self.a.pk]), {"conformity": "CONFORME"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(MaintenanceExecution.objects.exists())
