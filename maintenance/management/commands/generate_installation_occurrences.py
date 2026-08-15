from calendar import monthrange
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from assets.models import InstallationMaintenance, InstallationEvent, InstallationHourReading, ModeDeclenchement
from maintenance.models import MaintenanceOccurrence

# Statuts considérés comme "terminés" : une occurrence dans un de ces statuts
# ne bloque pas la création d'une nouvelle occurrence pour la même maintenance.
STATUTS_TERMINES = ("DONE", "CANCELLED")


def add_interval(base_date: date, unite: str, intervalle: int) -> date:
    """Calcule la prochaine échéance calendaire à partir d’une date de base
    (même logique que generate_installation_maintenance_notifications)."""
    if unite == "J":
        return base_date + timedelta(days=intervalle)
    if unite == "S":
        return base_date + timedelta(weeks=intervalle)
    # Mois ou années : arithmétique calendaire (même logique que la branche isolement existante)
    months = intervalle if unite == "M" else intervalle * 12
    y = base_date.year + (base_date.month - 1 + months) // 12
    m = (base_date.month - 1 + months) % 12 + 1
    d = min(base_date.day, monthrange(y, m)[1])
    return date(y, m, d)


def prochaine_echeance(maintenance: InstallationMaintenance, today: date, until: date):
    """Calcule la prochaine date d'échéance d'une maintenance d'installation, tous
    modes confondus. Retourne None si aucune échéance n'est à générer dans la fenêtre.

    Reprend exactement la logique de détection déjà écrite dans
    generate_installation_maintenance_notifications (branche calendaire basée sur le
    dernier InstallationEvent, branche compteur basée sur InstallationHourReading).
    """
    mode = maintenance.mode_declenchement
    inst = maintenance.installation
    echeances = []

    # Branche calendaire : date prévisible à l'avance, dans la fenêtre de génération.
    if mode in (ModeDeclenchement.CALENDRIER, ModeDeclenchement.LES_DEUX) and maintenance.intervalle and maintenance.unite_intervalle:
        last_event = (
            InstallationEvent.objects.filter(installation=inst, label__iexact=maintenance.title)
            .order_by("-date")
            .first()
        )
        base_date = timezone.localtime(last_event.date).date() if last_event else timezone.localtime(maintenance.created_at).date()
        next_date = add_interval(base_date, maintenance.unite_intervalle, maintenance.intervalle)
        if next_date <= until:
            echeances.append(next_date)

    # Branche compteur : pas de date prévisible à l'avance, l'échéance est constatée
    # dès que le seuil est atteint et déclenche une occurrence immédiate (aujourd'hui).
    if mode in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX) and maintenance.seuil_heures:
        last_reading = InstallationHourReading.objects.filter(installation=inst).order_by("-date").first()
        if last_reading:
            baseline = maintenance.derniere_echeance_heures or 0
            seuil = baseline + maintenance.seuil_heures
            if last_reading.hours >= seuil:
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

        for maintenance in InstallationMaintenance.objects.select_related("installation").all():
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
