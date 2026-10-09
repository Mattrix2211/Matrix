from django.db import migrations


def figer_versions(apps, schema_editor):
    """Les exécutions d'installation déjà saisies gardent la version validée à leur date,
    pour que leur historique ne suive pas les versions futures. Rejouable."""
    Execution = apps.get_model("maintenance", "MaintenanceExecution")
    Version = apps.get_model("assets", "ChecklistTemplate")
    candidates = Execution.objects.filter(
        version_fiche__isnull=True, occurrence__installation_maintenance__isnull=False,
    ).select_related("occurrence")
    for execution in candidates:
        versions = Version.objects.filter(
            fiche_id=execution.occurrence.installation_maintenance_id, etat="validee").order_by("-valide_le", "-numero")
        version = versions.filter(valide_le__lte=execution.created_at).first() or versions.order_by("numero").first()
        if version:
            Execution.objects.filter(pk=execution.pk).update(version_fiche=version)


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0005_execution_version_fiche"),
        ("assets", "0036_fiches_version_1"),
    ]

    operations = [migrations.RunPython(figer_versions, migrations.RunPython.noop)]
