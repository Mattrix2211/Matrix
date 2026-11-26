"""Corrections de sécurité de L06 sur le schéma de 0029 : compteurs indexés et bornés, opérateurs de récupération à nom unique,
essais de code comptés par source (la colonne par demande et le statut « bloquée » disparaissent).

Cette migration rattrape toute base ayant déjà appliqué la version initiale de 0029 (recette, démonstration) ; sur une base
neuve elle s'enchaîne sans effet de données. Le retour arrière rétablit le schéma, pas les données nettoyées."""
from django.db import migrations, models


def nettoyer(apps, schema_editor):
    Demande = apps.get_model("accounts", "DemandeReinitialisation")
    Operateur = apps.get_model("accounts", "OperateurRecuperation")
    Compteur = apps.get_model("accounts", "CompteurConnexion")
    User = apps.get_model("auth", "User")
    # Une demande « bloquée » (ancien mécanisme) est annulée : le titulaire demande un nouveau code.
    Demande.objects.filter(statut="BLOQUEE").update(statut="ANNULEE")
    # Noms d'opérateurs : le doublon reçoit un suffixe, l'habilitation et l'identité système restent inchangées.
    vus = set()
    for operateur in Operateur.objects.order_by("pk"):
        nom, rang = operateur.nom, 1
        while nom in vus:
            rang += 1
            nom = f"{operateur.nom} ({rang})"
        vus.add(nom)
        if nom != operateur.nom:
            Operateur.objects.filter(pk=operateur.pk).update(nom=nom)
    # Compteurs d'identifiants qui ne désignent aucun compte (flot d'identifiants inventés de l'ancienne version).
    existants = {nom.lower() for nom in User.objects.values_list("username", flat=True)}
    inutiles = [i for i in Compteur.objects.values_list("identifiant", flat=True).distinct()
                if i not in existants and not i.startswith(("code:",))]
    for debut in range(0, len(inutiles), 500):
        Compteur.objects.filter(identifiant__in=inutiles[debut:debut + 500]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0029_securite_reinitialisation_administrateur_general"),
    ]

    operations = [
        migrations.RunPython(nettoyer, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="demandereinitialisation",
            name="essais",
        ),
        migrations.AlterField(
            model_name="compteurconnexion",
            name="derniere_activite",
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name="demandereinitialisation",
            name="statut",
            field=models.CharField(
                choices=[
                    ("EN_ATTENTE_VERIFICATION", "En attente de vérification d'identité"),
                    ("ACTIVE", "Active"),
                    ("UTILISEE", "Utilisée"),
                    ("EXPIREE", "Expirée"),
                    ("ANNULEE", "Annulée"),
                ],
                default="ACTIVE",
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="operateurrecuperation",
            name="nom",
            field=models.CharField(max_length=128, unique=True),
        ),
    ]
