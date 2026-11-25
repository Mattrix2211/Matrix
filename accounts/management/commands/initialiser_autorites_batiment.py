"""Initialisation des premières autorités d'un bâtiment (AC-09).

Exécutée localement sur le serveur par un installateur autorisé, une seule fois par bâtiment : elle désigne le premier
commandant et, indépendamment, le premier administrateur technique. Aucun mot de passe ni identifiant n'est créé ou
imposé : les comptes existent déjà. Elle ne remplace aucune autorité en place et se verrouille après usage.
"""
import getpass
import socket

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from accounts.models import AuditLog, InitialisationBatiment, Roles, UserProfile
from org.models import Ship


class Command(BaseCommand):
    help = "Désigne le premier commandant (et, séparément, le premier administrateur technique) d'un bâtiment, une seule fois."

    def add_arguments(self, parser):
        parser.add_argument("--batiment", required=True, help="Code du bâtiment.")
        parser.add_argument("--commandant", required=True, help="Identifiant du compte à désigner commandant.")
        parser.add_argument("--administrateur-technique", dest="technique", default="", help="Identifiant du premier administrateur technique.")
        parser.add_argument("--autorisation", required=True, help="Référence de l'autorisation préalable de désignation.")
        parser.add_argument("--accepter-cumul", action="store_true", help="Autorise explicitement le même compte pour les deux fonctions.")

    def handle(self, *args, **options):
        User = get_user_model()
        operateur = f"{getpass.getuser()}@{socket.gethostname()}"
        try:
            navire = Ship.objects.get(code=options["batiment"])
            commandant = User.objects.get(username=options["commandant"], is_active=True)
            technique = User.objects.get(username=options["technique"], is_active=True) if options["technique"] else None
        except (Ship.DoesNotExist, User.DoesNotExist):
            raise CommandError("Bâtiment ou compte introuvable (ou inactif).")
        if not options["autorisation"].strip():
            raise CommandError("La référence d'autorisation est obligatoire.")
        if technique is not None and technique.pk == commandant.pk and not options["accepter_cumul"]:
            raise CommandError("Le même compte ne peut cumuler les deux fonctions que par --accepter-cumul.")
        try:
            with transaction.atomic():
                Ship.objects.select_for_update().get(pk=navire.pk)
                if UserProfile.objects.filter(ship=navire, role=Roles.COMMANDANT, user__is_active=True).exists():
                    raise CommandError("Ce bâtiment a déjà un commandant : l'initialisation n'est plus possible.")
                InitialisationBatiment.objects.create(
                    ship=navire, operateur=operateur, autorisation=options["autorisation"], commandant=commandant,
                    administrateur_technique=technique)
                self._designer(navire, commandant, technique, options["accepter_cumul"])
                AuditLog.objects.create(
                    actor=None, action="initialisation_batiment", target_user=commandant,
                    details=f"batiment={navire.code}; operateur={operateur}; autorisation={options['autorisation']}; "
                            f"commandant={commandant.username}; technique={technique.username if technique else '—'}",
                )
        except IntegrityError:
            raise CommandError("Ce bâtiment a déjà été initialisé : la procédure est verrouillée.")
        self.stdout.write(self.style.SUCCESS(f"Bâtiment {navire.code} initialisé : commandant {commandant.username}."))

    def _designer(self, navire, commandant, technique, cumul):
        profil_cdt, _ = UserProfile.objects.get_or_create(user=commandant)
        if profil_cdt.role == Roles.MASTER_ADMIN or commandant.is_superuser:
            raise CommandError("Un administrateur général ne peut pas être désigné commandant par cette procédure.")
        if profil_cdt.administrateur_technique and (technique is None or technique.pk != commandant.pk) and not cumul:
            raise CommandError("Ce compte porte déjà les droits techniques : le cumul doit être explicite (--accepter-cumul).")
        if profil_cdt.ship_id not in (None, navire.pk):
            raise CommandError("Le compte appartient à un autre bâtiment.")
        profil_cdt.role, profil_cdt.ship = Roles.COMMANDANT, navire
        profil_cdt.save()
        if technique is not None:
            profil_tech, _ = UserProfile.objects.get_or_create(user=technique)
            if technique.pk != commandant.pk:
                if profil_tech.role not in (Roles.EQUIPIER, "") or profil_tech.fonction_coma:
                    raise CommandError("Le premier administrateur technique ne doit porter aucune autorité métier (sauf cumul explicite).")
                if profil_tech.ship_id not in (None, navire.pk):
                    raise CommandError("Le compte technique appartient à un autre bâtiment.")
                profil_tech.ship = navire
            profil_tech.administrateur_technique = True
            profil_tech.save()
