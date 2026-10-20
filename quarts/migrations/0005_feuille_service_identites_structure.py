from django.db import migrations, models


class Migration(migrations.Migration):
    """Étape 1 : colonnes additives (identités nullables, structure figée)."""

    dependencies = [
        ("quarts", "0004_feuille_service_alertes_versions_listes"),
    ]

    operations = [
        migrations.AddField(
            model_name="rubriqueentetefeuilleservice",
            name="uid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="fonctionfeuilleservice",
            name="uid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="feuilleservice",
            name="structure_figee",
            field=models.JSONField(
                blank=True, null=True, verbose_name="Structure figée (rubriques et fonctions)",
                help_text="Rubriques et fonctions du bâtiment à la création de la feuille ; vide : feuille antérieure à l'historisation.",
            ),
        ),
        migrations.AlterField(
            model_name="feuilleservice",
            name="valeurs_entete",
            field=models.JSONField(
                blank=True, default=dict, verbose_name="Valeurs des rubriques d'en-tête",
                help_text="Dictionnaire {uid de la rubrique : valeur saisie} pour les rubriques « saisie chaque jour ».",
            ),
        ),
    ]
