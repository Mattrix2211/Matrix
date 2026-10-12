"""Vue COMANAV : accès, périmètre du bâtiment, étanchéité par équipage et contenu de chaque bloc."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType, Installation, InstallationIsolationReading, InstallationMaintenance
from logistics.models import Anomalie, CorrectiveTicket, StockPiece
from maintenance.models import CompteRenduCorrectif, MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship
from rondes.models import Ronde

URL = "/dashboard/comanav/"


class BaseComanav(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire alpha", code="ALP")
        self.autre = Ship.objects.create(name="Navire bravo", code="BRA")
        self.service, self.secteur, self.type_asset = self._organisation(self.navire, "A")
        self.service_b, self.secteur_b, self.type_b = self._organisation(self.autre, "B")
        self.comanav = self._marin("comanav", "ETAT_MAJOR", self.navire, fonction_coma="COMANAV")

    def _organisation(self, navire, suffixe):
        service = Service.objects.create(ship=navire, name=f"Service {suffixe}")
        secteur = Sector.objects.create(service=service, name=f"Secteur {suffixe}")
        return service, secteur, AssetType.objects.create(name=f"Type {suffixe}", category="Cat", sector=secteur)

    def _marin(self, nom, role, navire, **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.filter(user=user).update(role=role, ship=navire, **champs)
        return User.objects.get(pk=user.pk)

    def _materiel(self, navire=None, **champs):
        navire = navire or self.navire
        service, secteur = (self.service, self.secteur) if navire == self.navire else (self.service_b, self.secteur_b)
        type_asset = self.type_asset if navire == self.navire else self.type_b
        return Asset.objects.create(asset_type=type_asset, ship=navire, service=service, sector=secteur, **champs)

    def _installation(self, navire=None, **champs):
        navire = navire or self.navire
        service, secteur = (self.service, self.secteur) if navire == self.navire else (self.service_b, self.secteur_b)
        return Installation.objects.create(designation=champs.pop("designation", "Groupe"), ship=navire, service=service,
                                          sector=secteur, **champs)

    def _page(self, user):
        self.client.force_login(user)
        return self.client.get(URL)

    def _bloc(self, reponse, titre):
        return next(b for b in reponse.context["blocs"] if b["titre"] == titre)

    def _valeur(self, reponse, titre, libelle_debut):
        bloc = self._bloc(reponse, titre)
        return next(i["valeur"] for i in bloc["indicateurs"] if i["libelle"].startswith(libelle_debut))


class AccesTests(BaseComanav):
    def test_comanav_commandement_et_admin_ont_acces(self):
        for nom, role in (("cdt", "COMMANDANT"), ("cdt2", "COMMANDANT_EN_SECOND"), ("adm", "ADMIN_NAVIRE"), ("mas", "MASTER_ADMIN")):
            with self.subTest(role=role):
                self.assertEqual(self._page(self._marin(nom, role, self.navire)).status_code, 200)
        self.assertEqual(self._page(self.comanav).status_code, 200)

    def test_refuse_aux_autres(self):
        autres = [
            self._marin("simple", "EQUIPIER", self.navire),
            self._marin("chef", "CHEF_SERVICE", self.navire),
            self._marin("comaeq", "ETAT_MAJOR", self.navire, fonction_coma="COMAEQ"),
            self._marin("etat_major", "ETAT_MAJOR", self.navire),
            self._marin("sans_navire", "COMMANDANT", None),
        ]
        for user in autres:
            with self.subTest(user=user.username):
                self.assertEqual(self._page(user).status_code, 403)

    def test_anonyme_redirige(self):
        self.assertEqual(self.client.get(URL).status_code, 302)

    def test_comanav_inactif_refuse(self):
        User.objects.filter(pk=self.comanav.pk).update(is_active=False)
        self.client.force_login(User.objects.get(pk=self.comanav.pk))
        self.assertIn(self.client.get(URL).status_code, (302, 403))

    def test_lien_de_menu_ssi_acces(self):
        simple = self._marin("simple", "EQUIPIER", self.navire)
        self.client.force_login(simple)
        self.assertNotContains(self.client.get(reverse("home")), URL)
        self.client.force_login(self.comanav)
        self.assertContains(self.client.get(reverse("home")), URL)

    def test_administrateur_sans_batiment_choisi(self):
        mas = self._marin("mas", "MASTER_ADMIN", None)
        reponse = self._page(mas)
        self.assertContains(reponse, "Aucun bâtiment sélectionné")


class PerimetreTests(BaseComanav):
    def test_aucune_donnee_d_un_autre_navire(self):
        marque = "ZZFUITEZZ"
        materiel = self._materiel(self.autre, status="FAULTY")
        installation = self._installation(self.autre, designation=marque, critique=True)
        CorrectiveTicket.objects.create(asset=materiel, description=marque, status="WAITING_PARTS")
        StockPiece.objects.create(reference=marque, designation=marque, ship=self.autre, service=self.service_b,
                                  sector=self.secteur_b, quantite=0, quantite_minimale=5)
        Anomalie.objects.create(titre=marque, ship=self.autre, service=self.service_b, sector=self.secteur_b)
        Ronde.objects.create(nom=marque, ship=self.autre, date_prevue=date(2020, 1, 1))
        InstallationMaintenance.objects.create(installation=installation, periodicity="3 mois", title=marque)
        reponse = self._page(self.comanav)
        self.assertNotContains(reponse, marque)
        for bloc in reponse.context["blocs"]:
            for indicateur in bloc["indicateurs"]:
                self.assertEqual(indicateur["valeur"], 0, (bloc["titre"], indicateur["libelle"]))

    def test_comanav_rattache_par_son_service_voit_tout_son_batiment(self):
        UserProfile.objects.filter(user=self.comanav).update(service=self.service)
        self._materiel(status="FAULTY")
        self._materiel(status="OUT_OF_SERVICE")
        reponse = self._page(User.objects.get(pk=self.comanav.pk))
        self.assertEqual(self._valeur(reponse, "Indisponibilités", "Matériels défectueux"), 1)
        self.assertEqual(self._valeur(reponse, "Indisponibilités", "Matériels hors service"), 1)


class EtancheiteEquipageTests(BaseComanav):
    def test_equipage_a_terre_ne_voit_pas_les_tickets_de_l_autre_equipage(self):
        Ship.objects.filter(pk=self.navire.pk).update(double_equipage=True, equipage_a_bord="A")
        terre = self._marin("comanav_b", "ETAT_MAJOR", self.navire, fonction_coma="COMANAV", equipage="B")
        bord = self._marin("marin_a", "EQUIPIER", self.navire, equipage="A")
        materiel = self._materiel()
        ticket = CorrectiveTicket.objects.create(asset=materiel, description="Panne", status="WAITING_PARTS")
        ticket.assignees.add(bord)
        CorrectiveTicket.objects.create(asset=materiel, description="Libre", status="WAITING_PARTS")
        reponse = self._page(terre)
        self.assertEqual(self._valeur(reponse, "Logistique", "Tickets en attente de pièces"), 1)
        UserProfile.objects.filter(user=self.comanav).update(equipage="A")
        reponse = self._page(User.objects.get(pk=self.comanav.pk))
        self.assertEqual(self._valeur(reponse, "Logistique", "Tickets en attente de pièces"), 2)


class BlocsTests(BaseComanav):
    def test_interventions_et_maintenances(self):
        materiel = self._materiel()
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=materiel, name="Plan", every_n_days=30)
        MaintenanceOccurrence.objects.create(plan=plan, asset=materiel, scheduled_for="2020-01-01", status="OVERDUE")
        MaintenanceOccurrence.objects.create(plan=plan, asset=materiel, scheduled_for="2099-01-01", status="PLANNED")
        fait = MaintenanceOccurrence.objects.create(plan=plan, asset=materiel, scheduled_for="2026-01-01", status="DONE")
        MaintenanceExecution.objects.create(occurrence=fait, completed_at=timezone.now(), conformity="NON_CONFORME")
        ancienne = MaintenanceOccurrence.objects.create(plan=plan, asset=materiel, scheduled_for="2025-01-01", status="DONE")
        MaintenanceExecution.objects.create(occurrence=ancienne, completed_at=timezone.now() - timedelta(days=90), conformity="CONFORME")
        ticket = CorrectiveTicket.objects.create(asset=materiel, description="Panne", status="IN_REPAIR")
        CompteRenduCorrectif.objects.create(ticket=ticket, completed_at=timezone.now(), conformity="CONFORME")
        reponse = self._page(self.comanav)
        self.assertEqual(self._valeur(reponse, "Interventions", "Comptes rendus"), 2)
        self.assertEqual(self._valeur(reponse, "Interventions", "Avec réserve"), 1)
        self.assertEqual(self._valeur(reponse, "Interventions", "Maintenances en retard"), 1)
        # Le compte rendu non conforme ouvre lui-même un ticket (signal), en plus de la panne en réparation.
        self.assertEqual(self._valeur(reponse, "Interventions", "Tickets correctifs ouverts"), 2)
        self.assertEqual(len(self._bloc(reponse, "Interventions")["lignes"]), 2)

    def test_derives(self):
        installation = self._installation(isolation_seuil_ohms=500_000)
        for i in range(5):
            InstallationIsolationReading.objects.create(
                installation=installation, date=date(2026, 1, 1) + timedelta(days=i), ohms=1_000_000 - i * 100_000)
        self._installation(designation="Stable", isolation_seuil_ohms=500_000)
        reponse = self._page(self.comanav)
        bloc = self._bloc(reponse, "Dérives")
        self.assertEqual(bloc["indicateurs"][0]["valeur"], 1)
        self.assertEqual(bloc["lignes"][0]["titre"], "Groupe")
        self.assertIn("Dérive de l'isolement", bloc["lignes"][0]["detail"])

    def test_indisponibilites(self):
        self._materiel(status="FAULTY")
        self._materiel(status="OUT_OF_SERVICE")
        self._materiel(status="OUT_OF_SERVICE")
        self._materiel(status="OK")
        critique = self._installation(critique=True)
        self._installation(designation="Ordinaire")
        fiche = InstallationMaintenance.objects.create(installation=critique, periodicity="3 mois", title="Vidange")
        MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for="2020-01-01", status="OVERDUE")
        reponse = self._page(self.comanav)
        self.assertEqual(self._valeur(reponse, "Indisponibilités", "Matériels hors service"), 2)
        self.assertEqual(self._valeur(reponse, "Indisponibilités", "Matériels défectueux"), 1)
        self.assertEqual(self._valeur(reponse, "Indisponibilités", "Installations critiques"), 1)
        liens = [i["url"] for i in self._bloc(reponse, "Indisponibilités")["indicateurs"]]
        self.assertIn(f"{reverse('asset-list')}?status=OUT_OF_SERVICE", liens)

    def test_chaine_securite(self):
        Anomalie.objects.create(titre="Fuite", gravite=5, ship=self.navire)
        Anomalie.objects.create(titre="Bruit", gravite=2, ship=self.navire, statut="PRISE_EN_COMPTE")
        Anomalie.objects.create(titre="Réglée", ship=self.navire, statut="CLOTUREE")
        Ronde.objects.create(nom="Passée", ship=self.navire, date_prevue=date(2020, 1, 1))
        Ronde.objects.create(nom="Faite", ship=self.navire, date_prevue=date(2020, 1, 1), statut=Ronde.TERMINEE)
        Ronde.objects.create(nom="Future", ship=self.navire, date_prevue=timezone.localdate() + timedelta(days=3))
        reponse = self._page(self.comanav)
        self.assertEqual(self._valeur(reponse, "Chaîne sécurité", "Anomalies ouvertes"), 2)
        self.assertEqual(self._valeur(reponse, "Chaîne sécurité", "Rondes en retard"), 1)
        self.assertEqual(self._valeur(reponse, "Chaîne sécurité", "Qualifications"), 0)

    def test_logistique(self):
        materiel = self._materiel()
        CorrectiveTicket.objects.create(asset=materiel, description="Attente", status="WAITING_PARTS")
        CorrectiveTicket.objects.create(asset=materiel, description="Ouvert", status="REPORTED")
        StockPiece.objects.create(reference="R1", designation="Joint", ship=self.navire, service=self.service,
                                  sector=self.secteur, quantite=1, quantite_minimale=5)
        StockPiece.objects.create(reference="R2", designation="Vis", ship=self.navire, service=self.service,
                                  sector=self.secteur, quantite=9, quantite_minimale=5)
        reponse = self._page(self.comanav)
        self.assertEqual(self._valeur(reponse, "Logistique", "Tickets en attente de pièces"), 1)
        self.assertEqual(self._valeur(reponse, "Logistique", "Pièces sous le seuil"), 1)
        self.assertContains(reponse, "R1 — Joint")

    def test_page_vide_affiche_les_etats_vides(self):
        reponse = self._page(self.comanav)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Aucune dérive détectée")
        self.assertContains(reponse, "Stock conforme")
