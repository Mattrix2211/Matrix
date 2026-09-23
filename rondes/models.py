"""Rondes de contrôle (Phase 4 — Opérationnel).

Une ronde est un objet métier à part, distinct des ChecklistTemplate de la
maintenance : un MODÈLE (gabarit) porte un périmètre organisationnel, une
périodicité et des POINTS DE CONTRÔLE configurables par les utilisateurs
habilités. Chaque exécution (Ronde) copie les points du modèle au moment de sa
création (ResultatPoint) : modifier le modèle ensuite ne réécrit jamais une
ronde passée (versionnage par instantané).
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from accounts.models import Roles, UserProfile
from assets.models import Asset, Installation
from logistics.models import Anomalie
from matrix.core.models import OwnedModel, TimeStampedModel
from org.models import Sector, Service, Ship


class RondeModele(TimeStampedModel, OwnedModel):
    """Gabarit de ronde. Périmètre : un seul niveau choisi (navire, service ou
    secteur), les niveaux supérieurs en sont déduits (voir rattacher)."""
    nom = models.CharField(max_length=150, verbose_name="Nom de la ronde")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.CASCADE, related_name="ronde_modeles")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name="ronde_modeles")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.CASCADE, related_name="ronde_modeles")
    periodicite_jours = models.PositiveSmallIntegerField(
        default=1, verbose_name="Périodicité (en jours)",
        help_text="Une ronde est proposée tous les N jours (1 = tous les jours).",
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ronde_modeles_responsable", verbose_name="Marin désigné",
    )
    actif = models.BooleanField(default=True, verbose_name="Active")
    # Incrémentée à chaque modification des points : repère d'historique.
    version = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Modèle de ronde"
        verbose_name_plural = "Modèles de ronde"
        ordering = ["nom"]

    def rattacher(self, ship=None, service=None, sector=None):
        """Renseigne les trois niveaux à partir du plus fin fourni."""
        if sector is not None:
            self.sector, self.service, self.ship = sector, sector.service, sector.service.ship
        elif service is not None:
            self.sector, self.service, self.ship = None, service, service.ship
        else:
            self.sector, self.service, self.ship = None, None, ship

    def clean(self):
        super().clean()
        if self.periodicite_jours < 1:
            raise ValidationError("La périodicité doit être d'au moins 1 jour.")

    @property
    def libelle_perimetre(self):
        if self.sector_id:
            return f"Secteur {self.sector.name}"
        if self.service_id:
            return f"Service {self.service.name}"
        if self.ship_id:
            return f"Unité {self.ship.name}"
        return "Sans périmètre"

    def __str__(self):
        return self.nom


class PointControle(TimeStampedModel):
    """Point de contrôle d'un modèle : libellé libre, équipement facultatif
    (Installation OU Asset, ou rien : ex. état d'une coursive)."""
    modele = models.ForeignKey(RondeModele, on_delete=models.CASCADE, related_name="points")
    ordre = models.PositiveIntegerField(default=0)
    libelle = models.CharField(max_length=200, verbose_name="Point à contrôler")
    consigne = models.CharField(max_length=255, blank=True, default="", verbose_name="Consigne")
    installation = models.ForeignKey(
        Installation, null=True, blank=True, on_delete=models.SET_NULL, related_name="points_ronde",
    )
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.SET_NULL, related_name="points_ronde")
    avec_mesure = models.BooleanField(default=False, verbose_name="Relever une valeur")
    unite_mesure = models.CharField(max_length=20, blank=True, default="", verbose_name="Unité")
    gravite = models.PositiveSmallIntegerField(default=3, verbose_name="Gravité de l'anomalie si non conforme")

    class Meta:
        ordering = ["ordre", "pk"]

    def clean(self):
        super().clean()
        if self.installation_id and self.asset_id:
            raise ValidationError("Un point ne peut être lié qu'à un seul équipement : installation OU matériel.")

    def __str__(self):
        return self.libelle


class Ronde(TimeStampedModel):
    """Exécution datée d'un modèle. Le nom et le périmètre sont copiés : la
    ronde reste lisible même si son modèle est supprimé."""
    A_FAIRE, EN_COURS, TERMINEE, EN_RETARD = "A_FAIRE", "EN_COURS", "TERMINEE", "EN_RETARD"
    STATUTS = (
        (A_FAIRE, "À faire"),
        (EN_COURS, "En cours"),
        (TERMINEE, "Terminée"),
        (EN_RETARD, "En retard"),
    )
    STATUTS_OUVERTS = (A_FAIRE, EN_COURS, EN_RETARD)

    modele = models.ForeignKey(RondeModele, null=True, blank=True, on_delete=models.SET_NULL, related_name="rondes")
    version_modele = models.PositiveIntegerField(default=1)
    nom = models.CharField(max_length=150)
    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.SET_NULL, related_name="rondes")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.SET_NULL, related_name="rondes")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.SET_NULL, related_name="rondes")
    date_prevue = models.DateField()
    statut = models.CharField(max_length=10, choices=STATUTS, default=A_FAIRE)
    assigne_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="rondes_assignees",
    )
    realisee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="rondes_realisees",
    )
    debut = models.DateTimeField(null=True, blank=True)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ronde"
        ordering = ["-date_prevue", "-pk"]

    @property
    def est_ouverte(self):
        return self.statut in self.STATUTS_OUVERTS

    def __str__(self):
        return f"{self.nom} ({self.date_prevue:%d/%m/%Y})"


class ResultatPoint(TimeStampedModel):
    """Point d'une ronde exécutée : instantané du point de contrôle + réponse."""
    CONFORME, NON_CONFORME = "CONFORME", "NON_CONFORME"
    RESULTATS = ((CONFORME, "Conforme"), (NON_CONFORME, "Non conforme"))

    ronde = models.ForeignKey(Ronde, on_delete=models.CASCADE, related_name="resultats")
    ordre = models.PositiveIntegerField(default=0)
    libelle = models.CharField(max_length=200)
    consigne = models.CharField(max_length=255, blank=True, default="")
    installation = models.ForeignKey(Installation, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    equipement_libelle = models.CharField(max_length=255, blank=True, default="")
    avec_mesure = models.BooleanField(default=False)
    unite_mesure = models.CharField(max_length=20, blank=True, default="")
    gravite = models.PositiveSmallIntegerField(default=3)

    resultat = models.CharField(max_length=15, choices=RESULTATS, blank=True, default="")
    mesure = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    commentaire = models.TextField(blank=True, default="")
    saisi_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    saisi_le = models.DateTimeField(null=True, blank=True)
    anomalie = models.ForeignKey(Anomalie, null=True, blank=True, on_delete=models.SET_NULL, related_name="points_ronde")

    class Meta:
        ordering = ["ordre", "pk"]

    @property
    def equipement_lie(self):
        return self.installation or self.asset

    def __str__(self):
        return self.libelle


def destinataires_ronde(objet):
    """Chefs concernés par un modèle ou une ronde : chef de service/secteur du
    périmètre (uniquement sur les niveaux renseignés), même construction que
    logistics.models.destinataires_anomalie."""
    filtre = Q(pk__in=[])
    if objet.service_id:
        filtre |= Q(role=Roles.CHEF_SERVICE, service_id=objet.service_id)
    if objet.sector_id:
        filtre |= Q(role=Roles.CHEF_SECTEUR, sector_id=objet.sector_id)
    return UserProfile.objects.filter(filtre).select_related("user")
