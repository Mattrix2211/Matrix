"""Absences et indisponibilités des marins (Phase 2 — Vie quotidienne,
VISION_MATRIX_2_0.md §7/§7.4) : modèle générique couvrant tout motif rendant
un marin indisponible sur une période (permission, mission, maladie...),
utilisé par la détection de situations impossibles des échanges de service
(quarts/echanges.py::analyser_echange) et, à terme, par la génération
intelligente de listes (VISION §7.3). C'est le point resté explicitement
ouvert lors de la tâche « Échanges de tours de service » (commit 9e9e3f6,
limite acceptée par le Tech Lead), comblé ici.

App dédiée plutôt qu'ajout dans `quarts` ou `org` : une absence n'est ni une
liste de service (quarts, dont le rôle reste borné aux quarts/gardes) ni une
donnée de hiérarchie organisationnelle (org) — c'est une donnée personnelle
du marin, réutilisable par plusieurs modules (quarts aujourd'hui, la
génération de listes et d'autres modules demain) sans dépendre d'aucun
d'eux. Le référentiel des types d'absence (accounts.models.TypeAbsence) suit
le même pattern que les autres référentiels configurables déjà centralisés
dans accounts/models.py (ServiceFunctionChoice, FonctionQuartChoice...)."""
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import TypeAbsence
from matrix.core.models import OwnedModel, TimeStampedModel


class Absence(TimeStampedModel, OwnedModel):
    """Une période d'indisponibilité déclarée pour un marin. `created_by`
    (OwnedModel) conserve QUI a saisi l'absence (le marin lui-même ou un chef
    en son nom) — distinct de `validee_par`, qui trace la validation.

    Période en JOURS ENTIERS (date_debut/date_fin, comme
    quarts.models.ListeServiceAbstract.date_debut/date_fin) : une absence se
    déclare comme un congé (« du 10 au 15 »), pas heure par heure — la
    granularité la plus rapide à saisir pour ce type de donnée (CLAUDE.md
    §2). `chevauche_creneau` convertit cette période en plage horaire pleine
    journée pour la comparer aux créneaux de quart/garde (datetime précis)."""

    STATUT_DECLAREE = "DECLAREE"
    STATUT_VALIDEE = "VALIDEE"
    STATUT_CHOICES = (
        (STATUT_DECLAREE, "Déclarée"),
        (STATUT_VALIDEE, "Validée"),
    )

    marin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="absences",
        verbose_name="Marin",
    )
    type_absence = models.ForeignKey(
        TypeAbsence, on_delete=models.PROTECT, related_name="absences",
        verbose_name="Type d'absence",
    )
    date_debut = models.DateField(verbose_name="Début")
    date_fin = models.DateField(verbose_name="Fin")
    statut = models.CharField(max_length=16, choices=STATUT_CHOICES, default=STATUT_DECLAREE)
    motif = models.TextField(blank=True, default="", verbose_name="Précision (facultatif)")
    validee_le = models.DateTimeField(null=True, blank=True, verbose_name="Validée le")
    validee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="absences_validees", verbose_name="Validée par",
    )

    class Meta:
        ordering = ("-date_debut",)
        verbose_name = "Absence"
        verbose_name_plural = "Absences et indisponibilités"

    def clean(self):
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({"date_fin": "La date de fin ne peut pas précéder la date de début."})

    def plage_horaire(self):
        """Convertit la période (jours entiers) en plage datetime « aware » :
        minuit du jour de début à minuit du lendemain du jour de fin —
        utilisée pour comparer l'absence à un créneau de quart/garde
        (datetime précis) et pour l'affichage sur le calendrier."""
        tz = timezone.get_current_timezone()
        debut = timezone.make_aware(datetime.combine(self.date_debut, time.min), tz)
        fin = timezone.make_aware(datetime.combine(self.date_fin + timedelta(days=1), time.min), tz)
        return debut, fin

    def chevauche_creneau(self, creneau):
        """Vrai si `creneau` (CreneauQuart/CreneauServiceGarde, ou tout objet
        portant `debut`/`fin` datetime) tombe, même partiellement, dans cette
        absence."""
        debut_absence, fin_absence = self.plage_horaire()
        return creneau.debut < fin_absence and creneau.fin > debut_absence

    def __str__(self):
        return f"{self.marin} — {self.type_absence} du {self.date_debut} au {self.date_fin}"
