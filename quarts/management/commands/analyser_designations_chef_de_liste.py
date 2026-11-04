from collections import Counter

from django.core.management.base import BaseCommand

from quarts.designations import LIBELLES, designations_historiques, situation


class Command(BaseCommand):
    help = (
        "Inventaire en lecture seule des désignations de chef de liste historiques (sans type), qui gardent leurs effets sur les "
        "quarts à la mer ET les services à quai. Aucun droit n'est modifié : la qualification se fait explicitement dans « Chefs de liste »."
    )

    def handle(self, *args, **options):
        comptes = Counter()
        for cdl in designations_historiques().order_by("user__username"):
            classe = situation(cdl)
            comptes[classe] += 1
            self.stdout.write(
                f"{cdl.user.username} — {cdl.perimetre} : droits actuels sur les quarts à la mer ET les services à quai ; {LIBELLES[classe]}"
            )
        total = sum(comptes.values())
        self.stdout.write(
            f"{total} désignation(s) historique(s) à qualifier"
            + (" (" + ", ".join(f"{n} {LIBELLES[c].lower()}" for c, n in sorted(comptes.items())) + ")" if total else "")
            + " ; aucun droit modifié."
        )
