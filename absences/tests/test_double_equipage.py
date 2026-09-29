"""Double équipage, tranche 4 : les absences (déclaration, validation,
visibilité) ne franchissent jamais la frontière entre les deux équipages."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from absences.models import Absence
from absences.services import (
    absences_visibles,
    declarer_absence,
    marin_dans_perimetre,
    marins_de_mon_perimetre,
    peut_valider_absence,
)
from accounts.models import TypeAbsence, UserProfile
from org.models import Equipage, Ship

User = get_user_model()


def marin(nom, role, ship, equipage=None):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class AbsencesParEquipageTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="PSP Test", code="PT", classe_navire="PSP", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.ship, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.ship, nom="Rouge")
        self.ship.equipage_a_bord = self.bleu
        self.ship.save()
        self.chef_bleu = marin("chef_bleu", "COMMANDANT", self.ship, self.bleu)
        self.m_bleu = marin("m_bleu", "EQUIPIER", self.ship, self.bleu)
        self.m_rouge = marin("m_rouge", "EQUIPIER", self.ship, self.rouge)
        self.type_absence = TypeAbsence.objects.create(name="Permission")
        aujourd_hui = timezone.localdate()
        self.debut, self.fin = aujourd_hui, aujourd_hui + timedelta(days=2)

    def test_perimetre_du_chef_limite_a_son_equipage(self):
        self.assertTrue(marin_dans_perimetre(self.chef_bleu, self.m_bleu))
        self.assertFalse(marin_dans_perimetre(self.chef_bleu, self.m_rouge))
        self.assertEqual(set(marins_de_mon_perimetre(self.chef_bleu)), {self.m_bleu})

    def test_chef_ne_declare_pas_pour_l_autre_equipage(self):
        with self.assertRaises(PermissionError):
            declarer_absence(self.chef_bleu, self.m_rouge, self.type_absence, self.debut, self.fin)
        self.assertFalse(Absence.objects.exists())

    def test_absences_visibles_et_validation_sans_melange(self):
        absence_rouge = declarer_absence(self.m_rouge, self.m_rouge, self.type_absence, self.debut, self.fin)
        absence_bleu = declarer_absence(self.m_bleu, self.m_bleu, self.type_absence, self.debut, self.fin)
        self.assertEqual(set(absences_visibles(self.chef_bleu)), {absence_bleu})
        self.assertFalse(peut_valider_absence(self.chef_bleu, absence_rouge))
        self.assertTrue(peut_valider_absence(self.chef_bleu, absence_bleu))
