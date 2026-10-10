"""Adaptation locale d'une fiche flotte d'installation : le navire garde sa propre fiche, tracée comme
« adaptée de la fiche flotte vX », et décide s'il reprend les changements quand la fiche flotte évolue."""
from django.db import transaction

from accounts.models import AuditLog

from . import fiche_flotte, fiche_maintenance, fiche_validation as validation
from .models import Installation, InstallationMaintenance
from .proposition_article import ErreurCircuit


def flotte_adaptable(installation, flotte):
    """La fiche flotte vise cette installation, est validée et n'a pas encore d'adaptation sur ce navire."""
    if flotte.niveau != "FLOTTE" or flotte.categorie_id or flotte.version_validee is None:
        return False
    return (flotte in fiche_flotte.fiches_pour_installation(installation)
            and not installation.maintenances.filter(origine=flotte).exists())


def fiches_flotte_proposees(installation):
    """Fiches flotte applicables à l'installation que le navire n'a pas encore reprises."""
    return [f for f in fiche_flotte.fiches_pour_installation(installation) if flotte_adaptable(installation, f)]


def contenu_de_adaptation(flotte):
    """Contenu de départ de l'adaptation : celui de la version flotte appliquée, lignes à identité neuve."""
    contenu = fiche_maintenance.contenu_de(flotte.version_validee) | {"resume_modifications": ""}
    for ligne in contenu["lignes"]:
        ligne["cle"] = None
    return contenu


def _verrouiller(pk):
    """Adaptation verrouillée, installation d'abord puis fiche (même ordre que `soumettre`, sans interblocage)."""
    installation_id = (InstallationMaintenance.objects.filter(pk=pk, niveau="BORD", origine__isnull=False)
                       .values_list("installation_id", flat=True).first())
    if installation_id is None:
        raise ErreurCircuit("Cette fiche n'est pas une adaptation d'une fiche flotte.")
    Installation.objects.select_for_update().get(pk=installation_id)
    fiche = (InstallationMaintenance.objects.select_for_update(of=("self",)).select_related("installation__service", "origine")
             .filter(pk=pk, niveau="BORD", origine__isnull=False).first())
    if fiche is None:
        raise ErreurCircuit("Cette fiche n'est pas une adaptation d'une fiche flotte.")
    if fiche.origine_en_attente is None:
        raise ErreurCircuit("Aucun changement de la fiche flotte n'est à examiner : actualisez la page.")
    return fiche


@transaction.atomic
def reprendre(user, pk):
    """Le navire reprend la version flotte : nouvelle version locale, qui suit le circuit du bord."""
    fiche = _verrouiller(pk)
    flotte_version = fiche.origine.version_validee
    if flotte_version is None:
        raise ErreurCircuit("La fiche flotte n'a plus de version appliquée.")
    contenu = fiche_maintenance.contenu_de(flotte_version) | {
        "resume_modifications": f"Reprise de la fiche flotte v{flotte_version.numero}."}
    # Les lignes de même libellé gardent leur identité locale (historique et graphiques continus).
    locales = {i.label.strip().lower(): i.cle for i in fiche.version_validee.items.all()} if fiche.version_validee else {}
    for ligne in contenu["lignes"]:
        ligne["cle"] = locales.pop(ligne["label"].strip().lower(), None)
    version = validation.soumettre(user, fiche.installation, contenu, fiche)
    fiche.origine_numero, fiche.origine_en_attente = flotte_version.numero, None
    fiche.save(update_fields=["origine_numero", "origine_en_attente", "updated_at"])
    AuditLog.objects.create(
        actor=user, action="fiche.origine.reprise",
        details=f"« {fiche.title} » ({fiche.pk}) reprend la fiche flotte v{flotte_version.numero}; version locale v{version.numero}")
    return version


@transaction.atomic
def garder(user, pk):
    """Le navire garde son adaptation : la décision est tracée, la fiche locale ne change pas."""
    fiche = _verrouiller(pk)
    autorise, raison = validation.peut_rediger(user, fiche.installation)
    if not autorise:
        raise ErreurCircuit(raison)
    numero = fiche.origine_en_attente
    fiche.origine_en_attente = None
    fiche.save(update_fields=["origine_en_attente", "updated_at"])
    AuditLog.objects.create(
        actor=user, action="fiche.origine.gardee",
        details=f"« {fiche.title} » ({fiche.pk}) garde son adaptation de la fiche flotte v{fiche.origine_numero} (v{numero} non reprise)")
