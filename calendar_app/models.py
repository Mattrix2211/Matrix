from django.conf import settings
from django.db import models

from matrix.core.models import TimeStampedModel


class PersonalEvent(TimeStampedModel):
    """Événement personnel libre (rappel, note...) ajouté par un marin sur
    son propre calendrier. Visible uniquement par son créateur, à la
    différence des événements auto-générés (maintenance, ticket, formation)
    qui sont partagés selon le périmètre — d'où l'absence de tout champ de
    portée organisationnelle (navire/service/secteur/section)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="evenements_personnels",
    )
    title = models.CharField("Titre", max_length=200)
    starts_at = models.DateTimeField("Date et heure")
    note = models.TextField("Note", blank=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "Événement personnel"
        verbose_name_plural = "Événements personnels"

    def __str__(self):
        return f"{self.title} ({self.starts_at:%d/%m/%Y %H:%M})"
