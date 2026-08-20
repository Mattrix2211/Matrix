from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from assets.models import InstallationMaintenance, InstallationEvent, InstallationHourReading, ModeDeclenchement
from notifications.models import Notification, NotificationLevel
from notifications.utils import add_interval, human_delta

User = get_user_model()


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

        def notify(maintenance, verb, level):
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
                Notification.objects.create(
                    user=u, verb=verb, level=level, content_type=maint_ct, object_id=str(maintenance.id)
                )
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
                    # Échéance calendaire déjà dépassée = critique, à venir = simple attention.
                    level = NotificationLevel.DANGER if days <= 0 else NotificationLevel.WARNING
                    verb = f"Entretien — {inst.designation} : {maintenance.title} (échéance calendaire le {next_date.strftime('%d/%m/%Y')}, {human_delta(days)})"
                    notify(maintenance, verb, level)

            # Branche compteur
            if mode in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX) and maintenance.seuil_heures:
                last_reading = InstallationHourReading.objects.filter(installation=inst).order_by("-date").first()
                if last_reading:
                    baseline = maintenance.derniere_echeance_heures or 0
                    seuil = baseline + maintenance.seuil_heures
                    if last_reading.hours >= seuil:
                        # Seuil compteur déjà atteint/dépassé : toujours critique.
                        verb = f"Entretien — {inst.designation} : {maintenance.title} (échéance compteur atteinte : {last_reading.hours} h / seuil {seuil} h)"
                        notify(maintenance, verb, NotificationLevel.DANGER)

        self.stdout.write(f"Notifications créées: {created}")
