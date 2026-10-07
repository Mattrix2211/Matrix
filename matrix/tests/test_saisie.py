from django.test import SimpleTestCase

from matrix.core.saisie import entier_ou_none


class EntierOuNoneTests(SimpleTestCase):
    def test_valeurs_valides(self):
        self.assertEqual(entier_ou_none("12"), 12)
        self.assertEqual(entier_ou_none(" 7 "), 7)

    def test_valeurs_refusees(self):
        for valeur in ("abc", "", None, "-3", "1.5", "²", "٣", "9" * 40):
            self.assertIsNone(entier_ou_none(valeur), valeur)
