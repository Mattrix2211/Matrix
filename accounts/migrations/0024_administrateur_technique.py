"""Sépare l'administration technique du rôle métier (lot L06, AC-01).

Un ancien « administrateur d'unité » devient administrateur technique. Son rôle métier n'est jamais déduit de ce statut :
équipier, sauf si une fonction de commandant adjoint est déjà renseignée sur sa fiche (état-major, fonction conservée).
Chaque conversion est tracée dans le journal d'audit ; le sens inverse restaure le rôle d'origine.
"""
from django.db import migrations, models

ACTION = "l06_migration_role"


def separer(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    AuditLog = apps.get_model("accounts", "AuditLog")
    for profil in UserProfile.objects.filter(role="ADMIN_NAVIRE"):
        # Un administrateur d'unité ne tenait aucune fonction métier : le champ « fonction » n'était pas exercé hors état-major.
        # Aucune fonction n'est donc déduite ; celle qui figure sur la fiche est seulement journalisée, à confirmer.
        # La valeur n'est pas laissée sur la fiche : elle s'activerait à la première promotion en état-major sans confirmation.
        fonction = profil.fonction_coma
        profil.role = "EQUIPIER"
        profil.fonction_coma = ""
        profil.administrateur_technique = True
        profil.save(update_fields=["role", "administrateur_technique", "fonction_coma"])
        AuditLog.objects.create(
            actor=None, action=ACTION, target_user_id=profil.user_id,
            details=f"avant=ADMIN_NAVIRE; apres={profil.role}; fonction_a_confirmer={fonction or 'aucune'}",
        )


def restaurer(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    AuditLog = apps.get_model("accounts", "AuditLog")
    for journal in AuditLog.objects.filter(action=ACTION):
        apres = journal.details.split("apres=")[1].split(";")[0]
        fonction = journal.details.split("fonction_a_confirmer=")[1]
        # Un rôle modifié depuis la migration n'est pas écrasé.
        UserProfile.objects.filter(user_id=journal.target_user_id, administrateur_technique=True, role=apres).update(
            role="ADMIN_NAVIRE", administrateur_technique=False, fonction_coma="" if fonction == "aucune" else fonction)
        journal.delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0023_protection_suppression_unites")]
    operations = [
        migrations.AddField(
            model_name="userprofile", name="administrateur_technique",
            field=models.BooleanField(default=False, verbose_name="Administrateur technique"),
        ),
        migrations.AlterField(
            model_name="userprofile", name="role",
            field=models.CharField(choices=[
                ("MASTER_ADMIN", "Administrateur général"), ("ADMIN_NAVIRE", "Administrateur d'unité (obsolète)"),
                ("COMMANDANT", "Commandant"), ("COMMANDANT_EN_SECOND", "Commandant en second"), ("ETAT_MAJOR", "État-major"),
                ("CHEF_SERVICE", "Chef de service"), ("CHEF_SECTEUR", "Chef de secteur"), ("CHEF_SECTION", "Chef de section"),
                ("EQUIPIER", "Équipier")], max_length=32),
        ),
        migrations.AlterField(
            model_name="roleavailability", name="code",
            field=models.CharField(choices=[
                ("MASTER_ADMIN", "Administrateur général"), ("ADMIN_NAVIRE", "Administrateur d'unité (obsolète)"),
                ("COMMANDANT", "Commandant"), ("COMMANDANT_EN_SECOND", "Commandant en second"), ("ETAT_MAJOR", "État-major"),
                ("CHEF_SERVICE", "Chef de service"), ("CHEF_SECTEUR", "Chef de secteur"), ("CHEF_SECTION", "Chef de section"),
                ("EQUIPIER", "Équipier")], max_length=64, unique=True),
        ),
        migrations.RunPython(separer, restaurer),
    ]
