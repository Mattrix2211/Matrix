"""Documentation et procédures : bibliothèque contextualisée, validée et versionnée.

Une version publiée reste applicable jusqu'à la validation d'une nouvelle ; chaque version est conservée.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from matrix.core.models import OwnedModel, TimeStampedModel
from matrix.core.validators import valider_document
from org.models import Section, Sector, Service, Ship


class Document(TimeStampedModel, OwnedModel):
    ORIGINE_OFFICIELLE = "OFFICIELLE"
    ORIGINE_LOCALE = "LOCALE"
    ORIGINE_CHOICES = ((ORIGINE_OFFICIELLE, "Procédure officielle"), (ORIGINE_LOCALE, "Note locale (non réglementaire)"))

    titre = models.CharField(max_length=200, verbose_name="Titre")
    domaine = models.CharField(max_length=80, blank=True, default="", verbose_name="Domaine métier")
    origine = models.CharField(max_length=12, choices=ORIGINE_CHOICES, default=ORIGINE_LOCALE, verbose_name="Origine")
    reference_source = models.CharField(max_length=200, blank=True, default="", verbose_name="Source officielle (référence)")
    prochaine_revision = models.DateField(null=True, blank=True, verbose_name="Prochaine révision")
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="documents")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    equipage = models.CharField(max_length=8, blank=True, default="", verbose_name="Équipage")
    archive = models.BooleanField(default=False)

    class Meta:
        ordering = ("titre",)

    def __str__(self):
        return self.titre

    @property
    def cible_libelle(self):
        noeud = self.section or self.sector or self.service or self.ship
        return f"{noeud}" + (f" · équipage {self.equipage}" if self.equipage else "")

    @property
    def version_applicable(self):
        return self.versions.filter(etat=VersionDocument.ETAT_PUBLIEE).first()


class VersionDocument(TimeStampedModel):
    ETAT_BROUILLON = "BROUILLON"
    ETAT_SOUMISE = "SOUMISE"
    ETAT_PUBLIEE = "PUBLIEE"
    ETAT_REFUSEE = "REFUSEE"
    ETAT_OBSOLETE = "OBSOLETE"
    ETAT_CHOICES = (
        (ETAT_BROUILLON, "Brouillon"), (ETAT_SOUMISE, "Soumise à validation"), (ETAT_PUBLIEE, "Publiée"),
        (ETAT_REFUSEE, "Refusée"), (ETAT_OBSOLETE, "Obsolète"),
    )
    ETATS_OUVERTS = (ETAT_BROUILLON, ETAT_SOUMISE)

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    numero = models.PositiveIntegerField()
    contenu = models.TextField(verbose_name="Contenu")
    fichier = models.FileField(upload_to="documentation/", null=True, blank=True, validators=[valider_document], verbose_name="Fichier joint")
    resume = models.CharField(max_length=300, blank=True, default="", verbose_name="Ce qui change")
    etat = models.CharField(max_length=10, choices=ETAT_CHOICES, default=ETAT_BROUILLON)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="versions_documents")
    valide_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    valide_le = models.DateTimeField(null=True, blank=True)
    date_effet = models.DateField(null=True, blank=True)
    motif_refus = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("-numero",)
        unique_together = ("document", "numero")


class LienDocument(TimeStampedModel):
    """Rattachement d'un document à un objet (tâche, installation, formation) pour l'afficher à son contexte."""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="liens")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    objet = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = ("document", "content_type", "object_id")
