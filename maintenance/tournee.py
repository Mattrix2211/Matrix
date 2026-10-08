"""Tournée de matériel : plusieurs équipements contrôlés d'un même passage, présentés en UN tableau
par catégorie (une ligne par équipement, une colonne par ligne de la fiche) pour l'impression
comme pour la saisie en grille. Les installations gardent leur fiche individuelle."""
import hashlib
from datetime import date

from django.urls import reverse

from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from matrix.core.saisie import date_fr_ou_none, entier_ou_none, formater_date_fr

from .compte_rendu import ETATS, lignes_de_saisie, lire_saisie, resume
from .models import MaintenanceOccurrence

STATUTS_CLOS = ("DONE", "CANCELLED")
STATUTS_VERROUILLES = STATUTS_CLOS + ("WAITING_VALIDATION",)
MAX_IDENTIFIANTS = 500
SANS_CATEGORIE = "Sans catégorie"
COLONNE_OBSERVATION = "Observation / non vu (motif)"


def identifiants(texte):
    """Identifiants lus dans « 1,2,3 », sans doublon, dans l'ordre donné, plafonnés."""
    lus = [n for n in map(entier_ou_none, (texte or "").split(",", MAX_IDENTIFIANTS)[:MAX_IDENTIFIANTS]) if n is not None]
    return list(dict.fromkeys(lus))


def verrouillee(occ, execution):
    """Vrai si la grille ne doit plus réécrire l'occurrence : en validation, close ou déjà exécutée."""
    return occ.status in STATUTS_VERROUILLES or bool(execution and execution.completed_at)


def adresse(nom_url, occurrences):
    """Adresse d'une vue de tournée pour ces occurrences."""
    return f"{reverse(nom_url)}?ids={','.join(str(o.pk) for o in occurrences)}"


def peut_ecrire(user, occ):
    """Mêmes droits que le compte rendu individuel : assigné, ou seuil de gestion des tiers."""
    return (user in occ.assignees.all()
            or user_role_level(user) >= niveau_requis_pour(user, "maintenance_occurrence_gestion_tiers"))


def categorie_de(asset):
    """Catégorie du catalogue de l'article, à défaut celle du type de matériel."""
    if asset.article_catalogue_id:
        return asset.article_catalogue.categorie.nom
    return asset.asset_type.category or SANS_CATEGORIE


def emplacement_de(asset):
    """« Pont · emplacement · local » : ce qui permet de suivre la tournée à pied."""
    parties = [asset.plan_deck.name if asset.plan_deck_id else "",
               asset.location.name if asset.location_id else "", asset.local]
    return " · ".join(p for p in parties if p)


def repere_de(asset):
    """« Repère · n° de série » : ce qui distingue deux équipements de même désignation."""
    return " · ".join(p for p in (asset.internal_id, asset.serial_number) if p)


def libelle_colonne(item):
    """Libellé d'une ligne de fiche, l'unité n'étant ajoutée que si le libellé ne la porte pas déjà."""
    if item.unit and f"({item.unit})".lower() not in item.label.lower():
        return f"{item.label} ({item.unit})"
    return item.label


def _est_observation(item):
    """Ligne de texte libre « Observation(s) » de la fiche : remplacée par la colonne unique."""
    return item.field_type == "text" and item.label.strip().lower().startswith("observation")


def _cle_tri(occ):
    """Pont (ordre du plan, ceux sans pont en dernier), emplacement, puis désignation."""
    a = occ.asset
    pont = (0, a.plan_deck.order, a.plan_deck.name) if a.plan_deck_id else (1, 0, "")
    return (a.ship.name, pont, a.location.name if a.location_id else "", a.local,
            a.designation or a.asset_type.name, str(a.pk))


def charger(user, ids):
    """Occurrences de matériel demandées, dans le périmètre de l'appelant, sans filtre de droit d'écriture."""
    return list(
        MaintenanceOccurrence.objects.select_related(
            "plan", "plan__checklist_template", "asset", "asset__asset_type", "asset__ship", "asset__location",
            "asset__plan_deck", "asset__article_catalogue", "asset__article_catalogue__categorie", "execution__version_fiche",
        ).prefetch_related("assignees")
        .filter(build_scope_q(user, "asset__"), pk__in=ids, asset__isnull=False)
    )


