"""Le calendrier JSON ne révèle ni occurrence ni ticket hors du périmètre de l'appelant
(autre bâtiment, ou autre secteur du même bâtiment), filtres compris."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation, InstallationMaintenance, ModeDeclenchement
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


class FuiteCalendrierTests(TestCase):
    def _site(self, code):
        navire = Ship.objects.create(name=f"Navire {code}", code=code)
        service = Service.objects.create(ship=navire, name=f"Service {code}")
        secteurs = [Sector.objects.create(service=service, name=f"Secteur {code}{i}") for i in (1, 2)]
        return navire, service, secteurs

    def _materiel(self, navire, service, secteur, nom):
        type_actif = AssetType.objects.create(name=nom, category="Incendie", sector=secteur)
        actif = Asset.objects.create(asset_type=type_actif, ship=navire, service=service, sector=secteur)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=actif, name=f"Plan {nom}", every_n_days=30)
        occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=actif, scheduled_for=timezone.localdate(), status="PLANNED",
        )
        ticket = CorrectiveTicket.objects.create(
            asset=actif, description=f"Panne {nom}", planned_for=timezone.localdate(),
        )
        return occ, ticket

    def _installation(self, navire, service, secteur, nom):
        installation = Installation.objects.create(designation=nom, ship=navire, service=service, sector=secteur)
        maintenance = InstallationMaintenance.objects.create(
            installation=installation, periodicity="1 mois", title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER, intervalle=1, unite_intervalle="M",
        )
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance, scheduled_for=timezone.localdate(), status="PLANNED",
        )
        ticket = CorrectiveTicket.objects.create(
            installation=installation, description=f"Panne {nom}", planned_for=timezone.localdate(),
        )
        return occ, ticket

    def setUp(self):
        self.nor, svc_nor, (self.nor1, self.nor2) = self._site("NOR")
        self.bre, svc_bre, (self.bre1, _) = self._site("BRE")
        self.occ_nor1, self.tic_nor1 = self._materiel(self.nor, svc_nor, self.nor1, "Pompe Nor 1")
        self.occ_nor2, self.tic_nor2 = self._materiel(self.nor, svc_nor, self.nor2, "Pompe Nor 2")
        self.occ_bre, self.tic_bre = self._materiel(self.bre, svc_bre, self.bre1, "Pompe Bretagne")
        self.occ_inst_bre, self.tic_inst_bre = self._installation(self.bre, svc_bre, self.bre1, "Groupe Bretagne")
        self.occ_inst_nor, self.tic_inst_nor = self._installation(self.nor, svc_nor, self.nor1, "Groupe Nor")
        self.equipier_nor = User.objects.create_user(username="equipier_nor", password="pass")
        UserProfile.objects.filter(user=self.equipier_nor).update(role="EQUIPIER", sector=self.nor1)
        self.url = reverse("calendar-events") + f"?date={timezone.localdate().isoformat()}&view=day"

    def _ids(self, **filtres):
        self.client.login(username="equipier_nor", password="pass")
        reponse = self.client.get(self.url, filtres)
        self.assertEqual(reponse.status_code, 200)
        return {e["id"] for e in reponse.json()}, reponse.content.decode()

    def test_autre_batiment_invisible(self):
        ids, brut = self._ids()
        for objet in (self.occ_bre, self.occ_inst_bre):
            self.assertNotIn(f"occ-{objet.pk}", ids)
        for objet in (self.tic_bre, self.tic_inst_bre):
            self.assertNotIn(f"tic-{objet.pk}", ids)
        self.assertNotIn("Bretagne", brut)

    def test_autre_secteur_du_meme_batiment_invisible(self):
        ids, brut = self._ids()
        self.assertNotIn(f"occ-{self.occ_nor2.pk}", ids)
        self.assertNotIn(f"tic-{self.tic_nor2.pk}", ids)
        self.assertNotIn("Nor 2", brut)

    def test_objets_du_perimetre_visibles(self):
        ids, _ = self._ids()
        self.assertEqual(
            ids,
            {f"occ-{self.occ_nor1.pk}", f"occ-{self.occ_inst_nor.pk}",
             f"tic-{self.tic_nor1.pk}", f"tic-{self.tic_inst_nor.pk}"},
        )

    def test_filtre_sur_autre_batiment_ne_revele_rien(self):
        for filtres in ({"ship": self.bre.pk}, {"status": "PLANNED"}, {"type": "ticket", "ship": self.bre.pk}):
            ids, brut = self._ids(**filtres)
            self.assertFalse({i for i in ids if i.startswith(("occ-", "tic-"))} & {
                f"occ-{self.occ_bre.pk}", f"tic-{self.tic_bre.pk}",
                f"occ-{self.occ_inst_bre.pk}", f"tic-{self.tic_inst_bre.pk}",
            })
            self.assertNotIn("Bretagne", brut)

    def test_page_html_ne_liste_pas_les_objets_hors_perimetre(self):
        self.client.login(username="equipier_nor", password="pass")
        reponse = self.client.get(reverse("calendar-index"), {"view": "day"})
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, f"/maintenance/occurrences/{self.occ_bre.pk}/")
        self.assertNotContains(reponse, f"/logistics/tickets/{self.tic_bre.pk}/")

    def test_assigne_garde_son_occurrence(self):
        self.occ_bre.assignees.add(self.equipier_nor)
        ids, _ = self._ids()
        self.assertIn(f"occ-{self.occ_bre.pk}", ids)

    def test_recherches_ne_revelent_pas_le_autre_batiment(self):
        self.client.login(username="equipier_nor", password="pass")
        for url in (reverse("global-search"), reverse("recherche-rapide")):
            for terme in ("Groupe", "Panne", "Pompe"):
                contenu = self.client.get(url, {"q": terme}).content.decode()
                self.assertNotIn("Bretagne", contenu, f"{url} {terme}")
        self.assertContains(self.client.get(reverse("recherche-rapide"), {"q": "Groupe"}), "Groupe Nor")
