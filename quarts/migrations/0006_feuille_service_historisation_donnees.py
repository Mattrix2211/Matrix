import uuid

from django.db import migrations
from django.utils import timezone


def remplir_identites_et_figer(apps, schema_editor):
    """Identités stables pour l'existant ; saisies re-clefées par identité ; feuilles non
    publiées figées sur les réglages actuels. Les feuilles publiées restent sans instantané
    (affichées d'après leurs versions), leur structure d'origine n'étant pas connue."""
    Rubrique = apps.get_model("quarts", "RubriqueEnTeteFeuilleService")
    Fonction = apps.get_model("quarts", "FonctionFeuilleService")
    Feuille = apps.get_model("quarts", "FeuilleService")
    for modele in (Rubrique, Fonction):
        for objet in modele.objects.filter(uid__isnull=True):
            objet.uid = uuid.uuid4()
            objet.save(update_fields=["uid"])

    maintenant = timezone.now().isoformat()
    structures = {}
    for feuille in Feuille.objects.all():
        rubriques = list(Rubrique.objects.filter(ship_id=feuille.ship_id).order_by("ordre", "pk"))
        par_pk = {str(r.pk): str(r.uid) for r in rubriques}
        valeurs = {par_pk.get(cle, cle): v for cle, v in (feuille.valeurs_entete or {}).items()}
        champs = []
        if valeurs != feuille.valeurs_entete:
            feuille.valeurs_entete = valeurs
            champs.append("valeurs_entete")
        if feuille.statut != "PUBLIEE":
            if feuille.ship_id not in structures:
                structures[feuille.ship_id] = {
                    "origine": "migration",
                    "figee_le": maintenant,
                    "rubriques": [
                        {
                            "uid": str(r.uid), "libelle": r.libelle, "ordre": r.ordre,
                            "type_saisie": r.type_saisie, "valeur_fixe": r.valeur_fixe,
                        }
                        for r in rubriques if r.actif
                    ],
                    "fonctions": [
                        {
                            "uid": str(f.uid), "libelle": f.libelle, "ordre": f.ordre,
                            "poste_recherche": f.poste_recherche,
                        }
                        for f in Fonction.objects.filter(ship_id=feuille.ship_id, actif=True).order_by("ordre", "pk")
                    ],
                }
            feuille.structure_figee = structures[feuille.ship_id]
            champs.append("structure_figee")
        if champs:
            feuille.save(update_fields=champs)


def rekeyer_par_pk(apps, schema_editor):
    """Retour arrière : saisies re-clefées par identifiant de rubrique ; les structures figées sont abandonnées."""
    Rubrique = apps.get_model("quarts", "RubriqueEnTeteFeuilleService")
    Feuille = apps.get_model("quarts", "FeuilleService")
    for feuille in Feuille.objects.all():
        par_uid = {str(r.uid): str(r.pk) for r in Rubrique.objects.filter(ship_id=feuille.ship_id) if r.uid}
        valeurs = {par_uid.get(cle, cle): v for cle, v in (feuille.valeurs_entete or {}).items()}
        if valeurs != feuille.valeurs_entete:
            feuille.valeurs_entete = valeurs
            feuille.save(update_fields=["valeurs_entete"])


class Migration(migrations.Migration):

    dependencies = [
        ("quarts", "0005_feuille_service_identites_structure"),
    ]

    operations = [
        migrations.RunPython(remplir_identites_et_figer, rekeyer_par_pk),
    ]
