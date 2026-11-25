"""Installation : habilite un opérateur à la récupération d'un administrateur général (AC-17).

Deux opérateurs au plus par cette voie ; chacun choisit sa propre phrase secrète (saisie masquée, jamais en argument) et
s'authentifie ensuite avec l'identité système de son propre compte d'exploitation.
"""
import getpass

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.recuperation import habiliter_operateur, identite_systeme


class Command(BaseCommand):
    help = "Habilite l'opérateur qui exécute la commande (identité système) à la procédure de récupération."

    def add_arguments(self, parser):
        parser.add_argument("--nom", required=True, help="Nom de l'opérateur, tel qu'il figurera dans le journal d'audit.")

    def handle(self, *args, **options):
        phrase = getpass.getpass("Phrase secrète personnelle (12 caractères au moins) : ")
        if phrase != getpass.getpass("Confirmez la phrase secrète : "):
            raise CommandError("Les deux saisies diffèrent.")
        try:
            habiliter_operateur(options["nom"], identite_systeme(), phrase)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages))
        self.stdout.write(self.style.SUCCESS(f"Opérateur {options['nom']} habilité ({identite_systeme()})."))
