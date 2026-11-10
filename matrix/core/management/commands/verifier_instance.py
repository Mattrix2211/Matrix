"""Contrôle en lecture seule avant toute mise en production : marqueur de démonstration et mots de passe prévisibles."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from matrix.core import instance_demo


class Command(BaseCommand):
    help = "Signale (sans rien modifier) une base de démonstration ou des comptes à mot de passe prévisible."

    def handle(self, *args, **options):
        problemes = []
        marquee = instance_demo.base_marquee()
        self.stdout.write(f"Base marquée comme démonstration : {'oui' if marquee else 'non'} ; mode DEBUG : {'oui' if settings.DEBUG else 'non'}.")
        if marquee and not settings.DEBUG:
            problemes.append("la base est marquée « démonstration » mais le mode DEBUG est inactif (usage en production)")
        faibles = instance_demo.comptes_a_mot_de_passe_herite()
        if faibles:
            problemes.append(f"{len(faibles)} compte(s) actif(s) au mot de passe prévisible : {', '.join(faibles[:8])}{'…' if len(faibles) > 8 else ''}")
        if problemes:
            raise CommandError("Instance non conforme : " + " ; ".join(problemes) + ".")
        self.stdout.write(self.style.SUCCESS("Aucun compte à mot de passe prévisible, aucun marqueur de démonstration en production."))
