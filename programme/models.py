"""Programme du bâtiment : escales, arrêts techniques, exercices, réunions, ciblés par périmètre.

Les types sont propres à chaque navire et configurables ; l'état-major saisit et peut déléguer ce droit.
"""
from django.conf import settings
from django.db import models

from matrix.core.models import OwnedModel, TimeStampedModel
from org.models import Section, Sector, Service, Ship
from taches.models import Tache


class TypeProgramme(TimeStampedModel):
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="types_programme")
    nom = models.CharField(max_length=60, verbose_name="Nom")
    couleur = models.CharField(max_length=7, default="#0d6efd", verbose_name="Couleur")
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("nom",)
        unique_together = ("ship", "nom")

    def __str__(self):
        return self.nom


class EvenementProgramme(TimeStampedModel, OwnedModel):
    titre = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    type = models.ForeignKey(TypeProgramme, on_delete=models.PROTECT, related_name="evenements")
    debut = models.DateTimeField(verbose_name="Début")
    fin = models.DateTimeField(null=True, blank=True, verbose_name="Fin")
    lieu = models.CharField(max_length=120, blank=True, default="", verbose_name="Lieu")
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="evenements_programme")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name="evenements_programme")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.CASCADE, related_name="evenements_programme")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.CASCADE, related_name="evenements_programme")
    equipage = models.CharField(max_length=8, blank=True, default="", verbose_name="Équipage")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="evenements_programme")
    annule = models.BooleanField(default=False)
    taches = models.ManyToManyField(Tache, blank=True, related_name="evenements_programme")

    class Meta:
        ordering = ("debut",)

    def __str__(self):
        return self.titre

    @property
    def cible_libelle(self):
        noeud = self.section or self.sector or self.service or self.ship
        return f"{noeud}" + (f" · équipage {self.equipage}" if self.equipage else "")


class DelegationProgramme(TimeStampedModel):
    """Droit de saisir le programme, confié par l'état-major à un marin du bâtiment (dans son propre périmètre)."""
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="delegations_programme")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="delegations_programme")
    accordee_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        unique_together = ("ship", "user")
