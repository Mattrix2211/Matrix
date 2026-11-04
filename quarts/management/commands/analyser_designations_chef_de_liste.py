from django.core.management.base import BaseCommand

from quarts.designations import LIBELLES, designations_historiques, situation


class Command(BaseCommand):
    help = "Diagnostic en lecture seule : désignations de chef de liste historiques (sans type) à faire préciser. Ne modifie rien."

    def handle(self, *args, **options):
        lignes = 0
        for cdl in designations_historiques():
            lignes += 1
            self.stdout.write(f"{cdl.user.username} — {cdl.perimetre} : {LIBELLES[situation(cdl)]}")
        self.stdout.write(f"{lignes} désignation(s) historique(s) à préciser ; aucun droit modifié.")