def groupes(occurrences):
    """Un groupe par (catégorie, modèle de fiche) : les colonnes sont les lignes de la fiche, donc
    deux modèles différents ne partagent pas de tableau. Lignes triées pont puis emplacement."""
    items_par_modele, par_cle = {}, {}
    for occ in sorted(occurrences, key=_cle_tri):
        modele = occ.version_fiche()
        modele_id = modele.pk if modele else None
        if modele_id not in items_par_modele:
            items_par_modele[modele_id] = (
                [it for it in modele.items.order_by("order", "pk") if not _est_observation(it)] if modele else [])
        groupe = par_cle.setdefault((categorie_de(occ.asset), modele.name if modele else "", modele_id or 0), {
            "categorie": categorie_de(occ.asset), "modele": modele.name if modele else "",
            "items": items_par_modele[modele_id], "occurrences": [],
        })
        groupe["occurrences"].append(occ)
    return [par_cle[cle] for cle in sorted(par_cle)]


def empreinte(ids):
    """Empreinte hexadécimale stable d'une liste d'identifiants (ordre indifférent)."""
    return hashlib.sha1(",".join(map(str, sorted(ids))).encode()).hexdigest()


def cle_brouillon(ids, rang):
    """Clé stable de brouillon : même tournée, même tableau, même brouillon."""
    return f"tournee:{empreinte(ids)[:12]}:{rang}"


def libelle_equipement(occ):
    """Libellé accessible d'une ligne : désignation, emplacement et repère."""
    a = occ.asset
    lieu = emplacement_de(a)
    return " — ".join(p for p in (a.designation or a.asset_type.name, lieu, repere_de(a)) if p)


def colonnes_grille(items):
    """Colonnes de la grille : une par ligne de fiche, puis l'observation (ou motif si non vu)."""
    colonnes = []
    for it in items:
        libelle = libelle_colonne(it)
        if it.field_type == "checkbox":
            colonnes.append({"nom": f"i{it.pk}", "libelle": libelle, "type": "conformite",
                             "choix": [{"valeur": cle, "libelle": nom} for cle, nom in ETATS]})
        elif it.field_type == "number":
            colonnes.append({"nom": f"i{it.pk}", "libelle": libelle, "type": "nombre",
                             "min": it.valeur_min, "max": it.valeur_max})
        else:
            colonnes.append({"nom": f"i{it.pk}", "libelle": libelle, "type": "date" if it.field_type == "date" else "texte"})
    colonnes.append({"nom": "observation", "libelle": COLONNE_OBSERVATION, "placeholder": "Motif si non vu", "large": True})
    return colonnes


def lire_ligne(items, donnees):
    """(results, mesures, erreurs par colonne) d'une ligne de la grille ; réutilise la lecture du compte rendu individuel."""
    brut, erreurs, results, mesures = {}, {}, {}, {}
    for it in items:
        valeur = (donnees.get(f"i{it.pk}") or "").strip()
        if it.field_type == "date" and valeur:
            try:
                valeur = date_fr_ou_none(valeur).isoformat()
            except ValueError:
                erreurs[f"i{it.pk}"] = "Date invalide : saisissez jj/mm/aaaa."
                continue
        brut[f"item_{it.pk}"] = valeur
    for it in items:
        if f"i{it.pk}" in erreurs:
            continue
        r, m, e = lire_saisie([it], brut)
        results.update(r)
        mesures.update(m)
        if e:
            erreurs[f"i{it.pk}"] = e[0].split(" : ", 1)[-1]
    return results, mesures, erreurs


def valeurs_enregistrees(items, execution):
    """Valeurs de la grille pour une ligne, pré-remplies par un compte rendu commencé en direct."""
    valeurs = {"observation": execution.notes if execution else ""}
    lignes = lignes_de_saisie(items, execution.results if execution else {}, execution.measurements if execution else {})
    for ligne in lignes:
        it = ligne["item"]
        valeur = ligne["etat"] if it.field_type == "checkbox" else ligne["valeur"]
        if it.field_type == "date" and valeur:
            try:
                valeur = formater_date_fr(date.fromisoformat(valeur))
            except ValueError:
                pass
        valeurs[f"i{it.pk}"] = valeur
    return valeurs


def conformite(items, results, mesures):
    """Conformité du compte rendu d'un équipement, déduite de ses lignes."""
    synthese = resume(items, results, mesures)
    if synthese["non_conformes"]:
        return "NON_CONFORME"
    return "A_SURVEILLER" if synthese["a_surveiller"] else "CONFORME"
