from django.db import migrations


def normaliser_niveau(apps, schema_editor):
    """Le niveau suit la cible : une fiche de catégorie est une fiche flotte, une fiche d'installation une fiche du bord."""
    Fiche = apps.get_model("assets", "InstallationMaintenance")
    Fiche.objects.filter(categorie__isnull=False).exclude(niveau="FLOTTE").update(niveau="FLOTTE")
    Fiche.objects.filter(installation__isnull=False).exclude(niveau="BORD").update(niveau="BORD")


class Migration(migrations.Migration):

    dependencies = [("assets", "0037_fiches_flotte")]

    operations = [migrations.RunPython(normaliser_niveau, migrations.RunPython.noop)]
