from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import JSONField, Q
from matrix.core.models import TimeStampedModel, OwnedModel
from assets.models import Asset, ChecklistTemplate, InstallationMaintenance
from assets.models import AssetType
from assets.mesures import compteur_total
from assets.models import ModeDeclenchement
from django.db.models.signals import post_save
from django.dispatch import receiver
from logistics.models import CorrectiveTicket, TicketStatusLog, destinataires_ticket, niveau_alerte_ticket
from notifications.models import Notification
from accounts.models import AuditLog

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
    # 1 à 5 : 5 = le plus critique (trie « À faire »).
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

    def version_fiche(self):
        """Version de fiche appliquée : celle figée dans l'exécution, sinon la dernière validée."""
        execution = MaintenanceExecution.objects.filter(occurrence=self).select_related("version_fiche").first()
        if execution and execution.version_fiche_id:
            return execution.version_fiche
        if self.installation_maintenance_id:
            return self.installation_maintenance.version_validee
        modele = self.plan.checklist_template if self.plan_id else None
        return modele.version_applicable() if modele else None

    def lignes_fiche(self):
        """Lignes de contrôle et de relevé de la version appliquée, dans l'ordre de la fiche."""
        version = self.version_fiche()
        return list(version.items.order_by("order", "pk")) if version else []

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
    intervenants = models.ManyToManyField(User, blank=True, related_name="executions_intervenant", verbose_name="Intervenants")
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
    # Version de la fiche suivie lors de cette exécution, figée à la première écriture.
    version_fiche = models.ForeignKey(ChecklistTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="executions", verbose_name="Version de la fiche")

    def save(self, *args, **kwargs):
        if self.version_fiche_id is None:
            self.version_fiche = self.occurrence.version_fiche()
        super().save(*args, **kwargs)


def mettre_a_jour_echeance_installation(occ: "MaintenanceOccurrence") -> None:
    """Remet à jour l'échéance de la maintenance d'installation liée, une fois
    l'exécution validée (occurrence passée en statut DONE).

    - Branche compteur (COMPTEUR / LES_DEUX) : la référence 'derniere_echeance_heures'
      est alignée sur le compteur total courant (le plus grand relevé) : c'est le
      compteur à la visite, les heures depuis la dernière visite repartent de zéro.
    - Branche calendaire (CALENDRIER / LES_DEUX) : aucune mise à jour de modèle n'est
      nécessaire ici — generate_installation_occurrences relit directement la date de
      cette MaintenanceExecution comme référence pour calculer la prochaine échéance.
    """
    maintenance = occ.installation_maintenance
    if maintenance is None:
        return
    if maintenance.mode_declenchement in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX):
        total = compteur_total(maintenance.installation.hour_readings.all())
        if total is not None:
            maintenance.derniere_echeance_heures = total
            InstallationMaintenance.objects.filter(pk=maintenance.pk).update(derniere_echeance_heures=total)


@receiver(post_save, sender=MaintenanceExecution)
def create_corrective_on_non_conform(sender, instance: "MaintenanceExecution", created, **kwargs):
    if instance.conformity == "NON_CONFORME":
        occ = instance.occurrence
        asset = occ.asset
        # Une occurrence d'installation (occ.asset is None) ne déclenche pas de
        # ticket automatique : seuls les tickets créés à la main ou par conversion
        # d'une anomalie peuvent viser une installation (CorrectiveTicket.installation).
        if asset is None:
            return
        ticket, created_ticket = CorrectiveTicket.objects.get_or_create(
            asset=asset,
            description=f"Anomalie détectée sur maintenance {occ.id}",
            defaults={"severity": 3}
        )
        if created_ticket:
            TicketStatusLog.objects.create(ticket=ticket, old_status="REPORTED", new_status="REPORTED")
            # Journal transverse (AuditLog) en plus du TicketStatusLog dédié —
            # même principe que les créations manuelles de ticket, cf. tâche
            # Notion « Unifier les modèles d'historique/audit ». actor=None :
            # création automatique par le signal, pas par un utilisateur.
            AuditLog.objects.create(
                actor=instance.executed_by, action="create_ticket_auto",
                details=f"ticket={ticket.pk}; asset={asset}; occurrence={occ.id}",
            )
            # Alerte les chefs du périmètre dès la création automatique du ticket,
            # au même titre que le signalement manuel (logistics/web_views.py::
            # TicketCreateView) — c'est le même événement métier (anomalie
            # détectée sur un actif), seul le déclencheur diffère (inspection QR
            # non conforme plutôt qu'un signalement direct). Destinataires et
            # niveau mutualisés (logistics/models.py) pour ne pas dupliquer cette
            # logique entre les deux chemins de création.
            niveau_alerte = niveau_alerte_ticket(ticket.severity)
            for profile in destinataires_ticket(asset):
                if instance.executed_by_id and profile.user_id == instance.executed_by_id:
                    continue
                Notification.objects.create(
                    user=profile.user,
                    level=niveau_alerte,
                    verb=f"Anomalie détectée sur {asset} lors d'une inspection : {ticket.description}",
                )
