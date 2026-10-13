"""RETEX : un cas significatif transformé en enseignement validé, avec routage par domaine et actions suivies.

Il complète les historiques sans les recopier : la source reste liée (ticket, anomalie, tâche, demande…).
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from matrix.core.models import OwnedModel, TimeStampedModel
from org.models import Ship
from taches.models import Tache


class DomaineRetex(TimeStampedModel):
    """Domaine du bord, son COMA référent et l'organisme destinataire habituel (configurables par navire)."""
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="domaines_retex")
    nom = models.CharField(max_length=80, verbose_name="Domaine")
    coma = models.CharField(max_length=40, blank=True, default="", verbose_name="COMA référent")
    organisme = models.CharField(max_length=120, blank=True, default="", verbose_name="Organisme destinataire habituel")
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("nom",)
        unique_together = ("ship", "nom")

    def __str__(self):
        return self.nom


class Retex(TimeStampedModel, OwnedModel):
    ETAT_PROPOSE = "PROPOSE"
    ETAT_VALIDE = "VALIDE"
    ETAT_REFUSE = "REFUSE"
    ETAT_CLOS = "CLOS"
    ETAT_CHOICES = (
        (ETAT_PROPOSE, "Proposé"), (ETAT_VALIDE, "Validé et publié"), (ETAT_REFUSE, "Refusé"), (ETAT_CLOS, "Clos"),
    )
    DIFFUSION_CHOICES = (("BATIMENT", "Bâtiment"), ("FLOTTE", "Flotte (proposé à l'organisme destinataire)"))

    titre = models.CharField(max_length=200, verbose_name="Titre")
    constat = models.TextField(verbose_name="Constat")
    causes = models.TextField(blank=True, default="", verbose_name="Causes et analyses (si établies)")
    enseignement = models.TextField(verbose_name="Enseignement")
    recommandation = models.TextField(blank=True, default="", verbose_name="Recommandation")
    portee = models.CharField(max_length=200, blank=True, default="", verbose_name="Portée envisagée")
    diffusion = models.CharField(max_length=10, choices=DIFFUSION_CHOICES, default="BATIMENT", verbose_name="Niveau de diffusion")
    domaine = models.ForeignKey(DomaineRetex, on_delete=models.PROTECT, related_name="retex")
    organisme = models.CharField(max_length=120, blank=True, default="", verbose_name="Organisme destinataire")
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="retex")
    etat = models.CharField(max_length=10, choices=ETAT_CHOICES, default=ETAT_PROPOSE)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="retex_proposes")
    decide_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    decide_le = models.DateTimeField(null=True, blank=True)
    motif_decision = models.TextField(blank=True, default="")
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    object_id = models.CharField(max_length=64, blank=True, default="")
    source = GenericForeignKey("content_type", "object_id")
    source_libelle = models.CharField(max_length=200, blank=True, default="")
    document = models.OneToOneField("documentation.Document", null=True, blank=True, on_delete=models.SET_NULL, related_name="retex")
    taches = models.ManyToManyField(Tache, blank=True, related_name="retex")

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.titre
