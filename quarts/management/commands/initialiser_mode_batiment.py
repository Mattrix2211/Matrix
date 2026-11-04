from datetime import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from org.models import Ship
from quarts.mouvements import MouvementImpossible, initialiser_mode, mode_du_batiment


class Command(BaseCommand):
    help = "Initialise explicitement le mode (MER ou QUAI) d'un bâtiment dont la situation n'est pas renseignée. Tracé, jamais déduit d'une liste."

    def add_arguments(self, parser):
        parser.add_argument("--batiment", required=True, help="Nom ou code du bâtiment.")
        parser.add_argument("--mode", required=True, choices=["MER", "QUAI"])
        parser.add_argument("--par", required=True, help="Identifiant du COMAEQ ou du commandant qui déclare.")
        parser.add_argument("--motif", required=True)
        parser.add_argument("--depuis", help="Date et heure effectives (AAAA-MM-JJTHH:MM) ; maintenant par défaut.")

    def handle(self, *args, **options):
        ship = Ship.objects.filter(Q(name=options["batiment"]) | Q(code=options["batiment"])).first()
        auteur = User.objects.filter(username=options["par"]).first()
        if ship is None or auteur is None:
            raise CommandError("Bâtiment ou auteur introuvable.")
        if mode_du_batiment(ship) is not None:
            raise CommandError("Le mode de ce bâtiment est déjà renseigné ; déclarez un accostage ou un appareillage.")
        instant = timezone.make_aware(datetime.fromisoformat(options["depuis"])) if options["depuis"] else timezone.now()
        try:
            initialiser_mode(auteur, ship, options["mode"], instant, options["motif"])
        except MouvementImpossible as exc:
            raise CommandError(str(exc))
        self.stdout.write(f"{ship} : mode {options['mode']} initialisé par {auteur.username}.")
