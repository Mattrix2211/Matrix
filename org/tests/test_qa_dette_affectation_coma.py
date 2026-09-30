"""Règle du 30/09/2026 : la page « Équipages » refuse de rattacher à un autre
équipage un marin titulaire d'un poste COMA (le poste doit être libéré d'abord)."""
from django.core.cache import cache

from org.models import CommandantAdjoint
from org.tests.test_coherence_equipage import BaseDoubleEquipage, creer_marin


class AffectationTitulaireComaTests(BaseDoubleEquipage):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.cdt = creer_marin("cdt_qa", "COMMANDANT", self.ship, self.bleu)
        self.client.force_login(self.cdt)
        self.titulaire = creer_marin("coma_bleu", "ETAT_MAJOR", self.ship, self.bleu)
        self.poste = CommandantAdjoint.objects.create(
            ship=self.ship, equipage=self.bleu, sigle="COMAEQ", titulaire=self.titulaire)

    def test_rattacher_un_titulaire_coma_a_l_autre_equipage_est_refuse(self):
        self.client.post("/equipages/", {
            "action": "affecter_equipage_marin", "user_id": self.titulaire.pk, "equipage_id": self.rouge.pk,
        })
        self.titulaire.profile.refresh_from_db()
        self.assertEqual(self.titulaire.profile.equipage, self.bleu)
