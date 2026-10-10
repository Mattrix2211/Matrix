import uuid

from django.db import migrations, models


def creer_versions_initiales(apps, schema_editor):
    """Chaque fiche existante devient la version 1 validée d'elle-même, sans rien perdre ;
    les lignes de checklist déjà saisies gardent leur identité."""
    for item in apps.get_model("assets", "ChecklistItemTemplate").objects.filter(cle__isnull=True):
        item.cle = uuid.uuid4()
        item.save(update_fields=["cle"])
    Fiche = apps.get_model("assets", "InstallationMaintenance")
    Version = apps.get_model("assets", "ChecklistTemplate")
    for fiche in Fiche.objects.filter(installation__isnull=False, versions__isnull=True).select_related("installation"):
        Version.objects.create(
            fiche=fiche, numero=1, etat="validee", name=fiche.title, sector_id=fiche.installation.sector_id,
            description=fiche.description, mode_declenchement=fiche.mode_declenchement,
            intervalle=fiche.intervalle, unite_intervalle=fiche.unite_intervalle, seuil_heures=fiche.seuil_heures,
            duree_estimee_min=fiche.planned_duration_min, nb_personnes=fiche.people_count,
            redacteur_id=fiche.created_by_id, valide_le=fiche.updated_at,
        )


class Migration(migrations.Migration):

    dependencies = [("assets", "0035_fiches_maintenance_versions")]

    operations = [
        migrations.RunPython(creer_versions_initiales, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="checklistitemtemplate",
            name="cle",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
    ]
