from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from django.contrib.contenttypes.models import ContentType
from assets.models import Installation
from notifications.models import Notification

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

        users = list(User.objects.filter(is_active=True))
        if not users:
            self.stdout.write("Aucun utilisateur actif. Abort.")
            return

        inst_ct = ContentType.objects.get_for_model(Installation)
        created = 0

        def human_delta(days: int) -> str:
            if days == 0:
                return "aujourd’hui"
            if days > 0:
                return f"dans {days} j"
            return f"depuis {-days} j"

        # Heure courante (HH:MM) pour comparer aux préférences utilisateur
        now_local = timezone.localtime(now).time().replace(second=0, microsecond=0)

        for inst in Installation.objects.all().prefetch_related("vibration_readings", "isolation_readings"):
            # Vibration
            vib = inst.vibration_readings.order_by("-date").first()
            if vib:
                days_map = {"A": inst.vib_days_a, "B": inst.vib_days_b, "C": inst.vib_days_c}
                delta = days_map.get(vib.state, inst.vib_days_b)
                next_date = vib.date + timedelta(days=delta)
                days = (next_date - today).days
                if days <= window:
                    verb = f"Vibration — {inst.designation}: échéance le {next_date.strftime('%d/%m/%Y')} ({human_delta(days)})"
                    for u in users:
                        pref = getattr(getattr(u, 'profile', None), 'notification_time', None)
                        # défaut 08:00 si non défini
                        target_time = pref or timezone.datetime.strptime('08:00', '%H:%M').time()
                        if (now_local.hour, now_local.minute) != (target_time.hour, target_time.minute):
                            continue
                        if Notification.objects.filter(user=u, content_type=inst_ct, object_id=str(inst.id), verb=verb, created_at__gte=start_of_day).exists():
                            continue
                        Notification.objects.create(user=u, verb=verb, content_type=inst_ct, object_id=str(inst.id))
                        created += 1
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
                    verb = f"Isolement — {inst.designation}: échéance le {next_date.strftime('%d/%m/%Y')} ({human_delta(days)})"
                    for u in users:
                        pref = getattr(getattr(u, 'profile', None), 'notification_time', None)
                        target_time = pref or timezone.datetime.strptime('08:00', '%H:%M').time()
                        if (now_local.hour, now_local.minute) != (target_time.hour, target_time.minute):
                            continue
                        if Notification.objects.filter(user=u, content_type=inst_ct, object_id=str(inst.id), verb=verb, created_at__gte=start_of_day).exists():
                            continue
                        Notification.objects.create(user=u, verb=verb, content_type=inst_ct, object_id=str(inst.id))
                        created += 1

        self.stdout.write(self.style.SUCCESS(f"Notifications créées: {created}"))
