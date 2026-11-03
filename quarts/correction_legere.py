"""Une correction d'en-tête garde les visas seulement si elle ne change ni le sens ni une information opérationnelle.

Règle structurelle, sans seuil de similarité : seuls passent la casse, la ponctuation, les espaces et la coquille d'un mot
(un caractère de différence, mot d'au moins 4 lettres). Tout ajout, retrait, nombre, heure, date, négation ou
restriction modifiés, et tout remplacement de mot par un autre mot, imposent une nouvelle validation."""
import re
import unicodedata
from difflib import SequenceMatcher

# Mots qui portent le sens d'une consigne : jamais corrigés « à la volée ».
MOTS_SENSIBLES = frozenset({
    "non", "pas", "sans", "ni", "ne", "aucun", "aucune", "jamais", "plus", "moins", "tous", "tout", "toute", "toutes",
    "seul", "seule", "seuls", "seulement", "sauf", "interdit", "interdite", "autorise", "autorisee", "obligatoire",
    "avant", "apres", "debut", "fin", "mer", "quai",
})
CORRECTIONS_MAX = 3


def _mots(texte):
    sans_accent = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", sans_accent.lower())


def _distance(a, b):
    """Distance de Levenshtein (mots courts)."""
    precedente = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        courante = [i]
        for j, cb in enumerate(b, start=1):
            courante.append(min(precedente[j] + 1, courante[j - 1] + 1, precedente[j - 1] + (ca != cb)))
        precedente = courante
    return precedente[-1]


def _coquille(a, b):
    if a in MOTS_SENSIBLES or b in MOTS_SENSIBLES or any(c.isdigit() for c in a + b):
        return False
    return len(a) >= 4 and len(b) >= 4 and _distance(a, b) == 1


def correction_legere(avant, apres):
    """(True, "") si la correction est légère ; sinon (False, raison) : une nouvelle validation est requise."""
    mots_avant, mots_apres = _mots(avant), _mots(apres)
    if not mots_avant:
        return (not mots_apres), "une information est ajoutée à une rubrique vide"
    if mots_avant == mots_apres:
        return True, ""
    corrections = 0
    for operation, i1, i2, j1, j2 in SequenceMatcher(None, mots_avant, mots_apres, autojunk=False).get_opcodes():
        if operation == "equal":
            continue
        if operation != "replace" or i2 - i1 != j2 - j1:
            return False, "un mot est ajouté ou retiré"
        for a, b in zip(mots_avant[i1:i2], mots_apres[j1:j2]):
            if not _coquille(a, b):
                return False, f"« {a} » devient « {b} » : ce n'est pas une simple coquille"
            corrections += 1
    if corrections > CORRECTIONS_MAX:
        return False, "trop de mots corrigés pour une simple coquille"
    return True, ""
