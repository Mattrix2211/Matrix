"""Historique d'un équipement tiré des comptes rendus : frise chronologique et séries de relevés par ligne de fiche.

Tout vient des comptes rendus saisis (préventifs et correctifs) : aucune ressaisie. Une série suit la `cle` de la
ligne, stable d'une version de fiche à l'autre ; le dernier état d'une valeur corrigée par un chef est celui
des séries, la saisie d'origine du marin restant affichée à côté.
"""
from datetime import datetime

from django.urls import reverse
from django.utils import timezone

from assets.fiche_maintenance import gamme_de
from assets.trend import jours_avant_franchissement_seuil
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level

from .compte_rendu import ETATS, lignes_de_saisie, resume, valeur_de
from .models import CompteRenduCorrectif, MaintenanceExecution

LIBELLES_CONFORMITE = dict(MaintenanceExecution.CONFORMITY)
LIBELLES_ETATS = dict(ETATS)
GAMME_CORRECTIF = "Intervention corrective"
ETATS_BADGE = {"CONFORME": "ok", "A_SURVEILLER": "attention", "NON_CONFORME": "danger"}
TENDANCES = {"hausse": ("↗", "en hausse"), "baisse": ("↘", "en baisse"), "stable": ("→", "stable")}


def sources_de(installation=None, asset=None, exclure_execution=None):
    """Comptes rendus terminés de l'équipement (préventifs puis correctifs), du plus ancien au plus récent."""
    preventifs = MaintenanceExecution.objects.filter(completed_at__isnull=False).select_related(
        "occurrence__plan", "occurrence__installation_maintenance", "version_fiche__fiche", "executed_by",
    ).prefetch_related("intervenants", "version_fiche__items", "modifications__auteur", "occurrence__assignees")
    correctifs = CompteRenduCorrectif.objects.filter(completed_at__isnull=False).select_related(
        "ticket", "version_fiche__fiche", "executed_by",
    ).prefetch_related("intervenants", "version_fiche__items", "modifications__auteur", "ticket__assignees")
    if installation is not None:
        preventifs = preventifs.filter(occurrence__installation_maintenance__installation=installation)
        correctifs = correctifs.filter(ticket__installation=installation)
    else:
        preventifs = preventifs.filter(occurrence__asset=asset)
        correctifs = correctifs.filter(ticket__asset=asset)
    if exclure_execution is not None:
        preventifs = preventifs.exclude(pk=exclure_execution)
    return sorted([*preventifs, *correctifs], key=lambda s: (s.completed_at, s.pk if isinstance(s, MaintenanceExecution) else 0))


def formater_duree(minutes):
    """« 1 h 20 » ou « 45 min »."""
    heures, reste = divmod(int(minutes), 60)
    if not heures:
        return f"{reste} min"
    return f"{heures} h {reste:02d}" if reste else f"{heures} h"


def _items(version):
    """Lignes de la version, dans l'ordre de la fiche (déjà préchargées)."""
    return sorted(version.items.all(), key=lambda i: (i.order, i.pk)) if version else []


def _est_correctif(source):
    return isinstance(source, CompteRenduCorrectif)


def duree_estimee(occ, version):
    """Durée estimée en minutes d'une occurrence : celle de la version de fiche, à défaut celle de la fiche ou du plan."""
    fiche = occ.installation_maintenance
    if fiche is not None:
        return version.duree_estimee_min if version and version.duree_estimee_min else fiche.planned_duration_min
    return occ.plan.expected_duration_min


def _gamme_et_titre(source):
    """(gamme, titre, estimé en minutes) de l'intervention."""
    version = source.version_fiche
    if _est_correctif(source):
        return (gamme_de(version) if version and version.fiche_id else GAMME_CORRECTIF), "Intervention corrective", \
            source.duree_estimee_min or (version.duree_estimee_min if version else 0)
    occ = source.occurrence
    fiche = occ.installation_maintenance
    if fiche is not None:
        gamme = gamme_de(version) if version and version.fiche_id else fiche.periodicity
        return gamme, fiche.title, duree_estimee(occ, version)
    return occ.plan.name, occ.plan.name, duree_estimee(occ, version)


