"""Couverture : chaque point d'entrée est inventorié et rattaché à une règle du registre (lot L29)."""
import importlib
import re
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.test import TestCase
from django.urls import resolve

from matrix.core import points_entree
from matrix.core.modules import REGISTRE_PAR_CLE
from matrix.core.registre_acces import REGLES, VOCABULAIRE, regle_de

from .outils import points_non_couverts

PLAN = (Path(settings.BASE_DIR) / "docs" / "PLAN_LOTS_REPRISE.md").read_text(encoding="utf-8")


class InventaireTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.points = points_entree.inventaire()

    def test_l_inventaire_n_est_pas_vide(self):
        natures = {nature: [p for p in self.points if p.nature == nature] for nature in (points_entree.WEB, points_entree.API, points_entree.ADMIN, points_entree.TACHE)}
        self.assertGreater(len(natures["web"]), 100)
        self.assertGreater(len(natures["api"]), 100)
        self.assertEqual(len(natures["admin"]), len(admin.site._registry))
        self.assertGreater(len(natures["tache"]), 15)
        self.assertGreater(points_entree.nombre_routes_admin(), 0)

    def test_tout_point_d_entree_est_couvert_par_une_regle(self):
        self.assertEqual(points_non_couverts(self.points), [])

    def test_toute_regle_correspond_a_un_point_d_entree(self):
        utilisees = {regle_de(p).identifiant for p in self.points}
        self.assertEqual([r.identifiant for r in REGLES if r.identifiant not in utilisees], [])

    def test_les_controles_cites_existent(self):
        for regle in REGLES:
            self.assertLessEqual(set(regle.controles), VOCABULAIRE, regle.identifiant)

    def test_les_suites_de_couverture_citees_existent(self):
        for regle in REGLES:
            for module in regle.couverture:
                importlib.import_module(module)

    def test_chaque_ecart_nomme_un_lot_du_plan(self):
        for regle in REGLES:
            for ecart in regle.ecarts:
                lots = re.findall(r"\bL\d+\b", ecart)
                self.assertTrue(lots, f"{regle.identifiant} : {ecart}")
                for lot in lots:
                    self.assertIn(f"**{lot}**", PLAN, f"{regle.identifiant} : lot {lot} absent du plan")

    def test_les_taches_planifiees_sont_inventoriees(self):
        inventoriees = {p.cle for p in self.points if p.nature == points_entree.TACHE}
        planifiees = {e["task"] for e in settings.CELERY_BEAT_SCHEDULE.values()}
        self.assertLessEqual(planifiees, inventoriees)

    def test_les_variantes_de_format_ont_une_route_de_base(self):
        routes = [p for p in self.points if p.nature in (points_entree.WEB, points_entree.API)]
        bases = {(p.vue, p.methodes) for p in routes if not p.variante_format}
        for p in routes:
            if p.variante_format:
                self.assertIn((p.vue, p.methodes), bases, p.cle)

    def test_les_modules_cites_existent(self):
        for regle in REGLES:
            if regle.module:
                self.assertIn(regle.module, REGISTRE_PAR_CLE, regle.identifiant)

    def test_chaque_adresse_d_essai_atteint_la_vue_inventoriee(self):
        """Une adresse d'essai mal construite se verrait comme un faux « refus » ; on vérifie qu'elle résout bien la vue annoncée."""
        for p in self.points:
            if p.nature in (points_entree.WEB, points_entree.API) and p.url_exemple:
                callback = resolve(p.url_exemple).func
                cls = getattr(callback, "view_class", None) or getattr(callback, "cls", None) or callback
                self.assertEqual(f"{cls.__module__}.{cls.__name__}", p.vue, p.url_exemple)

    def test_les_routes_d_api_declarent_une_classe_de_permission(self):
        for p in self.points:
            if p.nature == points_entree.API and not p.variante_format and p.methodes:
                self.assertTrue(any(d.startswith("permission:") for d in p.declare), p.cle)
