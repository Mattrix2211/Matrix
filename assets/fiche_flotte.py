"""Fiches flotte : une fiche de matériel vaut pour sa catégorie du catalogue et ses sous-catégories.

Pour une gamme donnée, la fiche de la catégorie la plus proche de l'article s'applique : une
sous-catégorie remplace, pour cette gamme seulement, la fiche de son parent.
"""
from .fiche_maintenance import gamme_de
from .models import CategorieCatalogue, ChecklistTemplate, InstallationMaintenance

PROFONDEUR_MAX = 20  # garde-fou : la hiérarchie est protégée contre les cycles


def chaine(categorie):
    """La catégorie puis ses parents, du plus proche au plus lointain."""
    noeuds = []
    while categorie is not None and len(noeuds) < PROFONDEUR_MAX:
        noeuds.append(categorie)
        categorie = categorie.parent
    return noeuds


def descendants(categorie):
    """Identifiants de la catégorie et de toutes ses sous-catégories."""
    ids, frontiere = {categorie.pk}, {categorie.pk}
    while frontiere:
        frontiere = set(CategorieCatalogue.objects.filter(parent_id__in=frontiere).values_list("pk", flat=True)) - ids
        ids |= frontiere
    return ids


def cle_gamme(fiche):
    """Identité de la gamme (texte normalisé) de la version validée ; None tant qu'aucune n'est validée."""
    version = fiche.version_validee
    return gamme_de(version).strip().lower() if version else None


def fiches_applicables(categorie):
    """{gamme: fiche} pour une catégorie : à gamme égale, la fiche de la catégorie la plus proche l'emporte."""
    noeuds = chaine(categorie)
    fiches = InstallationMaintenance.objects.filter(niveau="FLOTTE", categorie_id__in=[n.pk for n in noeuds])
    par_categorie = {}
    for fiche in fiches.select_related("categorie"):
        par_categorie.setdefault(fiche.categorie_id, []).append(fiche)
    retenues = {}
    for noeud in noeuds:
        for fiche in par_categorie.get(noeud.pk, []):
            cle = cle_gamme(fiche)
            if cle is not None:
                retenues.setdefault(cle, fiche)
    return retenues


def version_applicable(asset, fiche, cache=None):
    """Version validée de la fiche que suit ce matériel pour la gamme de `fiche` (celle de la catégorie la
    plus proche). `cache` : dictionnaire partagé par une série d'appels, pour ne pas répéter les requêtes."""
    cache = {} if cache is None else cache

    def memo(cle, calcul):
        if cle not in cache:
            cache[cle] = calcul()
        return cache[cle]

    retenue = fiche
    if asset.article_catalogue_id:
        cle = memo(("gamme", fiche.pk), lambda: cle_gamme(fiche))
        if cle:
            categorie = asset.article_catalogue.categorie
            retenue = memo(("categorie", categorie.pk), lambda: fiches_applicables(categorie)).get(cle, fiche)
    return memo(("version", retenue.pk), lambda: retenue.version_validee)


def fiches_de_categorie(categorie):
    """Fiches applicables à une catégorie, triées par gamme : [{fiche, version, heritee}]."""
    return [
        {"fiche": f, "version": f.version_validee, "heritee": f.categorie_id != categorie.pk}
        for _, f in sorted(fiches_applicables(categorie).items())
    ]


def propositions_en_cours(categorie):
    """Versions de fiche en circuit (ou renvoyées) rattachées à la catégorie ou à ses parents."""
    return (ChecklistTemplate.objects.exclude(etat=ChecklistTemplate.Etat.VALIDEE)
            .filter(fiche__niveau="FLOTTE", fiche__categorie_id__in=[n.pk for n in chaine(categorie)])
            .select_related("fiche__categorie", "redacteur"))


def fiches_pour_installation(installation):
    """Fiches flotte d'installation qui visent cette installation (même désignation, référence et classe)."""
    classe = installation.ship.classe_navire
    fiches = InstallationMaintenance.objects.filter(
        niveau="FLOTTE", categorie__isnull=True, equipement__iexact=installation.designation)
    reference = installation.reference
    retenues = []
    for fiche in fiches.select_related("specialite"):
        if fiche.reference_equipement and fiche.reference_equipement.lower() != reference.lower():
            continue
        if fiche.classe_navire and fiche.classe_navire.lower() != classe.lower():
            continue
        if fiche.version_validee:
            retenues.append(fiche)
    return retenues
