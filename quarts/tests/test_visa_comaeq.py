"""Routage du visa de la feuille de service vers le titulaire du poste de COMAEQ
(tâche Notion « Router le visa de la feuille de service quotidienne vers le
titulaire COMAEQ ») : titulaire (fonction de commandant adjoint COMAEQ) du
bâtiment/équipage de la feuille, poste vacant -> escalade au commandant,
traçabilité et notifications."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from notifications.models import Notification
from org.models import Ship
from quarts.models import FeuilleService, peut_lire_feuille_service, peut_viser_comaeq, titulaire_comaeq


def _marin(username, role, ship, equipage="", fonction_coma=""):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(
        user=user, defaults={"role": role, "ship": ship, "equipage": equipage, "fonction_coma": fonction_coma}
    )
    return User.objects.get(pk=user.pk)


class VisaComaeqEquipageUniqueTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="BRF Visa", code="BV")
        self.autre = Ship.objects.create(name="Autre", code="AU")
        self.comaeq = _marin("comaeq", "ETAT_MAJOR", self.ship, fonction_coma="COMAEQ")
        self.comops = _marin("comops", "ETAT_MAJOR", self.ship, fonction_coma="COMOPS")
        self.commandant = _marin("cdt", "COMMANDANT", self.ship)
        self.cdt_autre = _marin("cdt_autre", "COMMANDANT", self.autre)
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
        UserProfile.objects.filter(user=self.comaeq).update(fonction_coma="")
        self.assertFalse(peut_viser_comaeq(self.comaeq, self.feuille))
        self.assertTrue(peut_viser_comaeq(self.commandant, self.feuille))
        self.feuille._notifier_prochain_visa()
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_comaeq_vacant").exists())
        notification = Notification.objects.get(user=self.commandant)
        self.assertIn("COMAEQ vacant", notification.verb)
        self.assertFalse(Notification.objects.filter(user=self.cdt_autre).exists())

    def test_commandant_en_second_ne_vise_jamais(self):
        # Le commandant en second a la vision du commandant en lecture seule : il ne vise pas,
        # même quand le poste de COMAEQ est vacant.
        UserProfile.objects.filter(user=self.comaeq).update(fonction_coma="")
        second = _marin("second", "COMMANDANT_EN_SECOND", self.ship)
        self.assertFalse(peut_viser_comaeq(second, self.feuille))
        self.assertTrue(peut_lire_feuille_service(second, self.feuille))

    def test_l_etat_major_non_titulaire_ne_lit_plus_via_le_visa(self):
        autre = _marin("autre_em", "ETAT_MAJOR", self.ship)
        self.assertFalse(peut_lire_feuille_service(autre, self.feuille))


class VisaComaeqDoubleEquipageTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(
            name="FREMM Visa", code="FV", classe_navire="FREMM", double_equipage=True, equipage_a_bord="A",
        )
        self.comaeq_bleu = _marin("comaeq_bleu", "ETAT_MAJOR", self.ship, "A", "COMAEQ")
        self.comaeq_rouge = _marin("comaeq_rouge", "ETAT_MAJOR", self.ship, "B", "COMAEQ")
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, equipage="A", date=timezone.localdate(), statut=FeuilleService.STATUT_VISA_COMAEQ,
        )

    def test_le_titulaire_est_celui_de_l_equipage_de_la_feuille(self):
        self.assertEqual(titulaire_comaeq(self.feuille), self.comaeq_bleu)
        self.assertTrue(peut_viser_comaeq(self.comaeq_bleu, self.feuille))
        self.assertFalse(peut_viser_comaeq(self.comaeq_rouge, self.feuille))

    def test_titulaire_passe_dans_l_autre_equipage_est_ignore(self):
        UserProfile.objects.filter(user=self.comaeq_bleu).update(equipage="B")
        self.comaeq_bleu = User.objects.get(pk=self.comaeq_bleu.pk)
        self.assertIsNone(titulaire_comaeq(self.feuille))
        self.assertFalse(peut_viser_comaeq(self.comaeq_bleu, self.feuille))

    def test_poste_vacant_d_un_equipage_n_escalade_pas_a_l_autre_equipage(self):
        UserProfile.objects.filter(user=self.comaeq_bleu).update(fonction_coma="")
        commandant_rouge = _marin("cdt_rouge", "COMMANDANT", self.ship, "B")
        commandant_bleu = _marin("cdt_bleu", "COMMANDANT", self.ship, "A")
        self.assertFalse(peut_viser_comaeq(commandant_rouge, self.feuille))
        self.assertTrue(peut_viser_comaeq(commandant_bleu, self.feuille))
        self.assertEqual(self.feuille.validateurs_a_notifier(), [commandant_bleu])
