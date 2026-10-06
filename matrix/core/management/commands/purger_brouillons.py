from django.core.management.base import BaseCommand

from matrix.core.brouillons import purger_brouillons_anciens


class Command(BaseCommand):
    help = "Supprime les brouillons non modifiés depuis la durée de conservation (BROUILLONS_CONSERVATION_JOURS)."

    def handle(self, *args, **options):
        nombre = purger_brouillons_anciens()
        self.stdout.write(f"{nombre} brouillon(s) supprimé(s).")
