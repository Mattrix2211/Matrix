"""Poste du bord : fonction à pourvoir, rattachée à l'organisation, avec les formations qu'elle exige.

Affecter un marin à qui il manque des qualifications reste possible : elles sont seulement signalées.
"""
from django.conf import settings
from django.db import models

from matrix.core.models import OwnedModel, TimeStampedModel
from org.models import Section, Sector, Service, Ship
from training.models import TrainingCourse


class Poste(TimeStampedModel, OwnedModel):
    intitule = models.CharField(max_length=120, verbose_name="Intitulé")
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="postes")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name="postes")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.CASCADE, related_name="postes")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.CASCADE, related_name="postes")
    equipage = models.CharField(max_length=8, blank=True, default="", verbose_name="Équipage")
    effectif = models.PositiveSmallIntegerField(default=1, verbose_name="Effectif requis")
    formations = models.ManyToManyField(TrainingCourse, blank=True, related_name="postes", verbose_name="Formations exigées")
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("intitule",)

    def __str__(self):
        return self.intitule

    @property
    def cible_libelle(self):
        noeud = self.section or self.sector or self.service or self.ship
        return f"{noeud}" + (f" · équipage {self.equipage}" if self.equipage else "")


class AffectationPoste(TimeStampedModel):
    poste = models.ForeignKey(Poste, on_delete=models.CASCADE, related_name="affectations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="affectations_poste")
    affecte_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        unique_together = ("poste", "user")
