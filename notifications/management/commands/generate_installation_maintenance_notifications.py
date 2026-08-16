from calendar import monthrange
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from assets.models import InstallationMaintenance, InstallationEvent, InstallationHourReading, ModeDeclenchement
from notifications.models import Notification

User = get_user_model()


def add_interval(base_date: date, unite: str, intervalle: int) -> date:
    """Calcule la prochaine échéance calendaire à partir d’une date de base."""
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


class Command(BaseCommand):
    help = "Génère des notifications d’échéances d’entretien (calendaire et/ou compteur) pour les maintenances d’installations (à lancer chaque jour à 08:00)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="Fenêtre en jours avant l’échéance calendaire (par défaut 7)")

    def handle(self, *args, **opts):
        window = int(opts.get("days") or 7)
        today = timezone.localdate()
        now = timezone.now()
        start_of_day = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        # select_related("profile") évite une requête par utilisateur pour lire sa
        # préférence d'heure de notification.
        users = list(User.objects.filter(is_active=True).select_related("profile"))
        if not users:
            self.stdout.write("Aucun utilisateur actif. Abort.")
            return

        maint_ct = ContentType.objects.get_for_model(InstallationMaintenance)
        created = 0

        def human_delta(days: int) -> str:
            if days == 0:
                return "aujourd’hui"
            if days > 0:
                return f"dans {days} j"
            return f"depuis {-days} j"

        # Heure courante (HH:MM) pour comparer aux préférences utilisateur
        now_local = timezone.localtime(now).time().replace(second=0, microsecond=0)

        # Notifications déjà envoyées aujourd'hui, chargées en une seule requête et
        # utilisées ensuite en mémoire : évite un .exists() par combinaison
        # maintenance x utilisateur (N x M requêtes), inoffensif tant que la commande
        # n'est jamais planifiée, problématique une fois exécutée chaque jour.
        deja_notifies = set(
            Notification.objects.filter(content_type=maint_ct, created_at__gte=start_of_day)
            .values_list("user_id", "object_id", "verb")
        )

        def notify(maintenance, verb):
            nonlocal created
            for u in users:
                pref = getattr(getattr(u, 'profile', None), 'notification_time', None)
                # défaut 08:00 si non défini
                target_time = pref or timezone.datetime.strptime('08:00', '%H:%M').time()
                if (now_local.hour, now_local.minute) != (target_time.hour, target_time.minute):
                    continue
                cle = (u.id, str(maintenance.id), verb)
                if cle in deja_notifies:
                    continue
                Notification.objects.create(user=u, verb=verb, content_type=maint_ct, object_id=str(maintenance.id))
                deja_notifies.add(cle)
                created += 1

        for maintenance in InstallationMaintenance.objects.select_related("installation").all():
            mode = maintenance.mode_declenchement
            inst = maintenance.installation

            # Branche calendaire
            if mode in (ModeDeclenchement.CALENDRIER, ModeDeclenchement.LES_DEUX) and maintenance.intervalle and maintenance.unite_intervalle:
                # Dernière réalisation connue : dernier événement de l'installation dont le
                # libellé correspond au titre de la maintenance (aucun lien direct en base entre
                # InstallationEvent et InstallationMaintenance) ; à défaut, date de création de la tâche.
                last_event = (
                    InstallationEvent.objects.filter(installation=inst, label__iexact=maintenance.title)
                    .order_by("-date")
                    .first()
                )
                base_date = timezone.localtime(last_event.date).date() if last_event else timezone.localtime(maintenance.created_at).date()
                next_date = add_interval(base_date, maintenance.unite_intervalle, maintenance.intervalle)
                days = (next_date - today).days
                if days <= window:
                    verb = f"Entretien — {inst.designation} : {maintenance.title} (échéance calendaire le {next_date.strftime('%d/%m/%Y')}, {human_delta(days)})"
                    notify(maintenance, verb)

            # Branche compteur
            if mode in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX) and maintenance.seuil_heures:
                last_reading = InstallationHourReading.objects.filter(installation=inst).order_by("-date").first()
                if last_reading:
                    baseline = maintenance.derniere_echeance_heures or 0
                    seuil = baseline + maintenance.seuil_heures
                    if last_reading.hours >= seuil:
                        verb = f"Entretien — {inst.designation} : {maintenance.title} (échéance compteur atteinte : {last_reading.hours} h / seuil {seuil} h)"
                        notify(maintenance, verb)

        self.stdout.write(f"Notifications créées: {created}")
