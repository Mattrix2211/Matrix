"""Cartographie des points d'entrée de Matrix et de leurs protections déclarées (lecture seule)."""
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand

from matrix.core import points_entree
from matrix.core.registre_acces import REGLES, regle_de


class Command(BaseCommand):
    help = "Affiche en Markdown l'inventaire des routes, modèles d'administration et tâches, par règle du registre d'accès."

    def handle(self, *args, **options):
        points = points_entree.inventaire()
        routes = [p for p in points if p.nature in (points_entree.WEB, points_entree.API)]
        par_regle = defaultdict(list)
        for p in points:
            par_regle[regle_de(p).identifiant].append(p)
        ecrire = self.stdout.write
        ecrire("| Nature | Points d'entrée | Dont écriture possible |\n|---|---|---|")
        for nature, libelle in ((points_entree.WEB, "Pages web"), (points_entree.API, "API (hors suffixes de format)"),
                                (points_entree.ADMIN, "Administration (modèles)"), (points_entree.TACHE, "Tâches Celery")):
            choisis = [p for p in points if p.nature == nature and not p.variante_format]
            ecrire(f"| {libelle} | {len(choisis)} | {sum(1 for p in choisis if p.ecriture_possible)} |")
        ecrire(f"\nVariantes d'API à suffixe de format (même vue que la route de base) : {sum(1 for p in routes if p.variante_format)}. "
               f"Routes d'administration générées : {points_entree.nombre_routes_admin()}.\n")
        ecrire("| Règle | Classe | Points | Contrôles attendus | Module | Lecture sensible | Écarts connus | Suites existantes |\n|---|---|---|---|---|---|---|---|")
        for regle in REGLES:
            nombre = len([p for p in par_regle[regle.identifiant] if not p.variante_format])
            ecrire(f"| {regle.identifiant} | {regle.classe} | {nombre} | {', '.join(regle.controles) or '—'} | {regle.module or '—'} | "
                   f"{'oui' if regle.lecture_sensible else 'non'} | {' ; '.join(regle.ecarts) or '—'} | "
                   f"{', '.join(regle.couverture) or '—'} |")
        ecrire("\n| Tâche | Planifiée | Règle |\n|---|---|---|")
        for p in (p for p in points if p.nature == points_entree.TACHE):
            ecrire(f"| {p.cle} | {'oui' if p.planifiee else 'non'} | {regle_de(p).identifiant} |")
        declarations = Counter(d.split(":")[0] for p in routes for d in p.declare)
        ecrire(f"\nProtections lisibles dans le code des routes : {dict(declarations)}.")
