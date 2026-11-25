"""Administrateur général : indicateur distinct du rôle métier (AC-15).

Un compte au rôle historique MASTER_ADMIN devient administrateur général (indicateur) avec le rôle métier minimal :
la migration n'attribue aucune fonction métier. Le sens inverse restaure le rôle historique tant que le rôle n'a pas été modifié.
"""
from django.db import migrations, models

ACTION = "l06_migration_administrateur_general"


def separer(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    AuditLog = apps.get_model("accounts", "AuditLog")
    for profil in UserProfile.objects.filter(role="MASTER_ADMIN"):
        profil.role, profil.administrateur_general = "EQUIPIER", True
        profil.save(update_fields=["role", "administrateur_general"])
        AuditLog.objects.create(actor=None, action=ACTION, target_user_id=profil.user_id,
                                details="avant=MASTER_ADMIN; apres=EQUIPIER+administrateur_general")


def restaurer(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    AuditLog = apps.get_model("accounts", "AuditLog")
    for journal in AuditLog.objects.filter(action=ACTION):
        UserProfile.objects.filter(user_id=journal.target_user_id, administrateur_general=True, role="EQUIPIER").update(
            role="MASTER_ADMIN", administrateur_general=False)
        journal.delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0027_echec_connexion")]
    operations = [
        migrations.AddField(model_name="userprofile", name="administrateur_general",
                            field=models.BooleanField(default=False, verbose_name="Administrateur général")),
        migrations.RunPython(separer, restaurer),
    ]
