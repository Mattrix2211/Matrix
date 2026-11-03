from datetime import datetime, time

from django.db import migrations
from django.utils import timezone


def reprendre_listes_publiees(apps, schema_editor):
    """Reprise conservatrice : rien n'est supprimé ni réécrit. Une liste déjà
    publiée garde son effet sur sa période ; seule sa situation est qualifiée
    (échue → terminée, sinon active sur sa période)."""
    ServiceGarde = apps.get_model("quarts", "ServiceGarde")
    aujourdhui = timezone.localdate()
    for liste in ServiceGarde.objects.filter(statut="PUBLIEE"):
        liste.activation_historique = True
        liste.prise_effet = timezone.make_aware(datetime.combine(liste.date_debut, time.min))
        liste.application = "TERMINEE" if liste.date_fin < aujourdhui else "ACTIVE"
        liste.save(update_fields=["activation_historique", "prise_effet", "application"])


class Migration(migrations.Migration):

    dependencies = [("quarts", "0013_application_liste_quai")]

    operations = [migrations.RunPython(reprendre_listes_publiees, migrations.RunPython.noop)]
