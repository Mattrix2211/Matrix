"""Signale les rectificatifs à préparer (idempotent) : retente les signalements échoués ou manqués."""
from django.core.management.base import BaseCommand

from quarts.rectificatif import signaler_divergences_a_venir


class Command(BaseCommand):
    help = "Notifie les responsables des feuilles publiées dont les affectations effectives ont changé (une fois par divergence)."

    def handle(self, *args, **options):
        examinees = signaler_divergences_a_venir("lors du passage de la commande")
        self.stdout.write(f"{examinees} feuille(s) examinée(s).")
