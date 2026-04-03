from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0017_installation_iso_periodicity_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstallationExtraField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.userprofile')),
                ('label', models.CharField(max_length=255)),
                ('value', models.TextField(blank=True, default='')),
                ('order', models.PositiveIntegerField(default=0)),
                ('installation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extra_fields', to='assets.installation')),
            ],
            options={'ordering': ['order', 'label']},
        ),
    ]
