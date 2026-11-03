"""Écran d'exécution : EPI, consignes, risques et points critiques de la fiche restent visibles (mêmes données que l'impression)."""
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from maintenance.models import MaintenanceOccurrence
from maintenance.tests.test_fiche_imprimable import _navire
from maintenance.web_views import securite_fiche


def _tous(*objets):
    return SimpleNamespace(all=lambda: list(objets))


def _version_fictive():
    return SimpleNamespace(
        fiche_id=1, numero=1, name="Fiche fictive", etapes=_tous(
            SimpleNamespace(texte="Isoler la ligne", attention="Surfaces chaudes : contrôler avant de toucher."),
            SimpleNamespace(texte="Remplacer le joint", attention="")),
        preparations=_tous(
            SimpleNamespace(type="epi", libelle="Gants de manutention", quantite=1),
            SimpleNamespace(type="consigne", libelle="Machine à l'arrêt, consignée (exemple fictif)", quantite=1),
            SimpleNamespace(type="outil", libelle="Clé dynamométrique", quantite=1)),
        duree_estimee_minutes=None, items=SimpleNamespace(order_by=lambda *a: []))


class SecuriteExecutionTests(TestCase):
    def setUp(self):
        sector, self.occ = _navire("S")
        user = User.objects.create_user(username="chef_secu", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "CHEF_SERVICE", "sector": sector})
        self.client.login(username="chef_secu", password="pass")

    def test_securite_fiche_reprend_les_donnees_de_la_fiche(self):
        items = [SimpleNamespace(label="Machine arrêtée", required=True), SimpleNamespace(label="Relevé facultatif", required=False)]
        s = securite_fiche(_version_fictive(), items)
        self.assertEqual(s["epi"], ["Gants de manutention"])
        self.assertEqual(s["consignes"], ["Machine à l'arrêt, consignée (exemple fictif)"])
        self.assertEqual([a["numero"] for a in s["attentions"]], [1])
        self.assertEqual(s["critiques"], ["Machine arrêtée"])
        self.assertTrue(s["renseignee"])

    def test_l_ecran_d_execution_affiche_la_securite_de_la_fiche(self):
        with mock.patch.object(MaintenanceOccurrence, "version_fiche", return_value=_version_fictive()):
            page = self.client.get(reverse("occurrence-execute", args=[self.occ.pk]))
        self.assertEqual(page.status_code, 200)
        for texte in ("Sécurité de l'intervention", "EPI nécessaires", "Gants de manutention", "Consignes et précautions avant intervention",
                      "Machine à l&#x27;arrêt, consignée", "Risques particuliers", "Surfaces chaudes"):
            self.assertContains(page, texte)

    def test_une_fiche_sans_consigne_le_dit_explicitement(self):
        page = self.client.get(reverse("occurrence-execute", args=[self.occ.pk]))
        self.assertContains(page, "Aucune consigne de sécurité n'est renseignée")
