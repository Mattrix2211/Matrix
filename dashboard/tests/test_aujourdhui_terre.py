"""« Aujourd'hui » à terre : choix de la vue, périmètre des bâtiments suivis, « À faire » et badges."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ResponsableSpecialite, SpecialityChoice
from assets.models import Asset, AssetType
from dashboard.aujourdhui_terre import a_faire_terre, batiments_suivis, cartes_batiments
from logistics.models import Anomalie, CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import ResponsableClasseNavire, Sector, Service, Ship


class AujourdhuiTerreTests(TestCase):
    def setUp(self):
        self.aujourdhui = timezone.localdate()
        self.ship_a = Ship.objects.create(name="Alpha", code="AL", classe_navire="FREMM")
        self.ship_b = Ship.objects.create(name="Bravo", code="BR", classe_navire="FREMM")
        self.ship_c = Ship.objects.create(name="Charlie", code="CH", classe_navire="Autre")
        self.ssf = User.objects.create_user(username="ssf", password="pass", last_name="Durand")
        ResponsableClasseNavire.objects.create(user=self.ssf, classe_navire="FREMM")
        self.assets = {}
        for ship in (self.ship_a, self.ship_b, self.ship_c):
            service = Service.objects.create(ship=ship, name="Énergie")
            secteur = Sector.objects.create(service=service, name="Propulsion")
            type_ = AssetType.objects.create(name=f"Pompe {ship.code}", category="Incendie", sector=secteur)
            self.assets[ship] = Asset.objects.create(asset_type=type_, ship=ship, service=service, sector=secteur)

    def _occurrence(self, ship, jours, statut):
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.assets[ship], name="Contrôle", every_n_days=30)
        return MaintenanceOccurrence.objects.create(
            plan=plan, asset=self.assets[ship], scheduled_for=self.aujourdhui + timedelta(days=jours), status=statut,
        )

    def test_perimetre_vide_ou_marin_a_bord_n_est_pas_a_terre(self):
        sans = User.objects.create_user(username="sans", password="pass")
        self.assertEqual(batiments_suivis(sans), [])
        self.ssf.profile.ship = self.ship_a
        self.ssf.profile.save()
        self.assertEqual(batiments_suivis(self.ssf), [])

    def test_batiments_de_la_classe_suivie(self):
        self.assertEqual(batiments_suivis(self.ssf), [self.ship_a, self.ship_b])

    def test_responsable_de_specialite_suit_toute_la_flotte(self):
        resp = User.objects.create_user(username="resp", password="pass")
        ResponsableSpecialite.objects.create(user=resp, specialite=SpecialityChoice.objects.create(name="Élec"))
        self.assertEqual(len(batiments_suivis(resp)), 3)

    def _avec_droit_de_gestion(self, *utilisateurs):
        for u in utilisateurs:
            u.profile.role = "CHEF_SECTION"
            u.profile.save()

    def test_a_faire_borne_aux_batiments_suivis(self):
        self._avec_droit_de_gestion(self.ssf)
        self._occurrence(self.ship_a, 1, "WAITING_VALIDATION")
        self._occurrence(self.ship_c, 1, "WAITING_VALIDATION")
        ticket = CorrectiveTicket.objects.create(asset=self.assets[self.ship_b], description="HS", status="BLOCKED")
        CorrectiveTicket.objects.create(asset=self.assets[self.ship_c], description="HS", status="BLOCKED")
        CorrectiveTicket.objects.create(asset=self.assets[self.ship_b], description="HS", status="REPORTED")
        urls = [e["url"] for e in a_faire_terre(batiments_suivis(self.ssf))]
        self.assertEqual(urls, [None, reverse("ticket-detail", args=[ticket.pk])])

    def test_liens_generes_suivis_a_terre(self):
        # Les liens « Valider » et « Commenter » doivent aboutir pour classe et spécialité.
        resp = User.objects.create_user(username="resp", password="pass")
        ResponsableSpecialite.objects.create(user=resp, specialite=SpecialityChoice.objects.create(name="Élec"))
        self._avec_droit_de_gestion(self.ssf, resp)
        attente = self._occurrence(self.ship_a, 1, "WAITING_VALIDATION")
        ticket = CorrectiveTicket.objects.create(asset=self.assets[self.ship_a], description="HS", status="BLOCKED")
        hors = self._occurrence(self.ship_c, 1, "WAITING_VALIDATION")
        hors_ticket = CorrectiveTicket.objects.create(asset=self.assets[self.ship_c], description="HS", status="BLOCKED")
        for nom in ("ssf", "resp"):
            self.client.login(username=nom, password="pass")
            self.assertEqual(self.client.get(reverse("ticket-detail", args=[ticket.pk])).status_code, 200)
            self.assertEqual(self.client.get(reverse("occurrence-execute", args=[attente.pk])).status_code, 200)
            self.assertEqual(
                self.client.post(reverse("ticket-comment-create", args=[ticket.pk]), {"body": "Suivi"}).status_code // 100, 3,
            )
        self.client.login(username="ssf", password="pass")
        self.assertEqual(self.client.get(reverse("ticket-detail", args=[hors_ticket.pk])).status_code, 400)
        self.assertEqual(self.client.get(reverse("occurrence-execute", args=[hors.pk])).status_code, 400)

    def test_sans_perimetre_ou_rattache_aucun_gain(self):
        ticket = CorrectiveTicket.objects.create(asset=self.assets[self.ship_b], description="HS", status="BLOCKED")
        User.objects.create_user(username="sans", password="pass")
        self.client.login(username="sans", password="pass")
        self.assertEqual(self.client.get(reverse("ticket-detail", args=[ticket.pk])).status_code, 400)
        # Rattaché au bâtiment Alpha : la responsabilité de classe n'élargit pas son périmètre.
        self.ssf.profile.ship = self.ship_a
        self.ssf.profile.save()
        self.client.login(username="ssf", password="pass")
        self.assertEqual(self.client.get(reverse("ticket-detail", args=[ticket.pk])).status_code, 400)

    def test_a_terre_aucun_bouton_valider_meme_avec_droit(self):
        self._avec_droit_de_gestion(self.ssf)
        attente = self._occurrence(self.ship_a, 1, "WAITING_VALIDATION")
        self.assertIsNone(a_faire_terre(batiments_suivis(self.ssf))[0]["url"])
        self.client.login(username="ssf", password="pass")
        self.assertNotContains(self.client.get(reverse("home")), "Valider")
        r = self.client.post(reverse("occurrence-execute", args=[attente.pk]), {"conformity": "CONFORME"})
        self.assertEqual(r.status_code, 403)
        attente.refresh_from_db()
        self.assertEqual(attente.status, "WAITING_VALIDATION")

    def test_badges_par_batiment(self):
        self._occurrence(self.ship_a, -2, "OVERDUE")
        self._occurrence(self.ship_a, 1, "WAITING_VALIDATION")
        Anomalie.objects.create(titre="Fuite", ship=self.ship_a)
        self.assets[self.ship_a].status = "OUT_OF_SERVICE"
        self.assets[self.ship_a].save()
        cartes = cartes_batiments(batiments_suivis(self.ssf), self.aujourdhui)
        self.assertEqual(
            [b["libelle"] for b in cartes[0]["badges"]],
            ["1 en retard", "1 anomalie(s) ouverte(s)", "1 indisponible(s)"],
        )
        self.assertEqual(cartes[1]["badges"], [{"etat": "ok", "libelle": "Rien à signaler"}])

    def test_page_a_terre_et_page_de_bord_inchangee(self):
        self.client.login(username="ssf", password="pass")
        r = self.client.get(reverse("home"))
        self.assertTemplateUsed(r, "dashboard/aujourdhui_terre.html")
        self.assertContains(r, "Alpha")
        self.assertNotContains(r, "Charlie")
        self.assertNotContains(r, "Ma journée")
        bord = User.objects.create_user(username="bord", password="pass")
        bord.profile.ship = self.ship_a
        bord.profile.save()
        self.client.login(username="bord", password="pass")
        self.assertTemplateUsed(self.client.get(reverse("home")), "dashboard/aujourdhui.html")
