"""Détection de dérive sur les relevés techniques d'une installation, par
régression linéaire simple (moindres carrés, sans machine learning ni
bibliothèque externe). Fonctions pures, sans dépendance aux modèles Django :
réutilisables par n'importe quelle commande ou tâche Celery sans risque
d'import circulaire (même principe que notifications/utils.py)."""
from datetime import date
from typing import List, Optional, Tuple

# Fenêtre de relevés utilisée pour la tendance : les plus anciens au-delà de
# ce nombre sont ignorés (on privilégie le rythme récent), et en dessous du
# minimum le calcul n'est pas jugé assez fiable pour déclencher une alerte.
NOMBRE_RELEVES_MIN = 3
NOMBRE_RELEVES_MAX = 10


def regression_lineaire_simple(points: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    """Calcule la pente et l'ordonnée à l'origine (méthode des moindres carrés)
    de la droite y = pente * x + origine ajustée sur une série de points (x, y).

    Renvoie None si le calcul n'est pas possible (moins de 2 points, ou tous
    les x identiques - la droite serait verticale, la pente indéfinie).
    """
    n = len(points)
    if n < 2:
        return None
    somme_x = sum(x for x, _ in points)
    somme_y = sum(y for _, y in points)
    somme_xy = sum(x * y for x, y in points)
    somme_x2 = sum(x * x for x, _ in points)
    denominateur = n * somme_x2 - somme_x ** 2
    if denominateur == 0:
        return None
    pente = (n * somme_xy - somme_x * somme_y) / denominateur
    origine = (somme_y - pente * somme_x) / n
    return pente, origine


def jours_avant_franchissement_seuil(
    releves: List[Tuple[date, float]], seuil: float, sens: str,
) -> Optional[int]:
    """Estime, par régression linéaire simple sur les derniers relevés d'une
    installation, le nombre de jours restant avant le franchissement d'un
    seuil - pour remonter une alerte AVANT le dépassement effectif.

    - releves : relevés (date, valeur), dans un ordre quelconque. Seuls les
      NOMBRE_RELEVES_MAX plus récents sont conservés, et au moins
      NOMBRE_RELEVES_MIN relevés sont nécessaires pour un calcul jugé fiable.
    - seuil : valeur du seuil de danger à ne pas franchir.
    - sens : "BAISSE" si la dégradation correspond à une valeur qui diminue
      vers le seuil (ex: isolement en Ohms), "HAUSSE" si elle correspond à
      une valeur qui augmente vers le seuil (ex: heures de marche cumulées
      par rapport au seuil d'entretien compteur).

    Renvoie le nombre de jours entiers avant franchissement estimé, ou None
    si :
    - il n'y a pas assez de relevés pour un calcul fiable,
    - le seuil est déjà franchi (dépassement avéré, ce n'est plus une dérive
      à anticiper mais un dépassement déjà traité ailleurs),
    - la tendance ne va pas dans le sens d'une dégradation (valeurs stables ou
      qui s'améliorent) : aucune alerte à remonter.
    """
    if sens not in ("BAISSE", "HAUSSE"):
        raise ValueError("sens doit être 'BAISSE' ou 'HAUSSE'")

    releves_tries = sorted(releves, key=lambda r: r[0])[-NOMBRE_RELEVES_MAX:]
    if len(releves_tries) < NOMBRE_RELEVES_MIN:
        return None

    date_reference = releves_tries[0][0]
    points = [((d - date_reference).days, float(v)) for d, v in releves_tries]
    resultat = regression_lineaire_simple(points)
    if resultat is None:
        return None
    pente, origine = resultat

    derniere_valeur = releves_tries[-1][1]
    dernier_x = points[-1][0]

    if sens == "BAISSE":
        if derniere_valeur <= seuil or pente >= 0:
            return None
    else:
        if derniere_valeur >= seuil or pente <= 0:
            return None

    x_seuil = (seuil - origine) / pente
    jours = round(x_seuil - dernier_x)
    if jours <= 0:
        return None
    return jours
