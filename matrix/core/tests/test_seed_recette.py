"""Tests de la commande `seed_recette` : idempotence, additivité, garde-fou et jeu minimal."""
import os
from io import StringIO
from unittest import mock

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from absences.models import Absence
from annonces.models import Annonce
from documentation.services import documents_associes
from maintenance.models import MaintenanceOccurrence
from notifications.models import Notification
from matrix.core.commandants_adjoints import titulaires_du_service
from org.models import Service
from quarts.models import ChefDeListe, CreneauQuart
from taches.models import Tache
from training.models import CandidatureFormation, ReferentFormation, peut_valider_formation


def _lancer(commande):
    call_command(commande, stdout=StringIO(), stderr=StringIO())


def _compteurs():
    return {m._meta.label: m.objects.count() for m in apps.get_models(include_auto_created=True)}


def _instantane():
    return {m._meta.label: {repr(sorted(ligne.items())) for ligne in m.objects.values()}
            for m in apps.get_models(include_auto_created=True)}


@override_settings(DEBUG=True)
class SeedRecetteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _lancer("seed_demo")

    def test_idempotent(self):
        _lancer("seed_recette")
        avant = _compteurs()
        _lancer("seed_recette")
        self.assertEqual(avant, _compteurs())

    def test_additif_sur_la_demo(self):
        demo = _instantane()
        _lancer("seed_recette")
        apres = _instantane()
        for modele, lignes in demo.items():
            self.assertTrue(lignes <= apres[modele], f"Objet de démonstration modifié ou supprimé : {modele}")

    def test_refus_hors_debug(self):
        with override_settings(DEBUG=False), mock.patch.dict(os.environ, {"MATRIX_RECETTE": "0"}):
            with self.assertRaises(CommandError):
                _lancer("seed_recette")
        self.assertFalse(User.objects.filter(username="equipier_a3").exists())

    def test_autorise_avec_variable_hors_debug(self):
        with override_settings(DEBUG=False), mock.patch.dict(os.environ, {"MATRIX_RECETTE": "1"}):
            _lancer("seed_recette")
        self.assertTrue(User.objects.filter(username="equipier_a3").exists())


@override_settings(DEBUG=True)
class SeedRecetteBaseVideTests(TestCase):
    def test_lance_la_demo_au_besoin(self):
        _lancer("seed_recette")
        self.assertTrue(User.objects.filter(username__in=["equipier_a", "equipier_a3"]).count() == 2)


