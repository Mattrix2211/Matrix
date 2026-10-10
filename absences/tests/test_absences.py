"""Tests du modèle générique d'absence/indisponibilité et de son workflow
de déclaration/validation (tâche Notion « Absences et indisponibilités »)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import AuditLog, TypeAbsence
from notifications.models import Notification
from org.models import Sector, Service, Ship
from quarts.models import CreneauServiceGarde, ServiceGarde
from absences.models import Absence
from absences.services import (
    absences_visibles,
    declarer_absence,
    marin_dans_perimetre,
    peut_gerer_absence_de,
    peut_valider_absence,
    valider_absence,
)


def _marin(nom, secteur=None, role="EQUIPIER"):
    user = User.objects.create_user(username=nom, password="pass")
    # Mute directement l'objet UserProfile déjà mis en cache par le signal
    # post_save (accounts/models.py) sur `user.profile`, plutôt que
    # UserProfile.objects.update_or_create(...) qui créerait un second objet
    # Python distinct : ce dernier laisserait `user.profile` (accédé plus
    # loin dans les tests via scope_filters_for_user/user_role_level) sur
    # l'ancienne valeur mise en cache (rôle/périmètre non renseignés), un
    # piège Django classique sur les relations OneToOne inversées.
    profile = user.profile
    profile.role = role
    profile.sector = secteur
    profile.save()
    return user


class BaseAbsenceTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Absences", code="ABS")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.sector = Sector.objects.create(service=self.service, name="Manœuvre")
        self.autre_secteur = Sector.objects.create(service=self.service, name="Autre")

        self.marin = _marin("marin_absent", self.sector)
        self.chef = _marin("chef_section", self.sector, role="CHEF_SECTION")
        self.chef_autre_secteur = _marin("chef_ailleurs", self.autre_secteur, role="CHEF_SECTION")
        self.collegue = _marin("collegue", self.sector)

        self.type_permission = TypeAbsence.objects.create(name="Permission")
        self.aujourdhui = timezone.localdate()


class ModeleAbsenceTests(BaseAbsenceTests):
    def test_date_fin_avant_date_debut_refusee(self):
        absence = Absence(
            marin=self.marin, type_absence=self.type_permission,
            date_debut=self.aujourdhui, date_fin=self.aujourdhui - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            absence.full_clean()

    def test_chevauche_creneau_periode_couverte(self):
        absence = Absence.objects.create(
            marin=self.marin, type_absence=self.type_permission,
            date_debut=self.aujourdhui, date_fin=self.aujourdhui + timedelta(days=2),
        )
        garde = ServiceGarde.objects.create(
            sector=self.sector, date_debut=self.aujourdhui, date_fin=self.aujourdhui + timedelta(days=5),
            statut=ServiceGarde.STATUT_PUBLIEE,
        )
        debut = timezone.make_aware(
            timezone.datetime.combine(self.aujourdhui + timedelta(days=1), timezone.datetime.min.time().replace(hour=8))
        )
        creneau_dedans = CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Garde", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin,
        )
        self.assertTrue(absence.chevauche_creneau(creneau_dedans))

        debut_hors = timezone.make_aware(
            timezone.datetime.combine(self.aujourdhui + timedelta(days=10), timezone.datetime.min.time().replace(hour=8))
        )
        creneau_dehors = CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Garde", debut=debut_hors, fin=debut_hors + timedelta(hours=4), marin=self.marin,
        )
        self.assertFalse(absence.chevauche_creneau(creneau_dehors))


class PermissionsAbsenceTests(BaseAbsenceTests):
    def test_marin_peut_toujours_gerer_sa_propre_absence(self):
        self.assertTrue(peut_gerer_absence_de(self.marin, self.marin))

    def test_chef_de_son_perimetre_peut_gerer(self):
        self.assertTrue(peut_gerer_absence_de(self.chef, self.marin))
        self.assertTrue(marin_dans_perimetre(self.chef, self.marin))

    def test_chef_d_un_autre_perimetre_ne_peut_pas(self):
        self.assertFalse(peut_gerer_absence_de(self.chef_autre_secteur, self.marin))

    def test_un_equipier_ne_gere_pas_l_absence_d_un_autre(self):
        self.assertFalse(peut_gerer_absence_de(self.collegue, self.marin))

    def test_le_marin_ne_valide_jamais_sa_propre_absence(self):
        absence = Absence.objects.create(
            marin=self.marin, type_absence=self.type_permission,
            date_debut=self.aujourdhui, date_fin=self.aujourdhui,
        )
        self.assertFalse(peut_valider_absence(self.marin, absence))

    def test_seul_un_chef_du_perimetre_valide(self):
        absence = Absence.objects.create(
            marin=self.marin, type_absence=self.type_permission,
            date_debut=self.aujourdhui, date_fin=self.aujourdhui,
        )
        self.assertTrue(peut_valider_absence(self.chef, absence))
        self.assertFalse(peut_valider_absence(self.chef_autre_secteur, absence))
        self.assertFalse(peut_valider_absence(self.collegue, absence))


class WorkflowAbsenceTests(BaseAbsenceTests):
    def test_marin_se_declare_statut_declaree_et_chef_notifie(self):
        absence = declarer_absence(
            self.marin, self.marin, self.type_permission, self.aujourdhui, self.aujourdhui + timedelta(days=3),
            motif="Convocation familiale",
        )
        self.assertEqual(absence.statut, Absence.STATUT_DECLAREE)
        self.assertTrue(
            Notification.objects.filter(user=self.chef, verb__contains="a déclaré une absence").exists()
        )
        self.assertTrue(AuditLog.objects.filter(action="absence_declaration", target_user=self.marin).exists())

    def test_chef_declare_pour_son_equipe_directement_validee(self):
        absence = declarer_absence(
            self.chef, self.marin, self.type_permission, self.aujourdhui, self.aujourdhui,
        )
        self.assertEqual(absence.statut, Absence.STATUT_VALIDEE)
        self.assertEqual(absence.validee_par, self.chef)
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="enregistré votre absence").exists())

    def test_declarer_pour_un_marin_hors_perimetre_refuse(self):
        with self.assertRaises(PermissionError):
            declarer_absence(
                self.chef_autre_secteur, self.marin, self.type_permission, self.aujourdhui, self.aujourdhui,
            )

    def test_validation_par_le_chef_notifie_le_marin_et_trace(self):
        absence = declarer_absence(
            self.marin, self.marin, self.type_permission, self.aujourdhui, self.aujourdhui,
        )
        valider_absence(absence, self.chef)
        absence.refresh_from_db()
        self.assertEqual(absence.statut, Absence.STATUT_VALIDEE)
        self.assertEqual(absence.validee_par, self.chef)
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="a validé votre absence").exists())
        self.assertTrue(AuditLog.objects.filter(action="absence_validation").exists())

    def test_validation_par_un_intrus_refusee(self):
        absence = declarer_absence(
            self.marin, self.marin, self.type_permission, self.aujourdhui, self.aujourdhui,
        )
        with self.assertRaises(PermissionError):
            valider_absence(absence, self.collegue)

    def test_absences_visibles_marin_ne_voit_que_les_siennes(self):
        declarer_absence(self.marin, self.marin, self.type_permission, self.aujourdhui, self.aujourdhui)
        declarer_absence(self.collegue, self.collegue, self.type_permission, self.aujourdhui, self.aujourdhui)
        visibles = absences_visibles(self.collegue)
        self.assertEqual(list(visibles.values_list("marin", flat=True)), [self.collegue.pk])

    def test_absences_visibles_chef_voit_son_perimetre(self):
        declarer_absence(self.marin, self.marin, self.type_permission, self.aujourdhui, self.aujourdhui)
        visibles = absences_visibles(self.chef)
        self.assertIn(self.marin.pk, list(visibles.values_list("marin", flat=True)))
