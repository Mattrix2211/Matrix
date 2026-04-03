from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logistics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="correctiveticket",
            name="planned_for",
            field=models.DateField(null=True, blank=True),
        ),
    ]
