"""Lecture, contrôle et résumé de la saisie d'un compte rendu de maintenance.

Format enregistré dans MaintenanceExecution, indexé par la `cle` (UUID stable d'une version de fiche à l'autre) ;
les comptes rendus d'avant gardent leurs libellés, que `valeur_de` sait encore lire :
- results[cle] = {"etat": conforme | non_conforme | sans_objet, "commentaire": ...} pour une case à cocher,
  ou le texte saisi pour un champ texte ou date ;
- measurements[cle] = nombre pour un relevé numérique.
"""
import math

from matrix.core.saisie import sans_nul

ETATS = (("conforme", "Conforme"), ("non_conforme", "Non conforme"), ("sans_objet", "Sans objet"))
_CLES_ETATS = {cle for cle, _ in ETATS}
LONGUEUR_MAX = 255
LONGUEUR_NOTES = 10000
LONGUEUR_MOTIF = 1000


def lire_nombre(texte):
    """Nombre saisi avec virgule ou point ; None si vide ; ValueError si illisible ou non fini."""
    brut = (texte or "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if not brut:
        return None
    valeur = float(brut)
    if not math.isfinite(valeur):
        raise ValueError(brut)
    return valeur


def valeur_de(donnees, item):
    """Valeur enregistrée pour une ligne : par `cle`, à défaut par libellé (anciens comptes rendus)."""
    if not isinstance(donnees, dict):
        return None
    cle = str(item.cle)
    return donnees[cle] if cle in donnees else donnees.get(item.label)


def par_libelle(items, donnees):
    """Même saisie indexée par libellé de ligne, pour l'afficher ou la tracer en clair."""
    lues = {it.label: valeur_de(donnees, it) for it in items}
    return {label: valeur for label, valeur in lues.items() if valeur is not None}


ETIQUETTES_MODIFIEES = {
    "conformite": "Conformité finale", "notes": "Observations", "debut": "Début", "fin": "Fin", "intervenants": "Intervenants",
    "constat": "Constat", "diagnostic": "Diagnostic", "action": "Action réalisée",
}


def differences(avant, apres):
    """Ce qui change entre deux saisies tracées (`_etat_saisie`) : {libellé: {"avant", "apres"}}, ligne par ligne."""
    resultat = {}
    for champ, libelle in ETIQUETTES_MODIFIEES.items():
        if avant.get(champ) != apres.get(champ):
            valeurs = [", ".join(v) if isinstance(v, list) else v for v in (avant.get(champ), apres.get(champ))]
            resultat[libelle] = {"avant": valeurs[0], "apres": valeurs[1]}
    for champ in ("resultats", "releves"):
        for libelle in avant[champ].keys() | apres[champ].keys():
            if avant[champ].get(libelle) != apres[champ].get(libelle):
                resultat[libelle] = {"avant": avant[champ].get(libelle), "apres": apres[champ].get(libelle)}
    return resultat


def instantane(auteur, exec_obj):
    """Saisie du marin figée à la clôture (cles de ligne conservées), pour la retrouver après correction."""
    saisie = {
        "par": auteur.pk if auteur else None, "par_nom": (auteur.get_full_name() or auteur.username) if auteur else "",
        "le": exec_obj.completed_at.isoformat() if exec_obj.completed_at else None,
        "results": exec_obj.results, "measurements": exec_obj.measurements,
        "conformite": exec_obj.conformity, "notes": exec_obj.notes,
    }
    if hasattr(exec_obj, "constat"):
        saisie["textes"] = {"Constat": exec_obj.constat, "Diagnostic": exec_obj.diagnostic, "Action réalisée": exec_obj.action_realisee}
    return saisie


def hors_plage(item, valeur):
    """Vrai si la valeur sort de la plage attendue de la ligne (bornes facultatives)."""
    return valeur is not None and (
        (item.valeur_min is not None and valeur < item.valeur_min)
        or (item.valeur_max is not None and valeur > item.valeur_max)
    )


def lire_saisie(items, donnees, exiger_complet=True):
    """Renvoie (results, measurements, erreurs) à partir des champs du formulaire.

    exiger_complet=False (enregistrement en cours d'exécution) : les lignes obligatoires
    peuvent rester vides.
    """
    results, mesures, erreurs = {}, {}, []
    for it in items:
        brut = sans_nul(donnees.get(f"item_{it.id}") or "").strip()
        if it.field_type == "checkbox":
            etat = brut if brut in _CLES_ETATS else ("conforme" if brut == "on" else "")
            if etat:
                commentaire = sans_nul(donnees.get(f"commentaire_{it.id}") or "").strip()[:LONGUEUR_MAX] if etat == "non_conforme" else ""
                results[str(it.cle)] = {"etat": etat, "commentaire": commentaire}
                continue
        elif it.field_type == "number":
            try:
                valeur = lire_nombre(brut)
            except ValueError:
                erreurs.append(f"« {it.label} » : valeur numérique illisible.")
                continue
            if valeur is not None:
                mesures[str(it.cle)] = valeur
                continue
        elif brut:
            results[str(it.cle)] = brut[:LONGUEUR_MAX]
            continue
        if it.required and exiger_complet:
            erreurs.append(f"« {it.label} » : à renseigner.")
    return results, mesures, erreurs


def lignes_de_saisie(items, results, mesures):
    """Lignes à afficher, dans l'ordre de la fiche papier, pré-remplies par la saisie enregistrée."""
    lignes = []
    for it in items:
        ligne = {"item": it, "etat": "", "commentaire": "", "valeur": "", "hors_plage": False}
        enregistre = valeur_de(results, it)
        if it.field_type == "checkbox":
            if isinstance(enregistre, dict):
                ligne["etat"] = enregistre.get("etat", "")
                ligne["commentaire"] = enregistre.get("commentaire", "")
        elif it.field_type == "number":
            valeur = valeur_de(mesures, it)
            if valeur is not None:
                ligne["valeur"] = f"{valeur:g}".replace(".", ",")
                ligne["hors_plage"] = hors_plage(it, valeur)
        elif isinstance(enregistre, str):
            ligne["valeur"] = enregistre
        lignes.append(ligne)
    return lignes


def resume(items, results, mesures):
    """Synthèse affichée à la validation : « 12/12 contrôles, 1 relevé à surveiller »."""
    controles = [it for it in items if it.field_type == "checkbox"]
    faits = sum(1 for it in controles if isinstance(valeur_de(results, it), dict))
    non_conformes = sum(
        1 for it in controles if isinstance(valeur_de(results, it), dict) and valeur_de(results, it).get("etat") == "non_conforme"
    )
    a_surveiller = sum(1 for it in items if it.field_type == "number" and hors_plage(it, valeur_de(mesures, it)))
    parties = []
    if controles:
        parties.append(f"{faits}/{len(controles)} contrôles")
    if non_conformes:
        parties.append(f"{non_conformes} non conforme{'s' if non_conformes > 1 else ''}")
    if a_surveiller:
        parties.append(f"{a_surveiller} relevé{'s' if a_surveiller > 1 else ''} à surveiller")
    return {
        "non_conformes": non_conformes, "a_surveiller": a_surveiller,
        "texte": ", ".join(parties) or "Aucun point à contrôler",
    }
