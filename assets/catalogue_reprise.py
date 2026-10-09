"""Reprise de l'existant : dossiers de matériel (AssetFolder) vers catégories du catalogue.

Mode proposé puis validé : `planifier` ne fait que lire, `appliquer` écrit en
transaction. Aucun dossier ni matériel n'est supprimé ou déplacé ; le matériel
reçoit seulement, s'il n'en a pas, le lien `article_catalogue`.
"""
import csv

from django.db import transaction

from accounts.models import AuditLog, SpecialityChoice

from .models import ArticleCatalogue, Asset, AssetFolder, CategorieCatalogue


def lire_correspondance(chemin):
    """Table {chemin de dossier: nom de spécialité} depuis un CSV `dossier;specialite`."""
    with open(chemin, encoding="utf-8-sig", newline="") as fichier:
        echantillon = fichier.read(2048)
        fichier.seek(0)
        separateur = ";" if echantillon.count(";") >= echantillon.count(",") else ","
        lignes = csv.DictReader(fichier, delimiter=separateur)
        return {
            (ligne.get("dossier") or "").strip(): (ligne.get("specialite") or "").strip()
            for ligne in lignes if (ligne.get("dossier") or "").strip()
        }


def _cle_article(materiel):
    return tuple((getattr(materiel, champ) or "").strip() for champ in ("designation", "marque", "reference"))


def planifier(specialite_defaut="", correspondance=None):
    """Rapport de correspondance, sans aucune écriture.

    Renvoie une liste ordonnée (parents avant enfants) de dictionnaires :
    dossier, chemin, specialite (nom ou None), nb_materiels, articles (clés distinctes),
    sans_designation (matériels qui ne pourront pas recevoir d'article).
    """
    correspondance = correspondance or {}
    dossiers = list(AssetFolder.objects.select_related("parent"))
    enfants = {}
    for dossier in dossiers:
        enfants.setdefault(dossier.parent_id, []).append(dossier)
    materiels = {}
    for materiel in Asset.objects.filter(folder__isnull=False):
        materiels.setdefault(materiel.folder_id, []).append(materiel)

    rapport = []

    def parcourir(parent_id, chemin_parent, specialite_parent):
        for dossier in sorted(enfants.get(parent_id, []), key=lambda d: d.name.lower()):
            chemin = f"{chemin_parent} / {dossier.name}" if chemin_parent else dossier.name
            specialite = (
                correspondance.get(chemin.replace(" / ", "/")) or correspondance.get(dossier.name)
                or specialite_parent or specialite_defaut or None
            )
            contenu = materiels.get(dossier.pk, [])
            avec_designation = [m for m in contenu if _cle_article(m)[0]]
            rapport.append({
                "dossier": dossier, "chemin": chemin, "specialite": specialite,
                "nb_materiels": len(contenu),
                "articles": sorted({_cle_article(m) for m in avec_designation}),
                "sans_designation": len(contenu) - len(avec_designation),
            })
            parcourir(dossier.pk, chemin, specialite)

    parcourir(None, "", None)
    return rapport


@transaction.atomic
def appliquer(rapport):
    """Crée catégories et articles manquants (idempotent) et rattache le matériel.

    Les lignes sans spécialité sont ignorées. Renvoie un compteur des créations.
    """
    noms = {s.name.lower(): s for s in SpecialityChoice.objects.all()}
    bilan = {"categories": 0, "articles": 0, "rattaches": 0, "ignores": 0}
    categories = {}
    for ligne in rapport:
        specialite = noms.get((ligne["specialite"] or "").lower())
        if specialite is None:
            bilan["ignores"] += 1
            continue
        dossier = ligne["dossier"]
        parent = categories.get(dossier.parent_id)
        # Une sous-catégorie suit la spécialité de son parent : sinon, elle devient une racine.
        if parent is not None and parent.specialite_id != specialite.pk:
            parent = None
        categorie = CategorieCatalogue.objects.filter(parent=parent, nom=dossier.name).first()
        if categorie is None:
            categorie = CategorieCatalogue.objects.create(parent=parent, nom=dossier.name, specialite=specialite)
            bilan["categories"] += 1
            AuditLog.objects.create(action="catalogue_reprise_categorie", details=f"id={categorie.pk}; dossier={dossier.pk}; chemin={ligne['chemin']}")
        categories[dossier.pk] = categorie
        for designation, marque, reference in ligne["articles"]:
            article = ArticleCatalogue.objects.filter(
                categorie=categorie, designation=designation, marque=marque, reference=reference).first()
            if article is None:
                modele = Asset.objects.filter(folder=dossier, designation=designation, marque=marque, reference=reference).exclude(nno="").first()
                article = ArticleCatalogue.objects.create(
                    categorie=categorie, designation=designation, marque=marque, reference=reference,
                    nno=modele.nno if modele else "")
                bilan["articles"] += 1
                AuditLog.objects.create(action="catalogue_reprise_article", details=f"id={article.pk}; dossier={dossier.pk}")
            # Seuls les matériels sans article sont rattachés : un choix existant n'est jamais écrasé.
            bilan["rattaches"] += Asset.objects.filter(
                folder=dossier, designation=designation, marque=marque, reference=reference,
                article_catalogue__isnull=True).update(article_catalogue=article)
    AuditLog.objects.create(action="catalogue_reprise", details=(
        f"categories={bilan['categories']}; articles={bilan['articles']}; "
        f"rattaches={bilan['rattaches']}; dossiers_ignores={bilan['ignores']}"))
    return bilan
