from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from assets.mesures import heures_depuis_visite_maintenance
from assets.models import InstallationMaintenance, InstallationEvent, ModeDeclenchement
from maintenance.models import MaintenanceOccurrence, MaintenanceExecution
from notifications.utils import add_interval

# Statuts considérés comme "terminés" : une occurrence dans un de ces statuts
# ne bloque pas la création d'une nouvelle occurrence pour la même maintenance.
STATUTS_TERMINES = ("DONE", "CANCELLED")


def prochaine_echeance(maintenance: InstallationMaintenance, today: date, until: date):
    """Calcule la prochaine date d'échéance d'une maintenance d'installation, tous
    modes confondus. Retourne None si aucune échéance n'est à générer dans la fenêtre.

    Branche calendaire : la dernière réalisation est lue en priorité sur la
    MaintenanceExecution de la dernière occurrence terminée, à défaut sur
    InstallationEvent.label (maintenances sans exécution structurée).
    """
    mode = maintenance.mode_declenchement
    inst = maintenance.installation
    echeances = []

    # Branche calendaire : date prévisible à l'avance, dans la fenêtre de génération.
    if mode in (ModeDeclenchement.CALENDRIER, ModeDeclenchement.LES_DEUX) and maintenance.intervalle and maintenance.unite_intervalle:
        last_execution = (
            MaintenanceExecution.objects.filter(
                occurrence__installation_maintenance=maintenance, completed_at__isnull=False
            )
            .order_by("-completed_at")
            .first()
        )
        if last_execution:
            base_date = timezone.localtime(last_execution.completed_at).date()
        else:
            last_event = (
                InstallationEvent.objects.filter(installation=inst, label__iexact=maintenance.title)
                .order_by("-date")
                .first()
            )
            base_date = timezone.localtime(last_event.date).date() if last_event else timezone.localtime(maintenance.created_at).date()
        next_date = add_interval(base_date, maintenance.unite_intervalle, maintenance.intervalle)
        if next_date <= until:
            echeances.append(next_date)

    # Branche compteur : pas de date prévisible, l'échéance est constatée dès que les
    # heures depuis la dernière visite atteignent le seuil (occurrence immédiate).
    if mode in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX) and maintenance.seuil_heures:
        depuis_visite = heures_depuis_visite_maintenance(maintenance, list(inst.hour_readings.all()))
        if depuis_visite is not None and depuis_visite >= maintenance.seuil_heures:
            echeances.append(today)

    if not echeances:
        return None
    # En mode "Le premier des deux", l'échéance la plus proche déclenche l'occurrence.
    return min(echeances)


class Command(BaseCommand):
    help = "Génère les occurrences de maintenance (calendrier et/ou compteur) pour les installations fixes, sur une fenêtre de 90 jours, comme generate_occurrences pour le matériel mobile (à lancer chaque jour)."

    def add_arguments(self, parser):
        parser.add_argument("--days-ahead", type=int, default=90, help="Fenêtre en jours pour la branche calendaire (par défaut 90, alignée sur generate_occurrences)")

    def handle(self, *args, **opts):
        days_ahead = int(opts.get("days_ahead") or 90)
        today = timezone.localdate()
        until = today + timedelta(days=days_ahead)
        created = 0

        for maintenance in InstallationMaintenance.objects.select_related("installation").filter(installation__isnull=False):
            echeance = prochaine_echeance(maintenance, today, until)
            if echeance is None:
                continue

            # Évite les doublons : une occurrence non terminée existe déjà pour cette maintenance.
            if maintenance.occurrences.exclude(status__in=STATUTS_TERMINES).exists():
                continue

            MaintenanceOccurrence.objects.create(
                installation_maintenance=maintenance,
                scheduled_for=echeance,
                status="PLANNED",
            )
            created += 1

        self.stdout.write(f"Occurrences d'installation créées : {created}")
