"""Signale les rectificatifs à préparer (idempotent) : retente les signalements échoués ou manqués."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from quarts.models import FeuilleService
from quarts.rectificatif import signaler_sans_risque


class Command(BaseCommand):
    help = "Notifie les responsables des feuilles publiées dont les affectations effectives ont changé (une fois par divergence)."

    def handle(self, *args, **options):
        feuilles = FeuilleService.objects.filter(
            date__gte=timezone.localdate(), versions__isnull=False,
        ).distinct()
        for feuille in feuilles:
            signaler_sans_risque(feuille, "lors du passage de la commande")
        self.stdout.write(f"{feuilles.count()} feuille(s) examinée(s).")
