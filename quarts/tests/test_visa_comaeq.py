"""Routage du visa de la feuille de service vers le titulaire du poste de COMAEQ
(tâche Notion « Router le visa de la feuille de service quotidienne vers le
titulaire COMAEQ ») : titulaire du bâtiment/équipage de la feuille, poste
vacant -> escalade au commandant (et au commandant en second si le droit lui
est confié), traçabilité et notifications."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from notifications.models import Notification
from org.models import CommandantAdjoint, CommandantEnSecond, Equipage, RoleThresholdConfig, Ship
from quarts.models import FeuilleService, peut_lire_feuille_service, peut_viser_comaeq, titulaire_comaeq


def _marin(username, role, ship, equipage=None):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class VisaComaeqEquipageUniqueTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="BRF Visa", code="BV")
        self.autre = Ship.objects.create(name="Autre", code="AU")
        self.comaeq = _marin("comaeq", "ETAT_MAJOR", self.ship)
        self.comops = _marin("comops", "ETAT_MAJOR", self.ship)
        self.commandant = _marin("cdt", "COMMANDANT", self.ship)
        self.cdt_autre = _marin("cdt_autre", "COMMANDANT", self.autre)
        self.poste = CommandantAdjoint.objects.create(ship=self.ship, sigle="COMAEQ", titulaire=self.comaeq)
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, date=timezone.localdate(), statut=FeuilleService.STATUT_VISA_COMAEQ,
            created_by=self.comops,
        )

    def test_seul_le_titulaire_du_poste_comaeq_vise(self):
        self.assertEqual(titulaire_comaeq(self.feuille), self.comaeq)
        self.assertTrue(peut_viser_comaeq(self.comaeq, self.feuille))
        self.assertFalse(peut_viser_comaeq(self.comops, self.feuille))

    def test_le_commandant_du_batiment_peut_viser_pas_celui_d_un_autre(self):
        self.assertTrue(peut_viser_comaeq(self.commandant, self.feuille))
        self.assertFalse(peut_viser_comaeq(self.cdt_autre, self.feuille))

    def test_seul_le_titulaire_est_notifie(self):
        self.assertEqual(self.feuille.validateurs_a_notifier(), [self.comaeq])

    def test_titulaire_desactive_equivaut_a_un_poste_vacant(self):
        self.comaeq.is_active = False
        self.comaeq.save()
        self.assertIsNone(titulaire_comaeq(self.feuille))

    def test_titulaire_d_un_autre_batiment_ignore(self):
        UserProfile.objects.filter(user=self.comaeq).update(ship=self.autre)
        self.assertIsNone(titulaire_comaeq(self.feuille))

    def test_poste_vacant_escalade_au_commandant_avec_trace_et_notification(self):
        self.poste.titulaire = None
        self.poste.save()
        self.assertFalse(peut_viser_comaeq(self.comaeq, self.feuille))
        self.assertTrue(peut_viser_comaeq(self.commandant, self.feuille))
        self.feuille._notifier_prochain_visa()
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_comaeq_vacant").exists())
        notification = Notification.objects.get(user=self.commandant)
        self.assertIn("COMAEQ vacant", notification.verb)
        self.assertFalse(Notification.objects.filter(user=self.cdt_autre).exists())

    def test_poste_inexistant_traite_comme_vacant(self):
        self.poste.delete()
        self.assertIsNone(titulaire_comaeq(self.feuille))
        self.assertTrue(peut_viser_comaeq(self.commandant, self.feuille))
        self.assertFalse(peut_viser_comaeq(self.comaeq, self.feuille))

    def test_commandant_en_second_vise_seulement_si_le_droit_est_confie(self):
        self.poste.titulaire = None
        self.poste.save()
        second = _marin("second", "ETAT_MAJOR", self.ship)
        CommandantEnSecond.objects.create(ship=self.ship, titulaire=second)
        self.assertFalse(peut_viser_comaeq(second, self.feuille))
        RoleThresholdConfig.objects.create(ship=self.ship, droits_en_second=["feuille_service_visa_comaeq"])
        self.assertTrue(peut_viser_comaeq(second, self.feuille))

    def test_le_droit_du_second_ne_joue_pas_si_le_poste_est_tenu(self):
        second = _marin("second", "ETAT_MAJOR", self.ship)
        CommandantEnSecond.objects.create(ship=self.ship, titulaire=second)
        RoleThresholdConfig.objects.create(ship=self.ship, droits_en_second=["feuille_service_visa_comaeq"])
        self.assertFalse(peut_viser_comaeq(second, self.feuille))

    def test_l_etat_major_non_titulaire_ne_lit_plus_via_le_visa(self):
        autre = _marin("autre_em", "ETAT_MAJOR", self.ship)
        self.assertFalse(peut_lire_feuille_service(autre, self.feuille))


class VisaComaeqDoubleEquipageTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="FREMM Visa", code="FV", classe_navire="FREMM", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.ship, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.ship, nom="Rouge")
        self.comaeq_bleu = _marin("comaeq_bleu", "ETAT_MAJOR", self.ship, self.bleu)
        self.comaeq_rouge = _marin("comaeq_rouge", "ETAT_MAJOR", self.ship, self.rouge)
        self.poste_bleu = CommandantAdjoint.objects.create(
            ship=self.ship, equipage=self.bleu, sigle="COMAEQ", titulaire=self.comaeq_bleu,
        )
        CommandantAdjoint.objects.create(
            ship=self.ship, equipage=self.rouge, sigle="COMAEQ", titulaire=self.comaeq_rouge,
        )
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, equipage=self.bleu, date=timezone.localdate(),
            statut=FeuilleService.STATUT_VISA_COMAEQ,
        )

    def test_le_titulaire_est_celui_de_l_equipage_de_la_feuille(self):
        self.assertEqual(titulaire_comaeq(self.feuille), self.comaeq_bleu)
        self.assertTrue(peut_viser_comaeq(self.comaeq_bleu, self.feuille))
        self.assertFalse(peut_viser_comaeq(self.comaeq_rouge, self.feuille))

    def test_titulaire_passe_dans_l_autre_equipage_est_ignore(self):
        UserProfile.objects.filter(user=self.comaeq_bleu).update(equipage=self.rouge)
        self.comaeq_bleu = User.objects.get(pk=self.comaeq_bleu.pk)
        self.assertIsNone(titulaire_comaeq(self.feuille))
        self.assertFalse(peut_viser_comaeq(self.comaeq_bleu, self.feuille))

    def test_poste_vacant_d_un_equipage_n_escalade_pas_a_l_autre_equipage(self):
        self.poste_bleu.titulaire = None
        self.poste_bleu.save()
        commandant_rouge = _marin("cdt_rouge", "COMMANDANT", self.ship, self.rouge)
        commandant_bleu = _marin("cdt_bleu", "COMMANDANT", self.ship, self.bleu)
        self.assertFalse(peut_viser_comaeq(commandant_rouge, self.feuille))
        self.assertTrue(peut_viser_comaeq(commandant_bleu, self.feuille))
        self.assertEqual(self.feuille.validateurs_a_notifier(), [commandant_bleu])
