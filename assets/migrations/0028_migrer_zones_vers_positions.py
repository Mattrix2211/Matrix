# Generated à la main le 10/09/2026 — remplacement des zones rectangulaires du
# plan visuel du navire par un positionnement précis (épingle x/y) par
# matériel, décision métier tranchée par l'utilisateur (cf. tâche Notion
# « Remplacer les zones du plan navire par un placement PRÉCIS du matériel »).
from django.db import migrations


def migrer_zones_vers_positions(apps, schema_editor):
    """Reprend les zones existantes (ancien système Zone, supprimé par cette
    migration) : pour chaque zone reliée à un Emplacement, place une épingle
    au centre géométrique de la zone pour chaque matériel de cet emplacement
    qui n'a pas déjà reçu de position (le premier centre rencontré l'emporte
    en cas de recoupement entre plusieurs zones pour le même emplacement,
    faute de règle métier permettant de départager). Ce n'est qu'un point de
    départ éditable : le chef de service repositionne ensuite précisément
    chaque matériel d'un simple clic sur le plan.

    Vérifié sur la base de développement au moment d'écrire cette migration :
    aucune zone n'y existait (0 ligne assets_zone), donc rien à migrer en
    pratique ici — ce code reste nécessaire pour ne pas perdre de données sur
    toute base ayant déjà des zones renseignées."""
    Zone = apps.get_model('assets', 'Zone')
    Asset = apps.get_model('assets', 'Asset')
    for zone in Zone.objects.exclude(location_id=None).iterator():
        points = zone.points or []
        if not points:
            continue
        try:
            xs = [float(p['x']) for p in points]
            ys = [float(p['y']) for p in points]
        except (TypeError, KeyError, ValueError):
            continue
        centre_x = round(sum(xs) / len(xs), 2)
        centre_y = round(sum(ys) / len(ys), 2)
        Asset.objects.filter(location_id=zone.location_id, plan_deck__isnull=True).update(
            plan_deck_id=zone.deck_id, position_x=centre_x, position_y=centre_y,
        )


def revenir_en_arriere(apps, schema_editor):
    """Pas de retour en arrière automatique : redessiner des zones à partir
    des positions x/y n'aurait pas de sens univoque (plusieurs matériels
    peuvent désormais être dispersés là où une seule zone existait avant)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0027_asset_position_plan'),
    ]

    operations = [
        migrations.RunPython(migrer_zones_vers_positions, revenir_en_arriere),
        migrations.DeleteModel(
            name='Zone',
        ),
    ]
