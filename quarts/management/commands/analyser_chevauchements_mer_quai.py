from django.core.management.base import BaseCommand

from quarts.models import CreneauQuart, CreneauServiceGarde


def chevauchements():
    """Couples (marin, créneau à quai, créneau à la mer) publiés qui se recouvrent, ou deux créneaux à quai."""
    quai = list(CreneauServiceGarde.objects.filter(service_garde__statut="PUBLIEE", marin__isnull=False).select_related("service_garde", "marin"))
    mer = list(CreneauQuart.objects.filter(quart__statut="PUBLIEE", marin__isnull=False).select_related("quart", "marin"))
    lignes = [("quai", c) for c in quai] + [("mer", c) for c in mer]
    lignes.sort(key=lambda x: (x[1].marin_id, x[1].debut))
    trouves = []
    for i, (genre1, c1) in enumerate(lignes):
        for genre2, c2 in lignes[i + 1:]:
            if c2.marin_id != c1.marin_id or c2.debut >= c1.fin:
                break
            if "quai" in (genre1, genre2):
                trouves.append((c1.marin, genre1, c1, genre2, c2))
    return trouves


class Command(BaseCommand):
    help = "Diagnostic en lecture seule : chevauchements entre services à quai et quarts à la mer publiés. Ne modifie rien."

    def handle(self, *args, **options):
        trouves = chevauchements()
        for marin, g1, c1, g2, c2 in trouves:
            liste1 = c1.service_garde if g1 == "quai" else c1.quart
            liste2 = c2.service_garde if g2 == "quai" else c2.quart
            self.stdout.write(
                f"{marin.username} : {g1} « {liste1} » {c1.debut:%d/%m %H:%M}-{c1.fin:%d/%m %H:%M}"
                f" / {g2} « {liste2} » {c2.debut:%d/%m %H:%M}-{c2.fin:%d/%m %H:%M}"
            )
        self.stdout.write(f"{len(trouves)} chevauchement(s) ; aucune donnée modifiée.")
