"""Tâche générique attribuée par un chef à un marin de son périmètre.

Le fil de discussion est le `Thread` générique de l'app `threads`, rattaché à la tâche.
"""
from django.conf import settings
from django.db import models

from matrix.core.models import OwnedModel, TimeStampedModel


class Tache(TimeStampedModel, OwnedModel):
    STATUT_A_FAIRE = "A_FAIRE"
    STATUT_EN_COURS = "EN_COURS"
    STATUT_BLOQUEE = "BLOQUEE"
    STATUT_TERMINEE = "TERMINEE"
    STATUT_CHOICES = (
        (STATUT_A_FAIRE, "À faire"),
        (STATUT_EN_COURS, "En cours"),
        (STATUT_BLOQUEE, "Bloquée"),
        (STATUT_TERMINEE, "Terminée"),
    )
    STATUTS_OUVERTS = (STATUT_A_FAIRE, STATUT_EN_COURS, STATUT_BLOQUEE)

    titre = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, default="", verbose_name="Consigne")
    echeance = models.DateField(verbose_name="Échéance")
    statut = models.CharField(max_length=16, choices=STATUT_CHOICES, default=STATUT_A_FAIRE)
    assigne = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="taches_assignees",
        verbose_name="Assignée à",
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="taches_suivies",
        verbose_name="Interlocuteurs du fil",
    )
    motif_blocage = models.TextField(blank=True, default="", verbose_name="Motif du blocage")
    compte_rendu = models.TextField(blank=True, default="", verbose_name="Compte rendu")
    terminee_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("echeance", "pk")
        verbose_name = "Tâche"
        verbose_name_plural = "Tâches"

    def __str__(self):
        return self.titre

    @property
    def ouverte(self):
        return self.statut in self.STATUTS_OUVERTS


class ParametresTaches(TimeStampedModel):
    """Réglages des tâches communs à toute la flotte (un seul enregistrement, modifié dans les Réglages)."""
    jours_entre_relances = models.PositiveSmallIntegerField(
        default=1, verbose_name="Jours entre deux relances (0 : pas de relance)")
    relancer_assigne = models.BooleanField(default=True, verbose_name="Relancer le marin assigné")
    relancer_chef_attributeur = models.BooleanField(default=True, verbose_name="Relancer le chef qui a attribué la tâche")
    relancer_chefs_si_blocage = models.BooleanField(
        default=True, verbose_name="Relancer les chefs du périmètre pour un blocage en retard")
    jours_terminees_affichees = models.PositiveSmallIntegerField(
        default=30, verbose_name="Jours d'affichage des tâches terminées dans la vue d'avancement")

    class Meta:
        verbose_name = "Réglages des tâches"
        verbose_name_plural = "Réglages des tâches"

    def __str__(self):
        return "Réglages des tâches"

    @classmethod
    def courants(cls):
        return cls.objects.first() or cls()
