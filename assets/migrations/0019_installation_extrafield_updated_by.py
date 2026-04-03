from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0018_installation_extrafield'),
    ]

    operations = [
        migrations.AddField(
            model_name='installationextrafield',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_installationextrafield_set', to=settings.AUTH_USER_MODEL),
        ),
    ]
