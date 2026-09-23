from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from assets.models import Installation
from notifications.models import Notification, NotificationLevel
from notifications.utils import human_delta

User = get_user_model()

class Command(BaseCommand):
    help = "Génère des notifications d’échéances vibration/isolement pour les installations (à lancer chaque jour à 08:00)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="Fenêtre en jours avant l’échéance (par défaut 7)")

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

        inst_ct = ContentType.objects.get_for_model(Installation)
        created = 0

        # Heure courante (HH:MM) pour comparer aux préférences utilisateur
        now_local = timezone.localtime(now).time().replace(second=0, microsecond=0)

        # Notifications déjà envoyées aujourd'hui, chargées en une seule requête et
        # utilisées ensuite en mémoire : évite un .exists() par combinaison
        # installation x utilisateur (N x M requêtes), inoffensif tant que la commande
        # n'est jamais planifiée, problématique une fois exécutée chaque jour.
        deja_notifies = set(
            Notification.objects.filter(content_type=inst_ct, created_at__gte=start_of_day)
            .values_list("user_id", "object_id", "verb")
        )

        def notifier(inst, verb, level):
            nonlocal created
            for u in users:
                pref = getattr(getattr(u, 'profile', None), 'notification_time', None)
                # défaut 08:00 si non défini
                target_time = pref or timezone.datetime.strptime('08:00', '%H:%M').time()
                if (now_local.hour, now_local.minute) != (target_time.hour, target_time.minute):
                    continue
                cle = (u.id, str(inst.id), verb)
                if cle in deja_notifies:
                    continue
                Notification.objects.create(
                    user=u, verb=verb, level=level, content_type=inst_ct, object_id=str(inst.id)
                )
                deja_notifies.add(cle)
                created += 1

        for inst in Installation.objects.all().prefetch_related("vibration_readings", "isolation_readings"):
            # Vibration
            vib = inst.vibration_readings.order_by("-date").first()
            if vib:
                days_map = {"A": inst.vib_days_a, "B": inst.vib_days_b, "C": inst.vib_days_c}
                delta = days_map.get(vib.state, inst.vib_days_b)
                next_date = vib.date + timedelta(days=delta)
                days = (next_date - today).days
                if days <= window:
                    # Échéance déjà dépassée = critique (DANGER), à venir = simple attention (WARNING).
                    level = NotificationLevel.DANGER if days <= 0 else NotificationLevel.WARNING
                    verb = f"Vibration — {inst.designation}: échéance le {next_date.strftime('%d/%m/%Y')} ({human_delta(days)})"
                    notifier(inst, verb, level)
            # Isolement
            iso = inst.isolation_readings.order_by("-date").first()
            if iso:
                months = 1 if inst.iso_periodicity == "M" else 3 if inst.iso_periodicity == "T" else 12
                # add months safely
                from calendar import monthrange
                y = iso.date.year + (iso.date.month - 1 + months) // 12
                m = (iso.date.month - 1 + months) % 12 + 1
                d = min(iso.date.day, monthrange(y, m)[1])
                next_date = timezone.localdate(timezone.datetime(y, m, d))
                days = (next_date - today).days
                if days <= window:
                    level = NotificationLevel.DANGER if days <= 0 else NotificationLevel.WARNING
                    verb = f"Isolement — {inst.designation}: échéance le {next_date.strftime('%d/%m/%Y')} ({human_delta(days)})"
                    notifier(inst, verb, level)

        self.stdout.write(self.style.SUCCESS(f"Notifications créées: {created}"))
