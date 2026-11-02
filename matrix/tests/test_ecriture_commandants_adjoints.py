"""Écriture des commandants adjoints : bornée aux services rattachés à leur fonction, lecture inchangée.

Bretagne (double équipage, équipage A à bord) : Navigation et Propulsion relèvent du COMANAV, Opérations du COMOPS,
Vie à bord du COMAEQ. Les mêmes actions sont tentées sur chaque service par chaque profil : refus hors périmètre,
succès dans le périmètre.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation
from logistics.models import Anomalie, CorrectiveTicket, StockPiece
from matrix.core.ecriture_service import niveau_ecriture_sur, peut_ecrire_sur_service, services_rattaches
from matrix.core.roles import RoleLevel
from org.models import Sector, Service, Ship


class BaseDroitsEcriture(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bretagne droits", code="BD", double_equipage=True, equipage_a_bord="A")
        self.services = {}
        self.secteurs = {}
        self.assets = {}
        self.tickets = {}
        self.pieces = {}
        self.anomalies = {}
        for nom, coma in (("Navigation", "COMANAV"), ("Operations", "COMOPS"), ("Vie a bord", "COMAEQ")):
            service = Service.objects.create(ship=self.navire, name=nom, commandant_adjoint=coma)
            secteur = Sector.objects.create(service=service, name=f"Secteur {nom}")
            type_asset = AssetType.objects.create(name=f"Type {nom}", category="MCO", sector=secteur)
            asset = Asset.objects.create(
                asset_type=type_asset, internal_id=f"A-{nom}", designation=f"Matériel {nom}", ship=self.navire,
                service=service, sector=secteur,
            )
            self.services[nom], self.secteurs[nom], self.assets[nom] = service, secteur, asset
            self.tickets[nom] = CorrectiveTicket.objects.create(asset=asset, description=f"Panne {nom}")
            self.pieces[nom] = StockPiece.objects.create(
                reference=f"REF-{nom}", designation=f"Pièce {nom}", ship=self.navire, service=service, sector=secteur,
                quantite=5, quantite_minimale=1,
            )
            self.anomalies[nom] = Anomalie.objects.create(
                titre=f"Anomalie {nom}", ship=self.navire, service=service, sector=secteur,
            )
        self.profils = {
            "comanav_a": self._marin("comanav_a", "ETAT_MAJOR", "A", fonction_coma="COMANAV"),
            "comops_a": self._marin("comops_a", "ETAT_MAJOR", "A", fonction_coma="COMOPS"),
            "comaeq_a": self._marin("comaeq_a", "ETAT_MAJOR", "A", fonction_coma="COMAEQ"),
            "comaeq_b": self._marin("comaeq_b", "ETAT_MAJOR", "B", fonction_coma="COMAEQ"),
            "etat_major_sans_fonction": self._marin("em_sans_fonction", "ETAT_MAJOR", "A"),
            "chef_service_nav": self._marin("chef_service_nav", "CHEF_SERVICE", "A", service=self.services["Navigation"]),
            "chef_secteur_nav": self._marin("chef_secteur_nav", "CHEF_SECTEUR", "A", service=self.services["Navigation"], sector=self.secteurs["Navigation"]),
            "commandant": self._marin("commandant", "COMMANDANT", "A"),
        }

    def _marin(self, nom, role, equipage, **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.navire, "equipage": equipage, **champs})
        return User.objects.get(pk=user.pk)

    def _post(self, qui, url, donnees=None):
        self.client.force_login(self.profils[qui])
        return self.client.post(url, donnees or {})


class RattachementTests(BaseDroitsEcriture):
    def test_services_rattaches_a_la_fonction(self):
        self.assertEqual(services_rattaches(self.profils["comanav_a"]), {self.services["Navigation"].pk})
        self.assertEqual(services_rattaches(self.profils["comops_a"]), {self.services["Operations"].pk})
        self.assertEqual(services_rattaches(self.profils["comaeq_a"]), {self.services["Vie a bord"].pk})
        self.assertEqual(services_rattaches(self.profils["etat_major_sans_fonction"]), set())

    def test_niveau_ramene_a_equipier_hors_des_services_rattaches(self):
        comaeq = self.profils["comaeq_a"]
        self.assertGreaterEqual(niveau_ecriture_sur(comaeq, self.tickets["Vie a bord"]), RoleLevel.CHEF_SERVICE)
        self.assertEqual(niveau_ecriture_sur(comaeq, self.tickets["Navigation"]), RoleLevel.EQUIPIER)
        self.assertEqual(niveau_ecriture_sur(comaeq, self.tickets["Operations"]), RoleLevel.EQUIPIER)
        self.assertFalse(peut_ecrire_sur_service(self.profils["etat_major_sans_fonction"], self.services["Navigation"].pk))

    def test_les_autres_roles_ne_sont_pas_concernes(self):
        for qui in ("chef_service_nav", "chef_secteur_nav", "commandant"):
            self.assertTrue(peut_ecrire_sur_service(self.profils[qui], self.services["Operations"].pk), qui)


class TicketsTests(BaseDroitsEcriture):
    def _transition(self, qui, service):
        ticket = self.tickets[service]
        reponse = self._post(qui, reverse("ticket-transition", args=[ticket.pk]), {"status": "DIAGNOSED"})
        ticket.refresh_from_db()
        return reponse, ticket.status

    def test_chaque_commandant_adjoint_agit_sur_ses_services_seulement(self):
        for qui, propre, autres in (
            ("comanav_a", "Navigation", ("Operations", "Vie a bord")),
            ("comops_a", "Operations", ("Navigation", "Vie a bord")),
            ("comaeq_a", "Vie a bord", ("Navigation", "Operations")),
        ):
            CorrectiveTicket.objects.update(status="REPORTED")
            reponse, statut = self._transition(qui, propre)
            self.assertIn(reponse.status_code, (200, 302), f"{qui} sur {propre}")
            self.assertEqual(statut, "DIAGNOSED", f"{qui} sur {propre}")
            for autre in autres:
                reponse, statut = self._transition(qui, autre)
                self.assertEqual(reponse.status_code, 403, f"{qui} sur {autre}")
                self.assertEqual(statut, "REPORTED", f"{qui} sur {autre}")

    def test_la_lecture_reste_ouverte_a_toute_la_coordination(self):
        self.client.force_login(self.profils["comaeq_a"])
        for service in self.tickets:
            self.assertEqual(self.client.get(reverse("ticket-detail", args=[self.tickets[service].pk])).status_code, 200, service)

    def test_etat_major_sans_fonction_ne_modifie_rien(self):
        for service in self.tickets:
            reponse, statut = self._transition("etat_major_sans_fonction", service)
            self.assertEqual((reponse.status_code, statut), (403, "REPORTED"), service)

    def test_chef_de_service_son_service_seulement(self):
        reponse, statut = self._transition("chef_service_nav", "Navigation")
        self.assertEqual((reponse.status_code in (200, 302), statut), (True, "DIAGNOSED"))
        for autre in ("Operations", "Vie a bord"):
            reponse, statut = self._transition("chef_service_nav", autre)
            self.assertEqual(statut, "REPORTED", autre)
            self.assertIn(reponse.status_code, (400, 403, 404), autre)

    def test_chef_de_secteur_son_secteur_seulement(self):
        reponse, statut = self._transition("chef_secteur_nav", "Navigation")
        self.assertEqual(statut, "DIAGNOSED")
        for autre in ("Operations", "Vie a bord"):
            _, statut = self._transition("chef_secteur_nav", autre)
            self.assertEqual(statut, "REPORTED", autre)

    def test_equipage_b_a_terre_ne_modifie_rien_meme_dans_ses_services(self):
        for service in self.tickets:
            reponse, statut = self._transition("comaeq_b", service)
            self.assertEqual(statut, "REPORTED", service)
            self.assertIn(reponse.status_code, (302, 400, 403, 404), service)

    def test_le_commandant_garde_toute_la_flotte_du_batiment(self):
        for service in self.tickets:
            reponse, statut = self._transition("commandant", service)
            self.assertEqual(statut, "DIAGNOSED", service)


class StockEtAnomaliesTests(BaseDroitsEcriture):
    def test_creation_de_piece_dans_un_secteur_rattache_seulement(self):
        for qui, propre, autre in (("comanav_a", "Navigation", "Operations"), ("comaeq_a", "Vie a bord", "Navigation")):
            donnees = {"action": "create_piece", "reference": f"NEW-{qui}", "designation": "Nouvelle", "quantite": "2",
                       "quantite_minimale": "1", "sector_id": self.secteurs[propre].pk}
            self.assertEqual(self._post(qui, reverse("stock-piece-list"), donnees).status_code, 302, f"{qui} dans {propre}")
            self.assertTrue(StockPiece.objects.filter(reference=f"NEW-{qui}").exists(), qui)
            refus = {**donnees, "reference": f"REFUS-{qui}", "sector_id": self.secteurs[autre].pk}
            self.assertEqual(self._post(qui, reverse("stock-piece-list"), refus).status_code, 403, f"{qui} dans {autre}")
            self.assertFalse(StockPiece.objects.filter(reference=f"REFUS-{qui}").exists(), qui)

    def test_transition_d_anomalie_par_service(self):
        for qui, propre, autre in (("comanav_a", "Navigation", "Operations"), ("comops_a", "Operations", "Vie a bord")):
            ok = self._post(qui, reverse("anomalie-transition", args=[self.anomalies[propre].pk]), {"statut": "PRISE_EN_COMPTE"})
            self.assertIn(ok.status_code, (200, 302), f"{qui} sur {propre}")
            self.anomalies[propre].refresh_from_db()
            self.assertEqual(self.anomalies[propre].statut, "PRISE_EN_COMPTE")
            refus = self._post(qui, reverse("anomalie-transition", args=[self.anomalies[autre].pk]), {"statut": "PRISE_EN_COMPTE"})
            self.assertEqual(refus.status_code, 403, f"{qui} sur {autre}")
            self.anomalies[autre].refresh_from_db()
            self.assertEqual(self.anomalies[autre].statut, "SIGNALEE")


class MaterielEtApiTests(BaseDroitsEcriture):
    def _api_modifier(self, qui, service):
        client = APIClient()
        client.force_login(self.profils[qui])
        return client.patch(f"/api/assets/assets/{self.assets[service].pk}/", {"designation": f"Modifié par {qui}"}, format="json")

    def test_api_modification_de_materiel_par_service(self):
        for qui, propre, autre in (("comanav_a", "Navigation", "Operations"), ("comaeq_a", "Vie a bord", "Navigation"),
                                   ("comops_a", "Operations", "Vie a bord")):
            self.assertEqual(self._api_modifier(qui, propre).status_code, 200, f"{qui} sur {propre}")
            self.assertEqual(self._api_modifier(qui, autre).status_code, 403, f"{qui} sur {autre}")
            self.assertNotEqual(Asset.objects.get(pk=self.assets[autre].pk).designation, f"Modifié par {qui}")

    def test_api_chefs_et_commandant(self):
        self.assertEqual(self._api_modifier("chef_service_nav", "Navigation").status_code, 200)
        self.assertIn(self._api_modifier("chef_service_nav", "Operations").status_code, (403, 404))
        self.assertEqual(self._api_modifier("commandant", "Operations").status_code, 200)

    def test_api_equipage_b_a_terre_lecture_seule(self):
        self.assertIn(self._api_modifier("comaeq_b", "Vie a bord").status_code, (403, 404))

    def test_suppression_de_materiel_via_formulaire_par_service(self):
        for qui, propre, autre in (("comanav_a", "Navigation", "Operations"),):
            self.assertEqual(self._post(qui, reverse("asset-list"), {"action": "delete_asset", "pk": self.assets[autre].pk}).status_code in (302, 403), True)
            self.assertTrue(Asset.objects.filter(pk=self.assets[autre].pk).exists(), f"{qui} ne supprime pas {autre}")

    def test_creation_de_materiel_exige_un_service_rattache(self):
        donnees = {"action": "create_asset", "designation": "Neuf", "internal_id": "NEUF-1", "ship_id": self.navire.pk,
                   "asset_type_id": AssetType.objects.filter(sector=self.secteurs["Operations"]).first().pk,
                   "service_id": self.services["Operations"].pk, "sector_id": self.secteurs["Operations"].pk}
        self.assertEqual(self._post("comanav_a", reverse("asset-list"), donnees).status_code, 403)
        self.assertFalse(Asset.objects.filter(internal_id="NEUF-1").exists())


class OccurrencesEtInstallationsTests(BaseDroitsEcriture):
    def setUp(self):
        super().setUp()
        from maintenance.models import MaintenanceOccurrence, MaintenancePlan
        from django.utils import timezone
        self.occurrences = {}
        self.installations = {}
        for nom, service in self.services.items():
            plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.assets[nom], name=f"Plan {nom}", every_n_days=30)
            self.occurrences[nom] = MaintenanceOccurrence.objects.create(
                plan=plan, asset=self.assets[nom], scheduled_for=timezone.localdate(), status="PLANNED")
            self.installations[nom] = Installation.objects.create(
                designation=f"Installation {nom}", ship=self.navire, service=service, sector=self.secteurs[nom])

    def test_execution_d_une_occurrence_d_un_tiers_par_service(self):
        for qui, propre, autre in (("comanav_a", "Navigation", "Operations"), ("comops_a", "Operations", "Vie a bord"),
                                   ("comaeq_a", "Vie a bord", "Navigation")):
            refus = self._post(qui, reverse("occurrence-execute", args=[self.occurrences[autre].pk]), {"action": "enregistrer"})
            self.assertEqual(refus.status_code, 403, f"{qui} sur {autre}")
            accepte = self._post(qui, reverse("occurrence-execute", args=[self.occurrences[propre].pk]), {"action": "enregistrer"})
            self.assertNotEqual(accepte.status_code, 403, f"{qui} sur {propre}")

    def test_lecture_de_la_fiche_d_execution_ouverte(self):
        self.client.force_login(self.profils["comaeq_a"])
        for nom in self.occurrences:
            self.assertEqual(self.client.get(reverse("occurrence-execute", args=[self.occurrences[nom].pk])).status_code, 200, nom)

    def test_documents_d_installation_par_service(self):
        for qui, propre, autre in (("comanav_a", "Navigation", "Operations"), ("comops_a", "Operations", "Navigation")):
            refus = self._post(qui, reverse("installation-document-ajouter", args=[self.installations[autre].pk]), {"titre": "x"})
            self.assertEqual(refus.status_code, 403, f"{qui} sur {autre}")
            accepte = self._post(qui, reverse("installation-document-ajouter", args=[self.installations[propre].pk]), {"titre": "x"})
            self.assertNotEqual(accepte.status_code, 403, f"{qui} sur {propre}")

    def test_chef_de_service_et_de_secteur_sur_les_occurrences(self):
        for qui in ("chef_service_nav", "chef_secteur_nav"):
            ok = self._post(qui, reverse("occurrence-execute", args=[self.occurrences["Navigation"].pk]), {"action": "enregistrer"})
            self.assertNotEqual(ok.status_code, 403, qui)
            hors = self._post(qui, reverse("occurrence-execute", args=[self.occurrences["Operations"].pk]), {"action": "enregistrer"})
            self.assertIn(hors.status_code, (403, 404), qui)

    def test_equipage_b_a_terre_refuse_partout(self):
        for nom in self.occurrences:
            reponse = self._post("comaeq_b", reverse("occurrence-execute", args=[self.occurrences[nom].pk]), {"action": "enregistrer"})
            self.assertEqual(reponse.status_code, 403, nom)
