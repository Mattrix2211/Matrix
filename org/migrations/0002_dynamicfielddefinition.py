from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("org", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DynamicFieldDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100)),
                ("label", models.CharField(max_length=255)),
                ("type", models.CharField(choices=[("text", "Texte"), ("number", "Nombre"), ("date", "Date"), ("choice", "Choix"), ("checkbox", "Case à cocher")], max_length=20)),
                ("required", models.BooleanField(default=False)),
                ("unit", models.CharField(blank=True, default="", max_length=20)),
                ("choices", models.JSONField(blank=True, default=list)),
                ("applies_to", models.CharField(blank=True, default="", help_text="asset_type|checklist_template", max_length=50)),
                ("sector", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dynamic_fields", to="org.sector")),
            ],
        ),
    ]
