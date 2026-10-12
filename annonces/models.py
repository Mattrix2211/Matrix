"""Annonce : diffusion descendante ciblée par périmètre (bâtiment, service, secteur, section, équipage).

Chaque modification crée une version conservée ; la lecture ou l'accusé de chaque marin est tracé.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from matrix.core.models import OwnedModel, TimeStampedModel
from notifications.models import NotificationLevel
from org.models import Section, Sector, Service, Ship


class Annonce(TimeStampedModel, OwnedModel):
    titre = models.CharField(max_length=200, verbose_name="Titre")
    corps = models.TextField(verbose_name="Message")
    niveau = models.CharField(max_length=10, choices=NotificationLevel.choices, default=NotificationLevel.INFO, verbose_name="Niveau")
    accuse_requis = models.BooleanField(default=False, verbose_name="Accusé de lecture requis")
    date_effet = models.DateField(default=timezone.localdate, verbose_name="Visible à partir du")
    date_fin = models.DateField(null=True, blank=True, verbose_name="Visible jusqu'au")
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="annonces", verbose_name="Bâtiment")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name="annonces")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.CASCADE, related_name="annonces")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.CASCADE, related_name="annonces")
    equipage = models.CharField(max_length=8, blank=True, default="", verbose_name="Équipage")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="annonces_publiees")
    version = models.PositiveIntegerField(default=1)
    archivee = models.BooleanField(default=False)
    diffusee_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-date_effet", "-created_at")

    def __str__(self):
        return self.titre

    def active_au(self, jour):
        return not self.archivee and self.date_effet <= jour and (self.date_fin is None or self.date_fin >= jour)

    @property
    def cible_libelle(self):
        noeud = self.section or self.sector or self.service or self.ship
        equipage = f" · équipage {self.equipage}" if self.equipage else ""
        return f"{noeud}{equipage}"


class VersionAnnonce(TimeStampedModel):
    annonce = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="versions")
    numero = models.PositiveIntegerField()
    titre = models.CharField(max_length=200)
    corps = models.TextField()
    niveau = models.CharField(max_length=10, choices=NotificationLevel.choices)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("-numero",)
        unique_together = ("annonce", "numero")


class LectureAnnonce(TimeStampedModel):
    """Lecture (ou accusé « J'ai pris connaissance ») d'un marin ; la date est celle de la première."""
    annonce = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="lectures")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lectures_annonces")
    accuse = models.BooleanField(default=False)
    version_lue = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("annonce", "user")


class ParametresAnnonces(TimeStampedModel):
    """Réglages des annonces communs à toute la flotte (un seul enregistrement, modifié dans les Réglages)."""
    jours_rappel_accuse = models.PositiveSmallIntegerField(
        default=2, verbose_name="Jours avant le rappel d'accusé de réception (0 : pas de rappel)")

    class Meta:
        verbose_name = "Réglages des annonces"
        verbose_name_plural = "Réglages des annonces"

    def __str__(self):
        return "Réglages des annonces"

    @classmethod
    def courants(cls):
        return cls.objects.first() or cls()