@override_settings(DEBUG=True)
class JeuMinimalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _lancer("seed_demo")
        _lancer("seed_recette")
        cls.a3 = User.objects.get(username="equipier_a3")
        cls.referent = User.objects.get(username="referent_formation_a")

    def test_julien(self):
        profil = self.a3.profile
        self.assertEqual((profil.role, profil.equipage, profil.grade, profil.specialite),
                         ("EQUIPIER", "A", "Quartier-maître", "Mécanique"))
        self.assertEqual(profil.sector.name, "Moteurs")
        self.assertEqual(profil.section.name, "Moteurs bâbord")
        self.assertTrue(self.a3.check_password("pass"))

    def test_maintenance_documentation_et_qualification(self):
        occ = MaintenanceOccurrence.objects.get(
            assignees=self.a3, installation_maintenance__title__contains="Contrôle trimestriel")
        fiche = occ.installation_maintenance
        self.assertEqual(fiche.installation.designation, "[Recette] Pompe d'incendie principale")
        qualification = fiche.version_validee.qualification
        self.assertIsNotNone(qualification)
        self.assertTrue(self.a3.training_records.filter(course=qualification, expires_at__gt=occ.scheduled_for).exists())
        self.assertEqual(documents_associes(self.a3, fiche.installation).count(), 1)

    def test_referent_n_est_ni_chef_de_secteur_ni_chef_de_liste(self):
        self.assertEqual(self.referent.profile.role, "EQUIPIER")
        self.assertEqual(self.referent.profile.equipage, "A")
        self.assertFalse(ChefDeListe.objects.filter(user=self.referent).exists())
        self.assertFalse(self.referent.profile.fonction_coma)

    def test_perimetre_du_referent(self):
        a_traiter = CandidatureFormation.objects.get(statut="TRANSMITTED", course__title__contains="Conduite du réseau")
        hors_ressort = CandidatureFormation.objects.get(statut="TRANSMITTED", course__title__contains="Travaux en hauteur")
        navire = self.referent.profile.ship
        self.assertEqual(ReferentFormation.objects.filter(user=self.referent).count(), 1)
        self.assertTrue(peut_valider_formation(self.referent, a_traiter.course, navire))
        self.assertFalse(peut_valider_formation(self.referent, hors_ressort.course, navire))

    def test_situations(self):
        self.assertTrue(Tache.objects.filter(titre__startswith="[Recette]", statut="A_FAIRE").exists())
        self.assertTrue(Annonce.objects.filter(titre__startswith="[Recette]", accuse_requis=True).count() >= 2)
        self.assertTrue(Notification.objects.filter(user=self.a3, verb__startswith="[Recette]").exists())
        # Conflit : une absence validée recouvre un créneau d'un quart publié.
        absence = Absence.objects.get(marin=self.a3, motif__startswith="[Recette]")
        creneaux = CreneauQuart.objects.filter(marin=self.a3, quart__statut="PUBLIEE")
        self.assertTrue(any(absence.chevauche_creneau(c) for c in creneaux))

    def test_couverture_des_perimetres(self):
        for compte in ("marin_b", "equipier_elec_a", "equipier_nor"):
            self.assertTrue(Tache.objects.filter(assigne__username=compte, titre__startswith="[Recette]").exists(), compte)
        self.assertTrue(Absence.objects.filter(marin__username="equipier_nor").exists())


@override_settings(DEBUG=True)
class ComaRecetteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _lancer("seed_demo")
        _lancer("seed_recette")

    def test_rattachements(self):
        attendus = {
            "coma_comanav_b": ("BRE", "B", "COMANAV"), "coma_comaeq_b": ("BRE", "B", "COMAEQ"),
            "coma_comanav_nor": ("NOR", "", "COMANAV"), "coma_comaeq_nor": ("NOR", "", "COMAEQ"),
        }
        for nom, (navire, equipage, fonction) in attendus.items():
            profil = User.objects.get(username=nom).profile
            self.assertEqual((profil.role, profil.ship.code, profil.equipage, profil.fonction_coma),
                             ("ETAT_MAJOR", navire, equipage, fonction), nom)

    def test_titulaires_par_service_et_equipage(self):
        def titulaires(navire, service, equipage=""):
            return set(titulaires_du_service(Service.objects.get(ship__code=navire, name=service), equipage)
                       .values_list("username", flat=True))
        self.assertEqual(titulaires("BRE", "Propulsion", "B"), {"coma_comanav_b"})
        self.assertEqual(titulaires("BRE", "Sécurité", "B"), {"coma_comaeq_b"})
        self.assertEqual(titulaires("BRE", "Propulsion", "A"), {"coma_comanav"})
        self.assertEqual(titulaires("NOR", "Propulsion"), {"coma_comanav_nor"})
        self.assertEqual(titulaires("NOR", "Sécurité"), {"coma_comaeq_nor"})

    def test_service_volontairement_sans_titulaire(self):
        operations = Service.objects.get(ship__code="BRE", name="Opérations")
        self.assertEqual(operations.commandant_adjoint, "COMOPS")
        self.assertFalse(titulaires_du_service(operations, "B").exists())
        self.assertTrue(titulaires_du_service(operations, "A").exists())

    def test_additif_et_idempotent_sur_les_coma(self):
        avant = _compteurs()
        _lancer("seed_recette")
        self.assertEqual(avant, _compteurs())
        self.assertEqual(User.objects.filter(profile__fonction_coma__gt="", profile__ship__code="NOR").count(), 2)
