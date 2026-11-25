"""Récupération exceptionnelle d'un administrateur général (AC-17), en deux exécutions locales d'opérateurs distincts.

    manage.py recuperer_acces_administrateur ouvrir --identifiant ID --justification "..." [--attribuer]
    manage.py recuperer_acces_administrateur valider --demande N

Chaque exécution demande la phrase secrète personnelle de l'opérateur, qui doit être habilité (`habiliter_operateur_recuperation`)
et exécuter la commande avec sa propre identité système. La procédure simplifiée (`simplifie`) n'existe qu'en développement :
elle est refusée dès que l'application tourne en production (DJANGO_DEBUG absent ou nul).
"""
import getpass

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts import recuperation
from accounts.models import AuditLog, OperateurRecuperation


class Command(BaseCommand):
    help = "Récupération d'un administrateur général : ouverture puis validation par un second opérateur."

    def add_arguments(self, parser):
        sous = parser.add_subparsers(dest="etape", required=True)
        ouvrir = sous.add_parser("ouvrir")
        ouvrir.add_argument("--identifiant", required=True)
        ouvrir.add_argument("--justification", required=True)
        ouvrir.add_argument("--attribuer", action="store_true", help="Seulement si aucun administrateur général n'est disponible.")
        valider = sous.add_parser("valider")
        valider.add_argument("--demande", type=int, required=True)
        sous.add_parser("simplifie").add_argument("--identifiant", required=True)

    def _operateur(self):
        phrase = getpass.getpass("Phrase secrète de l'opérateur : ")
        try:
            return recuperation.authentifier_operateur(recuperation.identite_systeme(), phrase)
        except PermissionDenied:
            raise CommandError("Opérateur non reconnu.")

    def handle(self, *args, **options):
        try:
            if options["etape"] == "simplifie":
                self._simplifie(options["identifiant"])
            elif options["etape"] == "ouvrir":
                demande, code = recuperation.ouvrir(self._operateur(), options["identifiant"], options["justification"], options["attribuer"])
                self.stdout.write(f"Demande {demande.pk} ouverte, valable jusqu'à {demande.expire_le:%H:%M}. Premier code (affiché une seule fois) : {code}")
            else:
                demande, code = recuperation.valider(self._operateur(), options["demande"])
                self.stdout.write(f"Demande {demande.pk} validée. Second code (affiché une seule fois) : {code}")
        except PermissionDenied:
            raise CommandError("Opération refusée : un second opérateur distinct est exigé.")
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages))

    def _simplifie(self, identifiant):
        if not settings.DEBUG:
            raise CommandError("La procédure simplifiée est réservée au développement : refusée en production.")
        un = OperateurRecuperation.objects.create(nom="dev-1", identifiant_systeme="dev-1", phrase="!")
        deux = OperateurRecuperation.objects.create(nom="dev-2", identifiant_systeme="dev-2", phrase="!")
        try:
            demande, a = recuperation.ouvrir(un, identifiant, "développement", attribuer=not recuperation._administrateur_general_disponible())
            _, b = recuperation.valider(deux, demande.pk)
        finally:
            un.delete()
            deux.delete()
        AuditLog.objects.create(actor=None, action="recuperation_simplifiee_developpement", target_user=demande.user, details="développement uniquement")
        self.stdout.write(f"Codes de développement : {a} et {b}")
