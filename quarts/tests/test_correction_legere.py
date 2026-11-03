"""Correction d'en-tête par le COMAEQ : une forte similarité textuelle ne prouve pas qu'une correction est mineure."""
from django.test import SimpleTestCase

from quarts.correction_legere import correction_legere


class CorrectionLegereTests(SimpleTestCase):
    def test_corrections_legeres(self):
        for avant, apres in (
            ("Journée à quai, consignes habituelles", "Journée à quai, consignes habituelles."),
            ("journée à quai", "Journée à Quai"),
            ("Appareillage prévu à 14h00", "Appareillage prévu à 14h00 "),
            ("Apparaillage prévu demain", "Appareillage prévu demain"),
            ("Exercice incendie génerale", "Exercice incendie générale"),
        ):
            self.assertEqual(correction_legere(avant, apres), (True, ""), (avant, apres))

    def test_une_forte_similarite_ne_suffit_pas_si_le_sens_change(self):
        for avant, apres in (
            ("Appareillage prévu à 14h00", "Appareillage prévu à 04h00"),      # heure : un seul caractère
            ("Appareillage non prévu aujourd'hui", "Appareillage prévu aujourd'hui"),   # négation retirée
            ("Sortie interdite sans autorisation", "Sortie interdite avec autorisation"),
            ("Accès au quai autorisé", "Accès au quai interdit"),
            ("Contrôle des cartouches de nuit", "Contrôle des cartouches de jour"),
            ("Permission le 12/11", "Permission le 13/11"),
            ("Exercice à la mer", "Exercice à la ter"),                        # mot sensible
            ("Appareillage prévu demain", "Accostage prévu demain"),
        ):
            legere, raison = correction_legere(avant, apres)
            self.assertFalse(legere, (avant, apres))
            self.assertTrue(raison)

    def test_ajout_ou_retrait_d_information_impose_une_nouvelle_validation(self):
        self.assertFalse(correction_legere("Journée à quai", "Journée à quai, appareillage 14h")[0])
        self.assertFalse(correction_legere("Journée à quai, appareillage 14h", "Journée à quai")[0])
        self.assertFalse(correction_legere("", "Journée à quai")[0])
        self.assertTrue(correction_legere("", "")[0])

    def test_trop_de_coquilles_cumulees(self):
        self.assertFalse(correction_legere("alpha bravo charlie delta", "alphu bravi charlia deltu")[0])
