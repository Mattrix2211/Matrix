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
    # Réglages lus une seule fois par bâtiment.
    rubriques_par_navire, fonctions_par_navire, structures = {}, {}, {}
    for rubrique in Rubrique.objects.order_by("ordre", "pk"):
        rubriques_par_navire.setdefault(rubrique.ship_id, []).append(rubrique)
    for fonction in Fonction.objects.filter(actif=True).order_by("ordre", "pk"):
        fonctions_par_navire.setdefault(fonction.ship_id, []).append(fonction)

    a_sauver = []
    for feuille in Feuille.objects.all():
        rubriques = rubriques_par_navire.get(feuille.ship_id, [])
        par_pk = {str(r.pk): str(r.uid) for r in rubriques}
        valeurs = {par_pk.get(cle, cle): v for cle, v in (feuille.valeurs_entete or {}).items()}
        modifiee = valeurs != feuille.valeurs_entete
        feuille.valeurs_entete = valeurs
        if feuille.statut != "PUBLIEE" and feuille.structure_figee is None:
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
                        for f in fonctions_par_navire.get(feuille.ship_id, [])
                    ],
                }
            feuille.structure_figee = structures[feuille.ship_id]
            modifiee = True
        if modifiee:
            a_sauver.append(feuille)
    Feuille.objects.bulk_update(a_sauver, ["valeurs_entete", "structure_figee"], batch_size=500)


def rekeyer_par_pk(apps, schema_editor):
    """Retour arrière : saisies re-clefées par identifiant de rubrique ; les structures figées sont abandonnées."""
    Rubrique = apps.get_model("quarts", "RubriqueEnTeteFeuilleService")
    Feuille = apps.get_model("quarts", "FeuilleService")
    par_uid_navire = {}
    for rubrique in Rubrique.objects.all():
        par_uid_navire.setdefault(rubrique.ship_id, {})[str(rubrique.uid)] = str(rubrique.pk)
    a_sauver = []
    for feuille in Feuille.objects.all():
        par_uid = par_uid_navire.get(feuille.ship_id, {})
        valeurs = {par_uid.get(cle, cle): v for cle, v in (feuille.valeurs_entete or {}).items()}
        if valeurs != feuille.valeurs_entete:
            feuille.valeurs_entete = valeurs
            a_sauver.append(feuille)
    Feuille.objects.bulk_update(a_sauver, ["valeurs_entete"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("quarts", "0005_feuille_service_identites_structure"),
    ]

    operations = [
        migrations.RunPython(remplir_identites_et_figer, rekeyer_par_pk),
    ]
