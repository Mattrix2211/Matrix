"""Lecture, contrôle et résumé de la saisie d'un compte rendu de maintenance.

Format enregistré dans MaintenanceExecution :
- results[libellé] = {"etat": conforme | non_conforme | sans_objet, "commentaire": ...} pour une case à cocher,
  ou le texte saisi pour un champ texte ou date ;
- measurements[libellé] = nombre pour un relevé numérique.
"""
ETATS = (("conforme", "Conforme"), ("non_conforme", "Non conforme"), ("sans_objet", "Sans objet"))
_CLES_ETATS = {cle for cle, _ in ETATS}


def lire_nombre(texte):
    """Nombre saisi avec virgule ou point ; None si vide ; ValueError si illisible."""
    brut = (texte or "").strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    return float(brut) if brut else None


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
        brut = (donnees.get(f"item_{it.id}") or "").strip()
        if it.field_type == "checkbox":
            etat = brut if brut in _CLES_ETATS else ("conforme" if brut == "on" else "")
            if etat:
                commentaire = (donnees.get(f"commentaire_{it.id}") or "").strip() if etat == "non_conforme" else ""
                results[it.label] = {"etat": etat, "commentaire": commentaire}
                continue
        elif it.field_type == "number":
            try:
                valeur = lire_nombre(brut)
            except ValueError:
                erreurs.append(f"« {it.label} » : valeur numérique illisible.")
                continue
            if valeur is not None:
                mesures[it.label] = valeur
                continue
        elif brut:
            results[it.label] = brut
            continue
        if it.required and exiger_complet:
            erreurs.append(f"« {it.label} » : à renseigner.")
    return results, mesures, erreurs


def lignes_de_saisie(items, results, mesures):
    """Lignes à afficher, dans l'ordre de la fiche papier, pré-remplies par la saisie enregistrée."""
    lignes = []
    for it in items:
        ligne = {"item": it, "etat": "", "commentaire": "", "valeur": "", "hors_plage": False}
        enregistre = results.get(it.label)
        if it.field_type == "checkbox":
            if isinstance(enregistre, dict):
                ligne["etat"] = enregistre.get("etat", "")
                ligne["commentaire"] = enregistre.get("commentaire", "")
        elif it.field_type == "number":
            valeur = mesures.get(it.label)
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
    faits = sum(1 for it in controles if isinstance(results.get(it.label), dict))
    non_conformes = sum(
        1 for it in controles if isinstance(results.get(it.label), dict) and results[it.label]["etat"] == "non_conforme"
    )
    a_surveiller = sum(1 for it in items if it.field_type == "number" and hors_plage(it, mesures.get(it.label)))
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
