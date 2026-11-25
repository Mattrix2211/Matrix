"""Récupération exceptionnelle de l'accès d'un administrateur général (AC-12, AC-09).

Procédure locale, sur le serveur, par un exploitant autorisé : elle émet un mot de passe provisoire à usage unique, affiché
une seule fois sur la console de l'exploitant, valide pour une durée limitée, que le titulaire remplace à sa première connexion.
Elle ne s'applique qu'à un compte d'administrateur général et efface le verrouillage de connexion de ce compte.
"""
import getpass
import socket
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.authentification import _cle
from accounts.models import AuditLog, UserProfile
from accounts.services import PROTECTION_RECUPERATION, generer_mot_de_passe, niveau_de_protection


class Command(BaseCommand):
    help = "Émet un mot de passe provisoire pour un compte d'administrateur général (procédure exceptionnelle, locale)."

    def add_arguments(self, parser):
        parser.add_argument("--identifiant", required=True)
        parser.add_argument("--autorisation", required=True, help="Référence de l'autorisation préalable de récupération.")

    def handle(self, *args, **options):
        try:
            compte = get_user_model().objects.get(username=options["identifiant"], is_active=True)
        except get_user_model().DoesNotExist:
            raise CommandError("Compte introuvable ou inactif.")
        if niveau_de_protection(compte) != PROTECTION_RECUPERATION:
            raise CommandError("Cette procédure ne concerne que les comptes d'administrateur général.")
        operateur = f"{getpass.getuser()}@{socket.gethostname()}"
        mot_de_passe = generer_mot_de_passe()
        compte.set_password(mot_de_passe)
        compte.save(update_fields=["password"])
        profil, _ = UserProfile.objects.get_or_create(user=compte)
        profil.mot_de_passe_provisoire = True
        profil.mot_de_passe_provisoire_expire_le = timezone.now() + timedelta(hours=settings.DUREE_MOT_DE_PASSE_PROVISOIRE_HEURES)
        profil.save(update_fields=["mot_de_passe_provisoire", "mot_de_passe_provisoire_expire_le"])
        cache.delete(_cle(compte.username))
        AuditLog.objects.create(
            actor=None, action="recuperation_acces", target_user=compte,
            details=f"operateur={operateur}; autorisation={options['autorisation']}; valide jusqu'au {profil.mot_de_passe_provisoire_expire_le:%d/%m/%Y %H:%M}",
        )
        self.stdout.write(f"Mot de passe provisoire (affiché une seule fois) : {mot_de_passe}")
