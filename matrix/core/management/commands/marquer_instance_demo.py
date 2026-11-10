"""Marque en base une base préparée comme instance de démonstration.

La preuve de préparation est l'identifiant écrit par scripts/preparer_instance_test.py dans le fichier voisin : cette commande
l'exige non vide et ne la fabrique jamais, sauf adoption explicite d'une base préparée avant le verrou (--adopter-ancienne-base).
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from matrix.core import instance_demo


class Command(BaseCommand):
    help = "Marque la base courante comme base de démonstration si elle a été préparée comme telle et ne contient que des comptes fictifs."

    def add_arguments(self, parser):
        parser.add_argument("--regenerer-mots-de-passe", action="store_true",
                            help="Remplace les anciens mots de passe prévisibles des comptes de démonstration.")
        parser.add_argument("--adopter-ancienne-base", action="store_true",
                            help="Base préparée avant le verrou (fichier voisin vide) : exige que chaque compte soit un compte de "
                                 "démonstration encore protégé par un ancien mot de passe prévisible, puis écrit l'identifiant d'instance.")

    def handle(self, *args, **options):
        adopter = options["adopter_ancienne_base"]
        manque = instance_demo.conditions_manquantes(exiger_preuve=not adopter)
        if adopter and not manque:
            fichier = instance_demo.fichier_marqueur()
            if fichier is None or not fichier.is_file():
                manque.append("le fichier voisin de la base est absent")
            elif instance_demo.identifiant_instance():
                manque.append("la base porte déjà un identifiant d'instance (l'adoption ne concerne que les bases préparées avant le verrou)")
        if manque:
            raise CommandError("Refus : " + " ; ".join(manque) + ".")
        etrangers = instance_demo.comptes_etrangers()
        if etrangers:
            raise CommandError(f"Refus : la base contient {len(etrangers)} compte(s) non fictif(s) ({', '.join(etrangers[:5])}…). "
                               "Aucune modification n'a été faite.")
        if adopter:
            refuses = instance_demo.adopter_ancienne_base()
            if refuses:
                raise CommandError(f"Refus d'adopter cette base : compte(s) sans ancien mot de passe prévisible ou absents ({', '.join(refuses[:5])}). "
                                   "Aucune modification n'a été faite. Utiliser --reinitialiser pour recréer une base de démonstration.")
        with transaction.atomic():
            instance_demo.marquer_base("marquer_instance_demo")
            if options["regenerer_mots_de_passe"]:
                modifies = instance_demo.regenerer_mots_de_passe_herites()
                self.stdout.write(f"Mots de passe prévisibles remplacés : {len(modifies)} compte(s). "
                                  f"Mots de passe {instance_demo.description_mots_de_passe()}.")
        self.stdout.write(self.style.SUCCESS(f"Base marquée comme base de démonstration ({get_user_model().objects.count()} compte(s))."))
