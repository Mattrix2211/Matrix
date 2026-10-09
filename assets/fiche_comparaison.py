"""Comparaison visuelle de deux versions d'une fiche : lignes, étapes et préparation ajoutées, modifiées ou supprimées."""
import difflib

from . import fiche_maintenance

LIBELLES = {"ajoutee": "Ajoutée", "modifiee": "Modifiée", "supprimee": "Supprimée", "deplacee": "Déplacée", "inchangee": "Inchangée"}
CHAMPS_LIGNE = (("label", "Point"), ("field_type", "Type"), ("unit", "Unité"), ("required", "Obligatoire"),
                ("valeur_min", "Minimum"), ("valeur_max", "Maximum"))


def _valeur(champ, valeur):
    if champ == "field_type":
        return "Relevé" if valeur == "number" else "Contrôle"
    if champ == "required":
        return "oui" if valeur else "non"
    return "—" if valeur in (None, "") else f"{valeur:g}" if isinstance(valeur, float) else str(valeur)


def _entree(statut, texte, details=()):
    return {"statut": statut, "libelle": LIBELLES[statut], "texte": texte, "details": list(details)}


def _comparer_lignes(avant, apres):
    anciennes = {i.cle: i for i in avant.items.order_by("order", "pk")}
    nouvelles = list(apres.items.order_by("order", "pk"))
    rang_avant = [c for c in anciennes if c in {i.cle for i in nouvelles}]
    rang_apres = [i.cle for i in nouvelles if i.cle in anciennes]
    resultat = []
    for item in nouvelles:
        ancien = anciennes.get(item.cle)
        if ancien is None:
            resultat.append(_entree("ajoutee", item.label))
            continue
        details = [f"{nom} : {_valeur(c, getattr(ancien, c))} → {_valeur(c, getattr(item, c))}"
                   for c, nom in CHAMPS_LIGNE if getattr(ancien, c) != getattr(item, c)]
        deplacee = rang_avant.index(item.cle) != rang_apres.index(item.cle)
        statut = "modifiee" if details else "deplacee" if deplacee else "inchangee"
        resultat.append(_entree(statut, item.label, details))
    restantes = {i.cle for i in nouvelles}
    resultat += [_entree("supprimee", i.label) for c, i in anciennes.items() if c not in restantes]
    return resultat


def _comparer_suites(avant, apres, formater):
    """Compare deux suites d'éléments (étapes, préparation) en gardant l'ordre ; un remplacement apparié est une modification."""
    resultat = []
    for operation, a1, a2, b1, b2 in difflib.SequenceMatcher(a=avant, b=apres, autojunk=False).get_opcodes():
        if operation == "equal":
            resultat += [_entree("inchangee", formater(x)) for x in apres[b1:b2]]
            continue
        anciens, nouveaux = avant[a1:a2], apres[b1:b2]
        paires = min(len(anciens), len(nouveaux))
        resultat += [_entree("modifiee", formater(n), [f"Avant : {formater(a)}"]) for a, n in zip(anciens, nouveaux)]
        resultat += [_entree("ajoutee", formater(n)) for n in nouveaux[paires:]]
        resultat += [_entree("supprimee", formater(a)) for a in anciens[paires:]]
    return resultat


def comparer(avant, apres):
    """Différences entre la version appliquée (`avant`) et la proposition (`apres`)."""
    a, b = fiche_maintenance.contenu_de(avant), fiche_maintenance.contenu_de(apres)
    champs = []
    for cle, nom in (("name", "Titre"), ("description", "Objet"), ("duree_estimee_min", "Durée estimée (min)"), ("nb_personnes", "Personnes")):
        if a[cle] != b[cle]:
            champs.append(_entree("modifiee", nom, [f"{a[cle] or '—'} → {b[cle] or '—'}"]))
    gammes = (fiche_maintenance.gamme_de(avant), fiche_maintenance.gamme_de(apres))
    if gammes[0] != gammes[1]:
        champs.append(_entree("modifiee", "Gamme", [f"{gammes[0]} → {gammes[1]}"]))
    if a["qualification"] != b["qualification"]:
        titres = [v.qualification.title if v.qualification_id else "Aucune" for v in (avant, apres)]
        champs.append(_entree("modifiee", "Qualification requise", [f"{titres[0]} → {titres[1]}"]))
    preparation = _comparer_suites(
        [(p["type"], p["libelle"], p["quantite"]) for p in a["preparations"]],
        [(p["type"], p["libelle"], p["quantite"]) for p in b["preparations"]], lambda p: f"{p[1]} × {p[2]}")
    etapes = _comparer_suites(
        [(e["texte"], e["attention"]) for e in a["etapes"]], [(e["texte"], e["attention"]) for e in b["etapes"]],
        lambda e: e[0] + (f" (Attention : {e[1]})" if e[1] else ""))
    lignes = _comparer_lignes(avant, apres)
    sections = [("Informations générales", champs), ("Préparation", preparation), ("Méthodologie", etapes), ("Contrôles et relevés", lignes)]
    total = sum(1 for _, liste in sections for e in liste if e["statut"] != "inchangee")
    return {"sections": sections, "total": total}
