from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("assets", "0038_fiches_niveau_coherent")]

    operations = [
        migrations.RemoveConstraint(model_name="installationmaintenance", name="fiche_installation_xor_categorie"),
        migrations.AddConstraint(
            model_name="installationmaintenance",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("categorie__isnull", True),
                        ("installation__isnull", False),
                        ("niveau", "BORD"),
                    ),
                    models.Q(
                        ("categorie__isnull", False),
                        ("installation__isnull", True),
                        ("niveau", "FLOTTE"),
                    ),
                    models.Q(
                        ("categorie__isnull", True),
                        ("installation__isnull", True),
                        ("niveau", "FLOTTE"),
                        ("specialite__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="fiche_cible_coherente",
            ),
        ),
    ]
