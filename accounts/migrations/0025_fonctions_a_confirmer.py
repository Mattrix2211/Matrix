"""Fonctions à confirmer (AC-14) et expiration du mot de passe provisoire (AC-12).

Les fonctions journalisées par la migration 0024 (`fonction_a_confirmer=…`) deviennent des demandes en attente ;
aucune fonction n'est appliquée : tant qu'une autorité ne l'a pas confirmée, elle ne confère aucun droit.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


ACTION = "l06_migration_role"


def creer_demandes(apps, schema_editor):
    AuditLog = apps.get_model("accounts", "AuditLog")
    Demande = apps.get_model("accounts", "FonctionAConfirmer")
    UserProfile = apps.get_model("accounts", "UserProfile")
    for ligne in AuditLog.objects.filter(action=ACTION, target_user__isnull=False):
        fonction = ligne.details.split("fonction_a_confirmer=")[-1]
        if fonction in ("", "aucune") or Demande.objects.filter(user_id=ligne.target_user_id).exists():
            continue
        profil = UserProfile.objects.filter(user_id=ligne.target_user_id).first()
        Demande.objects.create(user_id=ligne.target_user_id, ship_id=profil.ship_id if profil else None, fonction_ancienne=fonction)


def supprimer_demandes(apps, schema_editor):
    apps.get_model("accounts", "FonctionAConfirmer").objects.filter(statut="EN_ATTENTE").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0024_administrateur_technique"),
        ("org", "0018_protection_suppression_unites"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="mot_de_passe_provisoire_expire_le",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="FonctionAConfirmer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "fonction_ancienne",
                    models.CharField(
                        choices=[
                            ("COMAEQ", "COMAEQ (équipage)"),
                            ("COMOPS", "COMOPS (opérations)"),
                            ("COMANAV", "COMANAV (navire)"),
                            ("COMAVIA", "COMAVIA (aviation)"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("EN_ATTENTE", "En attente"),
                            ("CONFIRMEE", "Confirmée"),
                            ("CORRIGEE", "Corrigée"),
                            ("REFUSEE", "Refusée"),
                        ],
                        default="EN_ATTENTE",
                        max_length=12,
                    ),
                ),
                (
                    "fonction_retenue",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("COMAEQ", "COMAEQ (équipage)"),
                            ("COMOPS", "COMOPS (opérations)"),
                            ("COMANAV", "COMANAV (navire)"),
                            ("COMAVIA", "COMAVIA (aviation)"),
                        ],
                        default="",
                        max_length=16,
                    ),
                ),
                ("decide_le", models.DateTimeField(blank=True, null=True)),
                (
                    "decide_par",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="fonctions_decidees",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ship",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="fonctions_a_confirmer",
                        to="org.ship",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fonctions_a_confirmer",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("created_at",),
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("statut", "EN_ATTENTE")),
                        fields=("user",),
                        name="une_fonction_en_attente_par_compte",
                    )
                ],
            },
        ),
        migrations.RunPython(creer_demandes, supprimer_demandes),
    ]
