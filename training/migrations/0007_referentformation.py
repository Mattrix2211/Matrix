# Migration additive (phase 1/3 de la portabilité des formations, cf. tâche
# Notion « Formation unique et portable entre navires ») : crée le nouveau
# modèle ReferentFormation SANS toucher à TrainingCourse.sector/referents.
# Ordre impératif : (1) cette migration additive, (2) la commande de gestion
# `fusionner_formations` (training/management/commands/), (3) la migration
# finale 0008 qui retire sector/referents une fois la fusion vérifiée.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('org', '0003_delete_dynamicfielddefinition'),
        ('training', '0006_referentformationnavire'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferentFormation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referents', to='training.trainingcourse')),
                ('ship', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referents_formation', to='org.ship')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='formations_referentes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterUniqueTogether(
            name='referentformation',
            unique_together={('course', 'ship', 'user')},
        ),
    ]