def _texte(valeur):
    """Valeur enregistrée, lisible : « Non conforme (motif) », « 4,2 » ou le texte saisi."""
    if isinstance(valeur, dict):
        texte = LIBELLES_ETATS.get(valeur.get("etat"), "")
        return f"{texte} ({valeur['commentaire']})" if valeur.get("commentaire") else texte
    if isinstance(valeur, float):
        return f"{valeur:g}".replace(".", ",")
    return "—" if valeur in (None, "") else LIBELLES_CONFORMITE.get(valeur, str(valeur))


def _lignes_lisibles(items, results, mesures):
    """Lignes renseignées d'un compte rendu, avec leur état (non-conformité, hors plage)."""
    lignes = []
    for ligne in lignes_de_saisie(items, results, mesures):
        it = ligne["item"]
        if not (ligne["etat"] or ligne["valeur"]):
            continue
        lignes.append({
            "libelle": it.label, "unite": it.unit if it.field_type == "number" else "",
            "etat": ligne["etat"], "etat_libelle": LIBELLES_ETATS.get(ligne["etat"], ""),
            "commentaire": ligne["commentaire"], "valeur": ligne["valeur"], "hors_plage": ligne["hors_plage"],
            "non_conforme": ligne["etat"] == "non_conforme",
        })
    return lignes


def _modifications(source):
    """Corrections du compte rendu : qui, quand, motif, valeurs avant et après."""
    return [{
        "auteur": m.auteur, "date": m.created_at, "motif": m.motif,
        "changements": [{"libelle": libelle, "avant": _texte(c.get("avant")), "apres": _texte(c.get("apres"))}
                        for libelle, c in m.modifications.items()],
    } for m in source.modifications.all()]


def _origine(source, items):
    """Saisie d'origine du marin, si un chef a corrigé le compte rendu depuis."""
    origine = source.saisie_origine
    if not origine or not source.modifications.all():
        return None
    return {
        "par": origine.get("par_nom", ""), "le": datetime.fromisoformat(origine["le"]) if origine.get("le") else None,
        "conformite": LIBELLES_CONFORMITE.get(origine.get("conformite"), ""), "notes": origine.get("notes", ""),
        "textes": [(libelle, texte) for libelle, texte in origine.get("textes", {}).items() if texte],
        "lignes": _lignes_lisibles(items, origine.get("results", {}), origine.get("measurements", {})),
    }


def _lien(source, user, seuil):
    """Adresse du compte rendu, si l'utilisateur peut l'ouvrir (assigné ou chef)."""
    if _est_correctif(source):
        obj, nom, cible = source.ticket, "correctif-compte-rendu", source.ticket_id
    else:
        obj, nom, cible = source.occurrence, "occurrence-execute", source.occurrence_id
    if user_role_level(user) >= seuil or user in obj.assignees.all():
        return reverse(nom, args=[cible])
    return ""


