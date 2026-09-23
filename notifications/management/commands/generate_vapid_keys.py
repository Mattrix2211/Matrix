from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid02 as Vapid
from py_vapid.utils import b64urlencode


class Command(BaseCommand):
    help = (
        "Génère une paire de clés VAPID pour les notifications Web Push. "
        "À exécuter UNE SEULE FOIS : copiez le résultat dans les variables "
        "d'environnement VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY (jamais de "
        "génération à la volée à chaque démarrage, sinon les abonnements "
        "existants deviennent invalides)."
    )

    def handle(self, *args, **options):
        vapid = Vapid()
        vapid.generate_keys()

        cle_privee = b64urlencode(
            vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
        )
        cle_publique = b64urlencode(
            vapid.public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint,
            )
        )

        self.stdout.write(self.style.SUCCESS("Paire de clés VAPID générée."))
        self.stdout.write("")
        self.stdout.write("Ajoutez ces lignes à votre fichier d'environnement (.env / variables système) :")
        self.stdout.write(f"VAPID_PUBLIC_KEY={cle_publique}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={cle_privee}")
        self.stdout.write("VAPID_ADMIN_EMAIL=contact@votre-domaine.fr")
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Ne régénérez jamais ces clés une fois des abonnements créés : "
                "tous les appareils déjà abonnés deviendraient invalides."
            )
        )
