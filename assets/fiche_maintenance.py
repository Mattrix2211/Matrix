"""Fiches de maintenance : le calendrier dit QUAND, la fiche dit COMMENT.

Une fiche = une gamme (calendaire ou heures de marche). Ses versions sont des
ChecklistTemplate ; la fiche reflète la version validée, c'est elle qui alimente
le moteur d'échéances existant (generate_installation_occurrences).
"""
from django.db import transaction
from django.utils import timezone

from .models import (
    ChecklistItemTemplate, ChecklistTemplate, FicheEtape, FichePreparation, ModeDeclenchement,
)
from .mesures import formater_nombre

UNITES = {"J": ("jour", "jours"), "S": ("semaine", "semaines"), "M": ("mois", "mois"), "A": ("an", "ans")}
CHAMPS_TEXTE = ("name", "description", "resume_modifications")
CHAMPS_DECLENCHEMENT = ("mode_declenchement", "intervalle", "unite_intervalle", "seuil_heures")


def libelle_gamme(mode, intervalle, unite, seuil):
    """« 3 mois », « 1 000 h » ou « 3 mois ou 1 000 h » : identité lisible de la gamme."""
    parties = []
    if mode in (ModeDeclenchement.CALENDRIER, ModeDeclenchement.LES_DEUX) and intervalle and unite in UNITES:
        singulier, pluriel = UNITES[unite]
        parties.append(f"{intervalle} {singulier if intervalle == 1 else pluriel}")
    if mode in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX) and seuil:
        parties.append(f"{formater_nombre(seuil)} h")
    return " ou ".join(parties) or "—"


def gamme_de(version):
    return libelle_gamme(version.mode_declenchement, version.intervalle, version.unite_intervalle, version.seuil_heures)


def gammes_prises(installation, sauf=None):
    """Gammes déjà couvertes par une fiche de l'installation (version en cours ou validée)."""
    prises = set()
    for fiche in installation.maintenances.exclude(pk=getattr(sauf, "pk", None)).prefetch_related("versions"):
        version = fiche.version_en_cours or fiche.version_validee
        if version:
            prises.add(gamme_de(version))
    return prises


def contenu_de(version):
    """Contenu complet d'une version, sous la forme attendue par creer_version (assistant, copie)."""
    contenu = {c: getattr(version, c) for c in CHAMPS_TEXTE + CHAMPS_DECLENCHEMENT}
    contenu.update(
        duree_estimee_min=version.duree_estimee_min, nb_personnes=version.nb_personnes,
        qualification=version.qualification_id,
        preparations=[{"type": p.type, "libelle": p.libelle, "quantite": p.quantite, "piece": p.piece_id}
                      for p in version.preparations.all()],
        etapes=[{"texte": e.texte, "attention": e.attention} for e in version.etapes.all()],
        lignes=[{"cle": i.cle, "label": i.label, "field_type": i.field_type, "unit": i.unit, "required": i.required,
                 "valeur_min": i.valeur_min, "valeur_max": i.valeur_max}
                for i in version.items.order_by("order", "pk")],
    )
    return contenu


def _ecrire_contenu(version, contenu):
    """Remplace tout le contenu de la version (champs, préparation, étapes, lignes)."""
    for champ in CHAMPS_TEXTE + CHAMPS_DECLENCHEMENT + ("duree_estimee_min", "nb_personnes"):
        setattr(version, champ, contenu[champ])
    version.qualification_id = contenu.get("qualification")
    version.save()
    version.preparations.all().delete()
    version.etapes.all().delete()
    ancien = {i.cle: i for i in version.items.all()}
    gardees = set()
    for ordre, p in enumerate(contenu["preparations"]):
        FichePreparation.objects.create(version=version, ordre=ordre, type=p["type"], libelle=p["libelle"],
                                        quantite=p.get("quantite") or 1, piece_id=p.get("piece"))
    for ordre, e in enumerate(contenu["etapes"]):
        FicheEtape.objects.create(version=version, ordre=ordre, texte=e["texte"], attention=e.get("attention", ""))
    for ordre, ligne in enumerate(contenu["lignes"]):
        champs = {"order": ordre, "label": ligne["label"], "field_type": ligne["field_type"], "unit": ligne.get("unit", ""),
                  "required": ligne.get("required", False), "valeur_min": ligne.get("valeur_min"),
                  "valeur_max": ligne.get("valeur_max")}
        cle = ligne.get("cle")
        if cle in ancien:
            ChecklistItemTemplate.objects.filter(pk=ancien[cle].pk).update(**champs)
            gardees.add(cle)
        else:
            extra = {"cle": cle} if cle else {}
            ChecklistItemTemplate.objects.create(template=version, **champs, **extra)
    ChecklistItemTemplate.objects.filter(pk__in=[i.pk for c, i in ancien.items() if c not in gardees]).delete()


@transaction.atomic
def creer_version(fiche, contenu, auteur=None, **champs):
    """Nouvelle version de la fiche (numéro suivant) avec ce contenu ; les lignes qui portent une `cle` gardent
    leur identité d'une version à l'autre."""
    numero = (fiche.versions.order_by("-numero").values_list("numero", flat=True).first() or 0) + 1
    version = ChecklistTemplate(fiche=fiche, numero=numero, sector_id=fiche.installation.sector_id, redacteur=auteur,
                                name=contenu["name"], **champs)
    version.save()
    _ecrire_contenu(version, contenu)
    return version


@transaction.atomic
def remplacer_contenu(version, contenu):
    """Le rédacteur corrige sa version renvoyée : même version, nouveau contenu."""
    _ecrire_contenu(version, contenu)


@transaction.atomic
def appliquer_a_la_fiche(version):
    """À la validation : la fiche prend le déclenchement, la durée et l'effectif de la version validée."""
    fiche = version.fiche
    fiche.title, fiche.description = version.name, version.description
    fiche.mode_declenchement, fiche.intervalle = version.mode_declenchement, version.intervalle
    fiche.unite_intervalle, fiche.seuil_heures = version.unite_intervalle, version.seuil_heures
    fiche.planned_duration_min, fiche.people_count = version.duree_estimee_min, version.nb_personnes
    fiche.periodicity = gamme_de(version)
    fiche.save()


def contenu_initial():
    """Contenu vide d'une nouvelle fiche, prêt à être rempli par l'assistant."""
    return {
        "name": "", "description": "", "resume_modifications": "", "mode_declenchement": ModeDeclenchement.CALENDRIER,
        "intervalle": None, "unite_intervalle": "M", "seuil_heures": None, "duree_estimee_min": 0, "nb_personnes": 1,
        "qualification": None, "preparations": [], "etapes": [], "lignes": [],
    }


@transaction.atomic
def enregistrer_version_directe(fiche, auteur, motif):
    """Modification directe de la fiche (voie historique du chef de service) : elle devient une
    nouvelle version validée, le contenu de la précédente étant conservé."""
    precedente = fiche.version_validee
    contenu = contenu_de(precedente) if precedente else contenu_initial()
    modifie = dict(
        name=fiche.title, description=fiche.description, mode_declenchement=fiche.mode_declenchement,
        intervalle=fiche.intervalle, unite_intervalle=fiche.unite_intervalle, seuil_heures=fiche.seuil_heures,
        duree_estimee_min=fiche.planned_duration_min, nb_personnes=fiche.people_count)
    if precedente and all(contenu[c] == v for c, v in modifie.items()):
        return None
    contenu.update(modifie, resume_modifications=motif)
    return creer_version(fiche, contenu, auteur, etat=ChecklistTemplate.Etat.VALIDEE, valide_le=timezone.now())