def entree(source, user, seuil):
    """Une entrée de la frise : date, gamme, version de fiche, intervenants, résultat de chaque ligne, conformité."""
    version = source.version_fiche
    items = _items(version)
    gamme, titre, estime = _gamme_et_titre(source)
    lignes = _lignes_lisibles(items, source.results, source.measurements)
    synthese = resume(items, source.results, source.measurements)
    duree = None
    if source.started_at and source.completed_at and source.completed_at >= source.started_at:
        duree = int((source.completed_at - source.started_at).total_seconds() // 60)
    a_surveiller = bool(synthese["a_surveiller"])
    donnees = {
        "correctif": _est_correctif(source), "date": source.completed_at, "titre": titre, "gamme": gamme,
        "version": f"v{version.numero}" if version and version.fiche_id else "",
        "intervenants": [u.get_full_name() or u.username for u in source.intervenants.all()],
        "conformite": source.conformity, "etat_badge": ETATS_BADGE.get(source.conformity, "neutre"), "conformite_libelle": LIBELLES_CONFORMITE.get(source.conformity, ""),
        "lignes": lignes, "resume": synthese["texte"], "a_surveiller": a_surveiller,
        "attention": source.conformity != "CONFORME" or a_surveiller,
        "notes": source.notes,
        "duree": formater_duree(duree) if duree is not None else "",
        "estime": formater_duree(estime) if estime else "",
        "depassement": duree is not None and bool(estime) and duree > estime,
        "modifications": _modifications(source), "origine": _origine(source, items),
        "lien": _lien(source, user, seuil),
    }
    if _est_correctif(source):
        donnees.update(constat=source.constat, diagnostic=source.diagnostic, action=source.action_realisee, pieces=source.pieces)
    return donnees


def gammes_de(sources):
    """Gammes présentes dans l'historique, pour filtrer."""
    return sorted({_gamme_et_titre(s)[0] for s in sources})


def frise(sources, user, gamme="", seulement_anomalies=False):
    """Entrées de la frise (la plus récente d'abord), filtrées par gamme et par anomalies."""
    seuil = niveau_requis_pour(user, "maintenance_occurrence_gestion_tiers")
    entrees = [entree(s, user, seuil) for s in reversed(sources) if not gamme or _gamme_et_titre(s)[0] == gamme]
    return [e for e in entrees if e["attention"]] if seulement_anomalies else entrees


def recents(user, installation=None, asset=None, nombre=5):
    """Les derniers comptes rendus de l'équipement, pour sa fiche."""
    return frise(sources_de(installation, asset)[-nombre:], user)


def _derive(points, mini, maxi):
    """Jours avant franchissement d'une borne de la plage, par la détection de dérive existante."""
    releves = [(p["date"], p["valeur"]) for p in points]
    jours = []
    if mini is not None:
        jours.append(jours_avant_franchissement_seuil(releves, mini, "BAISSE"))
    if maxi is not None:
        jours.append(jours_avant_franchissement_seuil(releves, maxi, "HAUSSE"))
    jours = [j for j in jours if j is not None]
    return min(jours) if jours else None


def _tendance(points):
    if len(points) < 2:
        return None
    ecart = points[-1]["valeur"] - points[-2]["valeur"]
    code = "stable" if ecart == 0 else "hausse" if ecart > 0 else "baisse"
    return {"code": code, "symbole": TENDANCES[code][0], "libelle": TENDANCES[code][1]}


def series(sources):
    """Séries de relevés par ligne de fiche (`cle`) : points, dernière valeur, tendance et dérive.

    Un point corrigé par un chef porte la valeur d'origine du marin (`origine`)."""
    par_cle = {}
    for source in sources:
        if not source.version_fiche_id:
            continue
        gamme = _gamme_et_titre(source)[0]
        origine = (source.saisie_origine or {}).get("measurements", {})
        jour = timezone.localtime(source.completed_at).date()
        for rang, it in enumerate(_items(source.version_fiche)):
            valeur = valeur_de(source.measurements, it)
            if it.field_type != "number" or not isinstance(valeur, (int, float)):
                continue
            serie = par_cle.setdefault(str(it.cle), {"cle": str(it.cle), "points": []})
            serie.update(libelle=it.label, unite=it.unit, gamme=gamme, rang=rang, mini=it.valeur_min, maxi=it.valeur_max)
            avant = valeur_de(origine, it)
            corrige = bool(source.modifications.all()) and isinstance(avant, (int, float)) and avant != valeur
            serie["points"].append({
                "date": jour, "valeur": float(valeur), "origine": float(avant) if corrige else None,
                "corrige": corrige, "hors_plage": (it.valeur_min is not None and valeur < it.valeur_min)
                or (it.valeur_max is not None and valeur > it.valeur_max),
                "correctif": _est_correctif(source),
            })
    resultat = []
    for numero, serie in enumerate(sorted(par_cle.values(), key=lambda s: (s["gamme"], s["rang"], s["libelle"]))):
        points = serie["points"]
        serie.update(
            id_donnees=f"serie-{numero}", derniere=points[-1], tendance=_tendance(points), derive_jours=_derive(points, serie["mini"], serie["maxi"]),
            donnees={
                "libelle": serie["libelle"], "unite": serie["unite"], "mini": serie["mini"], "maxi": serie["maxi"],
                "dates": [p["date"].strftime("%d/%m/%Y") for p in points], "valeurs": [p["valeur"] for p in points],
            },
        )
        resultat.append(serie)
    return resultat


def derniers_releves(items, installation=None, asset=None, exclure_execution=None):
    """{cle: série} des relevés de ces lignes, hors le compte rendu en cours : rappel de la dernière valeur."""
    cles = {str(it.cle) for it in items if it.field_type == "number"}
    if not cles:
        return {}
    return {s["cle"]: s for s in series(sources_de(installation, asset, exclure_execution)) if s["cle"] in cles}
