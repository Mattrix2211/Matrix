"""Dédie la base courante à la démonstration (marqueur en base + fichier voisin) si elle ne contient que des comptes fictifs."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from matrix.core import instance_demo


class Command(BaseCommand):
    help = "Marque la base courante comme base de démonstration ; refuse si elle contient un compte non fictif."

    def add_arguments(self, parser):
        parser.add_argument("--regenerer-mots-de-passe", action="store_true",
                            help="Remplace les anciens mots de passe prévisibles des comptes de démonstration.")

    def handle(self, *args, **options):
        manque = instance_demo.conditions_manquantes(exiger_fichier=False)
        if manque:
            raise CommandError("Refus : " + " ; ".join(manque) + ".")
        etrangers = instance_demo.comptes_etrangers()
        if etrangers:
            raise CommandError(f"Refus : la base contient {len(etrangers)} compte(s) non fictif(s) ({', '.join(etrangers[:5])}…). "
                               "Aucune modification n'a été faite.")
        with transaction.atomic():
            instance_demo.marquer_base("marquer_instance_demo")
            if options["regenerer_mots_de_passe"]:
                modifies = instance_demo.regenerer_mots_de_passe_herites()
                self.stdout.write(f"Mots de passe prévisibles remplacés : {len(modifies)} compte(s). "
                                  f"Mots de passe {instance_demo.description_mots_de_passe()}.")
        fichier = instance_demo.fichier_marqueur()
        if fichier is not None:
            fichier.touch()
        self.stdout.write(self.style.SUCCESS(f"Base marquée comme base de démonstration ({get_user_model().objects.count()} compte(s))."))
