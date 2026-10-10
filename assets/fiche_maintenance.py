"""Fiches de maintenance : le calendrier dit QUAND, la fiche dit COMMENT.

Une fiche = une gamme (calendaire ou heures de marche). Ses versions sont des
ChecklistTemplate ; la fiche reflète la version validée, c'est elle qui alimente
le moteur d'échéances existant (generate_installation_occurrences).
"""
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog

from .models import (
    ChecklistItemTemplate, ChecklistTemplate, EvenementProposition, FicheEtape, FichePreparation, InstallationMaintenance,
    ModeDeclenchement,
)
from .proposition_article import ErreurCircuit
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
    """Gamme de la version ; une fiche sans déclenchement structuré garde sa périodicité saisie."""
    gamme = libelle_gamme(version.mode_declenchement, version.intervalle, version.unite_intervalle, version.seuil_heures)
    periodicite = version.fiche.periodicity.strip() if version.fiche_id else ""
    return gamme if gamme != "—" or periodicite in ("", "—") else periodicite


def gammes_des_fiches(fiches, sauf=None):
    """Gammes déjà couvertes par ces fiches (version en cours ou validée)."""
    prises = set()
    for fiche in fiches.exclude(pk=getattr(sauf, "pk", None)).prefetch_related("versions"):
        version = fiche.version_en_cours or fiche.version_validee
        prises.add((gamme_de(version) if version else fiche.periodicity).strip().lower())
    return prises


def gammes_prises(installation, sauf=None):
    """Gammes déjà couvertes par une fiche de l'installation."""
    return gammes_des_fiches(installation.maintenances.all(), sauf)


JOURS_PAR_UNITE = {"J": 1, "S": 7, "M": 30, "A": 365}


def jours_de_gamme(fiche):
    """Périodicité calendaire de la fiche en jours (90 jours par défaut, comme un plan de matériel)."""
    return (fiche.intervalle or 0) * JOURS_PAR_UNITE.get(fiche.unite_intervalle, 0) or 90


MAX_LIGNES = 200
MAX_ENTIER = {"intervalle": 10000, "seuil_heures": 1_000_000, "duree_estimee_min": 100_000, "nb_personnes": 1000}


def verifier_contenu(contenu, installation, fiche=None):
    """Refuse un contenu forgé ou incohérent (message clair, jamais d'erreur serveur)."""
    from logistics.models import StockPiece
    from training.models import TrainingCourse

    if len(contenu["name"]) > 255:
        raise ErreurCircuit("Le titre est limité à 255 caractères.")
    for champ, maximum in MAX_ENTIER.items():
        if contenu[champ] is not None and not (1 if champ == "nb_personnes" else 0) <= contenu[champ] <= maximum:
            raise ErreurCircuit(f"La valeur de « {champ.replace('_', ' ')} » est hors limites (maximum {maximum}).")
    if contenu["unite_intervalle"] not in (None, *UNITES):
        raise ErreurCircuit("Unité de périodicité inconnue.")
    if contenu["qualification"] is not None and not TrainingCourse.objects.filter(pk=contenu["qualification"]).exists():
        raise ErreurCircuit("Qualification inconnue.")
    if max(len(contenu["preparations"]), len(contenu["etapes"]), len(contenu["lignes"])) > MAX_LIGNES:
        raise ErreurCircuit(f"Trop de lignes : {MAX_LIGNES} au maximum par rubrique.")
    pieces = {p["piece"] for p in contenu["preparations"] if p.get("piece") is not None}
    if pieces and (installation is None
                   or StockPiece.objects.filter(pk__in=pieces, ship_id=installation.ship_id).count() != len(pieces)):
        raise ErreurCircuit("Pièce inconnue ou n'appartenant pas au stock de ce bâtiment : une fiche flotte n'en désigne aucune.")
    if any(len(p["libelle"]) > 255 or not 1 <= p["quantite"] <= 100_000 for p in contenu["preparations"]):
        raise ErreurCircuit("Une ligne de préparation est trop longue ou sa quantité est hors limites.")
    connues = set(ChecklistItemTemplate.objects.filter(template__fiche=fiche).values_list("cle", flat=True)) if fiche else set()
    vues = set()
    for ligne in contenu["lignes"]:
        if len(ligne["label"]) > 255 or len(ligne.get("unit", "")) > 50:
            raise ErreurCircuit("Un libellé (255 caractères) ou une unité (50 caractères) est trop long.")
        if ligne.get("cle") and (ligne["cle"] not in connues or ligne["cle"] in vues):
            raise ErreurCircuit("Identifiant de ligne inconnu ou en double : rechargez l'assistant.")
        vues.add(ligne.get("cle"))
        mini, maxi = ligne.get("valeur_min"), ligne.get("valeur_max")
        if mini is not None and maxi is not None and mini > maxi:
            raise ErreurCircuit(f"« {ligne['label']} » : le minimum dépasse le maximum.")


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
    secteur = fiche.installation.sector_id if fiche.installation_id else None
    version = ChecklistTemplate(fiche=fiche, numero=numero, sector_id=secteur, redacteur=auteur,
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
    nouvelle version validée, le contenu de la précédente étant conservé. Refusée tant qu'une
    version est en circuit ; None si rien ne change."""
    fiche = InstallationMaintenance.objects.select_for_update().get(pk=fiche.pk)
    precedente = fiche.version_validee
    contenu = contenu_de(precedente) if precedente else contenu_initial()
    modifie = dict(
        name=fiche.title, description=fiche.description, mode_declenchement=fiche.mode_declenchement,
        intervalle=fiche.intervalle, unite_intervalle=fiche.unite_intervalle, seuil_heures=fiche.seuil_heures,
        duree_estimee_min=fiche.planned_duration_min, nb_personnes=fiche.people_count)
    if precedente and all(contenu[c] == v for c, v in modifie.items()):
        return None
    if fiche.version_en_cours:
        raise ErreurCircuit("Une version de cette fiche est en cours de validation : attendez son issue avant de modifier directement.")
    gamme = libelle_gamme(fiche.mode_declenchement, fiche.intervalle, fiche.unite_intervalle, fiche.seuil_heures)
    if gamme == "—":
        gamme = fiche.periodicity.strip()
    # Une gamme déjà dupliquée avant ce contrôle ne bloque pas une modification qui ne la change pas.
    ancienne = gamme_de(precedente).strip() if precedente else None
    if gamme not in ("", "—") and gamme != ancienne and gamme.lower() in gammes_prises(fiche.installation, sauf=fiche):
        raise ErreurCircuit(f"Une fiche existe déjà pour la gamme « {gamme} » sur cette installation.")
    contenu.update(modifie, resume_modifications=motif)
    version = creer_version(fiche, contenu, auteur, etat=ChecklistTemplate.Etat.VALIDEE, valide_le=timezone.now())
    EvenementProposition.objects.create(version=version, action=EvenementProposition.Action.PUBLIEE, user=auteur, motif=motif)
    AuditLog.objects.create(actor=auteur, action="fiche.version.directe", details=f"« {version.name} » v{version.numero} ({version.pk}); {motif}")
    return version
