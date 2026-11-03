"""Circuit complet de la feuille de service sur les deux équipages : le rédacteur (BSC) suit sa feuille pendant la
validation sans pouvoir la modifier, un renvoi explicite la lui rend, et le COMAEQ de l'équipage la publie d'un seul
bouton « Publier », de façon atomique et sans conserver un visa devenu invalide."""
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from org.models import Sector, Service, Ship
from quarts.models import FeuilleService, RedacteurFeuilleService, RubriqueEnTeteFeuilleService


class CircuitFeuilleDeuxEquipagesTests(TestCase):
    def setUp(self):
        self.client.raise_request_exception = False
        self.ship = Ship.objects.create(name="Frégate circuit", code="FC", double_equipage=True, equipage_a_bord="A")
        self.service = Service.objects.create(ship=self.ship, name="Pont", commandant_adjoint="COMAEQ")
        self.secteur = Sector.objects.create(service=self.service, name="Manoeuvre")
        RubriqueEnTeteFeuilleService.objects.create(ship=self.ship, ordre=1, libelle="Type de journée", type_saisie="QUOTIDIENNE")
        self.jour = timezone.localdate()
        self.url = f"/quarts/feuille-service/{self.ship.pk}/{self.jour.isoformat()}/"
        self.equipes = {}
        for eq in ("A", "B"):
            e = {
                "bsc": self._marin(f"bsc_{eq}", "EQUIPIER", eq, sector=self.secteur),
                "chef_secteur": self._marin(f"chefsect_{eq}", "CHEF_SECTEUR", eq, sector=self.secteur),
                "chef_service": self._marin(f"chefserv_{eq}", "CHEF_SERVICE", eq, service=self.service),
                "comaeq": self._marin(f"comaeq_{eq}", "ETAT_MAJOR", eq, fonction_coma="COMAEQ"),
            }
            RedacteurFeuilleService.objects.create(ship=self.ship, equipage=eq, user=e["bsc"])
            self.equipes[eq] = e
        self.comanav = self._marin("comanav_x", "ETAT_MAJOR", "A", fonction_coma="COMANAV")

    def _marin(self, nom, role, equipage, **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.ship, "equipage": equipage, **champs})
        return User.objects.get(pk=user.pk)

    def _agir(self, user, action, **donnees):
        self.client.force_login(user)
        return self.client.post(self.url, {"action": action, **donnees})

    def _feuille(self, eq):
        return FeuilleService.objects.get(ship=self.ship, equipage=eq, date=self.jour)

    def _proposer(self, eq):
        e = self.equipes[eq]
        self._agir(e["bsc"], "creer")
        self._agir(e["bsc"], "enregistrer_entete")
        self._agir(e["bsc"], "proposer")
        return self._feuille(eq)

    def _publier_comme(self, user):
        self.client.force_login(user)
        page = self.client.get(self.url)
        return self.client.post(self.url, {"action": "viser_comaeq", "jeton_visa": page.context["jeton_visa"]})

    def test_le_bsc_suit_sa_feuille_proposee_en_lecture_seule_sur_les_deux_equipages(self):
        for eq in ("A", "B"):
            bsc = self.equipes[eq]["bsc"]
            feuille = self._proposer(eq)
            self.assertEqual(feuille.statut, FeuilleService.STATUT_VISA_SECTEUR, eq)
            self.client.force_login(bsc)
            page = self.client.get(self.url)
            self.assertEqual(page.status_code, 200, f"équipage {eq}")
            self.assertNotContains(page, 'value="enregistrer_entete"')
            self.assertEqual(self._agir(bsc, "enregistrer_entete").status_code, 403, eq)
            self.assertEqual(self._agir(bsc, "proposer").status_code, 403, eq)

    def test_un_marin_non_redacteur_ne_voit_toujours_pas_la_copie_de_travail(self):
        self._proposer("A")
        autre = self._marin("simple_A", "EQUIPIER", "A", sector=self.secteur)
        self.client.force_login(autre)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_le_renvoi_explicite_rend_la_modification_et_efface_les_visas(self):
        e = self.equipes["A"]
        self._proposer("A")
        self._agir(e["chef_secteur"], "viser_secteur")
        self.assertEqual(self._agir(e["chef_service"], "renvoyer", motif="Précisions à apporter").status_code, 302)
        feuille = self._feuille("A")
        self.assertEqual(feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertIsNone(feuille.visa_secteur_par)
        self.assertEqual(self._agir(e["bsc"], "enregistrer_entete").status_code, 302)

    def test_publier_un_seul_bouton_publie_atomiquement_chaque_equipage(self):
        for eq in ("A", "B"):
            e = self.equipes[eq]
            self._proposer(eq)
            self._agir(e["chef_secteur"], "viser_secteur")
            self._agir(e["chef_service"], "viser_service")
            self.client.force_login(e["comaeq"])
            page = self.client.get(self.url)
            self.assertContains(page, "Publier")
            self.assertNotContains(page, "Viser et publier")
            self._publier_comme(e["comaeq"])
            feuille = self._feuille(eq)
            self.assertEqual(feuille.statut, FeuilleService.STATUT_PUBLIEE, eq)
            self.assertEqual((feuille.publiee_par, feuille.visa_comaeq_par), (e["comaeq"], e["comaeq"]))
            self.assertIsNotNone(feuille.publiee_le)
            self.assertEqual(feuille.versions.count(), 1)
            self.assertTrue(AuditLog.objects.filter(actor=e["comaeq"], action="feuille_service_publiee").exists())
            self.client.force_login(e["bsc"])
            self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_le_comaeq_de_l_autre_equipage_et_un_autre_commandant_adjoint_ne_publient_pas(self):
        e = self.equipes["A"]
        self._proposer("A")
        self._agir(e["chef_secteur"], "viser_secteur")
        self._agir(e["chef_service"], "viser_service")
        for intrus in (self.equipes["B"]["comaeq"], self.comanav):
            self.client.force_login(e["comaeq"])
            jeton = self.client.get(self.url).context["jeton_visa"]
            self.client.force_login(intrus)
            reponse = self.client.post(self.url, {"action": "viser_comaeq", "jeton_visa": jeton})
            self.assertIn(reponse.status_code, (403, 404), intrus.username)
        self.assertEqual(self._feuille("A").statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertEqual(self._feuille("A").versions.count(), 0)

    def test_une_publication_qui_echoue_ne_laisse_ni_version_ni_statut_publie(self):
        e = self.equipes["A"]
        self._proposer("A")
        self._agir(e["chef_secteur"], "viser_secteur")
        self._agir(e["chef_service"], "viser_service")
        with mock.patch.object(FeuilleService, "creer_version", side_effect=RuntimeError("panne")):
            self._publier_comme(e["comaeq"])
        feuille = self._feuille("A")
        self.assertEqual(feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertEqual(feuille.versions.count(), 0)
        self.assertIsNone(feuille.publiee_par)
