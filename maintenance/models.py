from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import JSONField, Q
from matrix.core.models import TimeStampedModel, OwnedModel
from assets.models import Asset, ChecklistTemplate, InstallationMaintenance
from assets.models import AssetType
from assets.models import InstallationHourReading, ModeDeclenchement
from django.db.models.signals import post_save
from django.dispatch import receiver
from logistics.models import CorrectiveTicket, TicketStatusLog

User = get_user_model()

class MaintenancePlan(TimeStampedModel, OwnedModel):
    SCOPE = (
        ("ASSET_TYPE", "Par type d'actif"),
        ("ASSET", "Par actif"),
    )
    scope = models.CharField(max_length=16, choices=SCOPE)
    asset_type = models.ForeignKey(AssetType, null=True, blank=True, on_delete=models.CASCADE, related_name="maintenance_plans")
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.CASCADE, related_name="maintenance_plans")
    name = models.CharField(max_length=255)
    every_n_days = models.PositiveIntegerField(default=90)
    expected_duration_min = models.PositiveIntegerField(default=30)
    checklist_template = models.ForeignKey(ChecklistTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    requires_validation = models.BooleanField(default=False)
    validation_role = models.CharField(max_length=32, blank=True, default="CHEF_SECTION")

class MaintenanceOccurrence(TimeStampedModel, OwnedModel):
    STATUS = (
        ("PLANNED", "Planifiée"),
        ("ASSIGNED", "Assignée"),
        ("IN_PROGRESS", "En cours"),
        ("WAITING_VALIDATION", "En validation"),
        ("DONE", "Terminée"),
        ("OVERDUE", "En retard"),
        ("CANCELLED", "Annulée"),
    )
    # Occurrence liée à du matériel mobile : plan + asset renseignés ensemble.
    plan = models.ForeignKey(MaintenancePlan, null=True, blank=True, on_delete=models.CASCADE, related_name="occurrences")
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.CASCADE, related_name="occurrences")
    # Occurrence liée à une installation fixe : installation_maintenance seul renseigné.
    installation_maintenance = models.ForeignKey(
        InstallationMaintenance, null=True, blank=True, on_delete=models.CASCADE, related_name="occurrences"
    )
    scheduled_for = models.DateField()
    status = models.CharField(max_length=24, choices=STATUS, default="PLANNED")
    priority = models.PositiveSmallIntegerField(default=3)
    assignees = models.ManyToManyField(User, blank=True, related_name="assigned_occurrences")

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="occurrence_liee_a_asset_xor_installation",
                condition=(
                    (Q(plan__isnull=False) & Q(asset__isnull=False) & Q(installation_maintenance__isnull=True))
                    | (Q(plan__isnull=True) & Q(asset__isnull=True) & Q(installation_maintenance__isnull=False))
                ),
            ),
        ]

    @property
    def titre_affiche(self):
        """Libellé lisible de l'occurrence, qu'elle concerne du matériel
        mobile (plan + asset) ou une installation fixe (installation_maintenance).
        Point unique pour ce libellé, utilisé par calendar_app, dashboard et
        l'export iCal — à ne pas dupliquer ailleurs."""
        if self.installation_maintenance_id:
            return f"{self.installation_maintenance.installation} - {self.installation_maintenance.title}"
        return str(self.asset)

class OccurrenceStatusLog(TimeStampedModel):
    occurrence = models.ForeignKey(MaintenanceOccurrence, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=24)
    new_status = models.CharField(max_length=24)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True, default="")

class MaintenanceExecution(TimeStampedModel, OwnedModel):
    CONFORMITY = (
        ("CONFORME", "Conforme"),
        ("NON_CONFORME", "Non conforme"),
        ("A_SURVEILLER", "À surveiller"),
    )
    occurrence = models.OneToOneField(MaintenanceOccurrence, on_delete=models.CASCADE, related_name="execution")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="executions")
    results = JSONField(default=dict, blank=True)
    measurements = JSONField(default=dict, blank=True)
    conformity = models.CharField(max_length=24, choices=CONFORMITY, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    # Signature de validation (T-FEAT signature) : le passage en "Terminée" (DONE) sur
    # une installation critique exige une ré-authentification légère (mot de passe
    # courant, cf. OccurrenceExecuteView) avant d'être appliqué. AuditLog trace déjà
    # "qui a fait quoi", mais ces deux champs distinguent explicitement une validation
    # engageante d'une simple exécution.
    valide_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="executions_validees", verbose_name="Validé par",
    )
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name="Date de validation")


def mettre_a_jour_echeance_installation(occ: "MaintenanceOccurrence") -> None:
    """Remet à jour l'échéance de la maintenance d'installation liée, une fois
    l'exécution validée (occurrence passée en statut DONE).

    - Branche compteur (COMPTEUR / LES_DEUX) : la référence 'derniere_echeance_heures'
      est alignée sur le dernier relevé d'heures de marche connu, ce qui repousse le
      prochain déclenchement du seuil configuré.
    - Branche calendaire (CALENDRIER / LES_DEUX) : aucune mise à jour de modèle n'est
      nécessaire ici — generate_installation_occurrences relit directement la date de
      cette MaintenanceExecution comme référence pour calculer la prochaine échéance.
    """
    maintenance = occ.installation_maintenance
    if maintenance is None:
        return
    if maintenance.mode_declenchement in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX):
        dernier_releve = (
            InstallationHourReading.objects.filter(installation=maintenance.installation)
            .order_by("-date")
            .first()
        )
        if dernier_releve is not None:
            maintenance.derniere_echeance_heures = dernier_releve.hours
            InstallationMaintenance.objects.filter(pk=maintenance.pk).update(
                derniere_echeance_heures=dernier_releve.hours
            )


@receiver(post_save, sender=MaintenanceExecution)
def create_corrective_on_non_conform(sender, instance: "MaintenanceExecution", created, **kwargs):
    if instance.conformity == "NON_CONFORME":
        occ = instance.occurrence
        asset = occ.asset
        # CorrectiveTicket ne concerne aujourd'hui que le matériel mobile (FK asset
        # non-nullable) : aucun équivalent n'existe côté installation fixe. Une
        # occurrence d'installation (occ.asset is None) ne doit donc pas déclencher
        # de ticket correctif tant que ce concept n'existe pas pour les installations.
        if asset is None:
            return
        ticket, created_ticket = CorrectiveTicket.objects.get_or_create(
            asset=asset,
            description=f"Anomalie détectée sur maintenance {occ.id}",
            defaults={"severity": 3}
        )
        if created_ticket:
            TicketStatusLog.objects.create(ticket=ticket, old_status="REPORTED", new_status="REPORTED")
