"""Indicateurs chiffrés de maintenance et de correctif de l'accueil, dans le périmètre de l'utilisateur.

Remplacent les graphiques décoratifs : chaque chiffre mène au dossier filtré correspondant et se calcule
avec les mêmes périmètres que les listes (aucun chiffre sans dossier derrière)."""
from django.db.models import Count, Q
from django.urls import reverse

from logistics.models import CorrectiveTicket, STATUTS_TICKET_OUVERTS
from logistics.perimetre import perimetre_tickets_q
from maintenance.models import MaintenanceOccurrence
from maintenance.perimetre import A_VENIR_JOURS, a_venir_q, perimetre_occurrences_q, retard_q


def indicateurs_maintenance(user, jour):
    """Quatre compteurs d'occurrences de maintenance et le nombre de tickets correctifs ouverts."""
    occurrences = MaintenanceOccurrence.objects.filter(perimetre_occurrences_q(user))
    chiffres = occurrences.aggregate(
        retard=Count("pk", filter=retard_q(jour)),
        a_venir=Count("pk", filter=a_venir_q(jour)),
        en_validation=Count("pk", filter=Q(status="WAITING_VALIDATION")),
    )
    tickets = CorrectiveTicket.objects.filter(perimetre_tickets_q(user), status__in=STATUTS_TICKET_OUVERTS).count()
    liste = reverse("maintenance-occurrences")
    return [
        {"libelle": "En retard", "valeur": chiffres["retard"], "etat": "danger" if chiffres["retard"] else "ok",
         "url": f"{liste}?retard=1"},
        {"libelle": f"À venir ({A_VENIR_JOURS} jours)", "valeur": chiffres["a_venir"], "etat": "", "url": f"{liste}?a_venir=1"},
        {"libelle": "En attente de validation", "valeur": chiffres["en_validation"],
         "etat": "attention" if chiffres["en_validation"] else "ok", "url": f"{liste}?statut=WAITING_VALIDATION"},
        {"libelle": "Tickets correctifs ouverts", "valeur": tickets, "etat": "attention" if tickets else "ok",
         "url": reverse("ticket-list")},
    ]
