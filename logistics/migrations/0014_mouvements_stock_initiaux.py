from django.db import migrations

MOTIF = "Inventaire initial (reprise du stock existant)"


def creer_inventaires_initiaux(apps, schema_editor):
    """Un mouvement par pièce déjà en stock, pour que la somme des mouvements égale la quantité actuelle."""
    StockPiece = apps.get_model("logistics", "StockPiece")
    MouvementStock = apps.get_model("logistics", "MouvementStock")
    MouvementStock.objects.bulk_create([
        MouvementStock(piece=p, type="INVENTAIRE", quantite=p.quantite, solde_apres=p.quantite, motif=MOTIF)
        for p in StockPiece.objects.filter(quantite__gt=0)
    ])


def supprimer_inventaires_initiaux(apps, schema_editor):
    apps.get_model("logistics", "MouvementStock").objects.filter(motif=MOTIF, auteur__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("logistics", "0013_mouvement_stock"),
    ]

    operations = [
        migrations.RunPython(creer_inventaires_initiaux, supprimer_inventaires_initiaux),
    ]
