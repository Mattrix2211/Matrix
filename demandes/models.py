"""Demande : dossier de suivi d'une difficulté signalée sur un objet (tâche, installation, anomalie…).

Le fil de discussion est le `Thread` générique de l'app `threads`, rattaché à la demande.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from matrix.core.models import OwnedModel, TimeStampedModel
from org.models import Section, Sector, Service, Ship


class Demande(TimeStampedModel, OwnedModel):
    ETAT_OUVERT = "OUVERT"
    ETAT_EN_TRAITEMENT = "EN_TRAITEMENT"
    ETAT_EN_ATTENTE = "EN_ATTENTE"
    ETAT_RESOLU = "RESOLU"
    ETAT_CLOS = "CLOS"
    ETAT_CHOICES = (
        (ETAT_OUVERT, "Ouvert"),
        (ETAT_EN_TRAITEMENT, "En traitement"),
        (ETAT_EN_ATTENTE, "En attente d'information"),
        (ETAT_RESOLU, "Résolu"),
        (ETAT_CLOS, "Clos"),
    )
    ETATS_OUVERTS = (ETAT_OUVERT, ETAT_EN_TRAITEMENT, ETAT_EN_ATTENTE, ETAT_RESOLU)

    PRIORITE_NORMALE = "NORMALE"
    PRIORITE_URGENTE = "URGENTE"
    PRIORITE_CHOICES = ((PRIORITE_NORMALE, "Normale"), (PRIORITE_URGENTE, "Urgente"))

    titre = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    etat = models.CharField(max_length=16, choices=ETAT_CHOICES, default=ETAT_OUVERT, verbose_name="État")
    priorite = models.CharField(max_length=8, choices=PRIORITE_CHOICES, default=PRIORITE_NORMALE, verbose_name="Priorité")
    echeance = models.DateField(null=True, blank=True, verbose_name="Échéance")
    declarant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="demandes_declarees")
    # Jamais sans propriétaire : un responsable est désigné dès la création.
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="demandes_a_traiter")
    interlocuteurs = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="demandes_suivies", verbose_name="Interlocuteurs désignés",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    objet = GenericForeignKey("content_type", "object_id")
    # Rattachement du déclarant, copié à la création : sert au périmètre des chefs.
    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.SET_NULL, related_name="demandes")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.SET_NULL, related_name="demandes")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.SET_NULL, related_name="demandes")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="demandes")
    resolue_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Demande"
        verbose_name_plural = "Demandes"

    def __str__(self):
        return self.titre

    @property
    def ouverte(self):
        return self.etat in self.ETATS_OUVERTS

    def acteurs(self):
        """Comptes qui suivent le dossier : déclarant, responsable, interlocuteurs désignés."""
        ids = {self.declarant_id, self.responsable_id, *self.interlocuteurs.values_list("pk", flat=True)}
        return get_user_model().objects.filter(pk__in=ids, is_active=True)
