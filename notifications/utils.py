"""Fonctions utilitaires pures partagées par les commandes de notification et
de génération d'occurrences des installations fixes (aucune dépendance aux
modèles Django : pas de risque d'import circulaire entre apps)."""
from calendar import monthrange
from datetime import date, timedelta


def add_interval(base_date: date, unite: str, intervalle: int) -> date:
    """Calcule la prochaine échéance calendaire à partir d'une date de base.

    - "J" : jours, "S" : semaines, "M" : mois, "A" : années (arithmétique
      calendaire, en bornant le jour au dernier jour du mois cible).
    """
    if unite == "J":
        return base_date + timedelta(days=intervalle)
    if unite == "S":
        return base_date + timedelta(weeks=intervalle)
    # Mois ou années : arithmétique calendaire (même logique que la branche isolement existante)
    months = intervalle if unite == "M" else intervalle * 12
    y = base_date.year + (base_date.month - 1 + months) // 12
    m = (base_date.month - 1 + months) % 12 + 1
    d = min(base_date.day, monthrange(y, m)[1])
    return date(y, m, d)


def human_delta(days: int) -> str:
    """Formule lisible d'un écart en jours par rapport à aujourd'hui, pour
    les messages de notification d'échéance."""
    if days == 0:
        return "aujourd’hui"
    if days > 0:
        return f"dans {days} j"
    return f"depuis {-days} j"
