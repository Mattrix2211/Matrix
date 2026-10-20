import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Étape 3 : identités obligatoires et uniques."""

    dependencies = [
        ("quarts", "0006_feuille_service_historisation_donnees"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rubriqueentetefeuilleservice",
            name="uid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="fonctionfeuilleservice",
            name="uid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
