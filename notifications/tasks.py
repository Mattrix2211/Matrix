from celery import shared_task
from django.core.management import call_command
from django.db.models import F, Q
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta, time as dt_time
from .models import Notification, NotificationLevel
from training.models import TrainingRecord
from maintenance.models import MaintenanceOccurrence
from logistics.models import StockPiece
from accounts.models import UserProfile, Roles
from assets.models import Installation, InstallationMaintenance, ModeDeclenchement
from assets.trend import jours_avant_franchissement_seuil
from calendar_app.views import evenements_utilisateur_jour

# Échéances (en jours avant expiration) auxquelles une formation déclenche une
# alerte : réutilisé par dashboard/web_views.py pour aligner le seuil "bientôt
# expirée" de la carte "Mes qualifications" sur celui de ces notifications,
# plutôt que de dupliquer ces valeurs à un autre endroit du code.
JOURS_ALERTE_EXPIRATION_FORMATION = (30, 60, 90)


@shared_task
def notify_expiring_training(days_list=JOURS_ALERTE_EXPIRATION_FORMATION):
    today = timezone.localdate()
    for days in days_list:
        target = today + timedelta(days=days)
        for rec in TrainingRecord.objects.filter(expires_at=target).select_related('user', 'course'):
            Notification.objects.get_or_create(
                user=rec.user,
                verb=f"Formation '{rec.course.title}' expire dans {days} jours",
                defaults={"level": NotificationLevel.WARNING},
            )
    return {"status": "ok"}

@shared_task
def notify_overdue_occurrences():
    occurrences = MaintenanceOccurrence.objects.filter(status='OVERDUE').select_related(
        'plan'
    ).prefetch_related('assignees')
    for occ in occurrences:
        for u in occ.assignees.all():
            Notification.objects.get_or_create(
                user=u,
                verb=f"Occurrence en retard: {occ.id}",
                defaults={"level": NotificationLevel.DANGER},
            )
    return {"status": "ok"}

@shared_task
def notify_low_stock():
    """Alerte les chefs concernés dès qu'une pièce de stock passe sous son seuil minimal.

    Le destinataire est déterminé à partir du périmètre de la pièce (service/secteur/
    section) : chef de service dont le service correspond, chef de secteur dont le
    secteur correspond, et chef de section dont la section correspond si la pièce en
    a une (section optionnelle, comme sur Installation/Asset).

    Déduplication : une seule notification active par pièce et par destinataire tant
    qu'elle n'a pas été résolue - pas de rappel quotidien pour une même pièce déjà sous
    le seuil.

    Cycle de vie de l'alerte : dès qu'une pièce repasse au-dessus (ou à l'égal) de son
    seuil minimal, la notification active liée à cette pièce est résolue (même pattern
    que l'action "marquer comme lue" côté utilisateur : aucune autre partie du code ne
    supprime réellement une Notification en base). Une fois résolue, une nouvelle
    rupture recrée bien une alerte, puisque la déduplication ne porte que sur les
    notifications encore actives.
    """
    piece_ct = ContentType.objects.get_for_model(StockPiece)

    # Pièces redevenues conformes : on résout leurs notifications actives pour
    # permettre une nouvelle alerte en cas de re-rupture future.
    for piece in StockPiece.objects.filter(quantite__gte=F("quantite_minimale")):
        Notification.objects.filter(
            content_type=piece_ct, object_id=str(piece.pk), is_read=False
        ).update(is_read=True)

    for piece in StockPiece.objects.filter(quantite__lt=F("quantite_minimale")).select_related(
        "service", "sector", "section"
    ):
        scope_filter = Q(role=Roles.CHEF_SERVICE, service=piece.service) | Q(
            role=Roles.CHEF_SECTEUR, sector=piece.sector
        )
        if piece.section_id:
            scope_filter |= Q(role=Roles.CHEF_SECTION, section=piece.section)

        verb = f"Stock sous le seuil : {piece.reference} - {piece.designation} ({piece.quantite}/{piece.quantite_minimale})"
        for profile in UserProfile.objects.filter(scope_filter).select_related("user"):
            Notification.objects.get_or_create(
                user=profile.user,
                content_type=piece_ct,
                object_id=str(piece.pk),
                is_read=False,
                defaults={"verb": verb, "level": NotificationLevel.DANGER},
            )
    return {"status": "ok"}

@shared_task
def generate_installation_notifications(days: int = 7):
    """Alerte les marins des échéances de vibration/isolement des installations fixes.

    Enveloppe la commande de gestion du même nom (qui porte la logique métier et ses
    tests) afin de la rendre planifiable quotidiennement via Celery Beat.
    """
    call_command("generate_installation_notifications", days=days)
    return {"status": "ok"}

@shared_task
def generate_installation_maintenance_notifications(days: int = 7):
    """Alerte les marins des échéances d'entretien (calendaire/compteur) des
    maintenances d'installations fixes.

    Enveloppe la commande de gestion du même nom (qui porte la logique métier et ses
    tests) afin de la rendre planifiable quotidiennement via Celery Beat.
    """
    call_command("generate_installation_maintenance_notifications", days=days)
    return {"status": "ok"}


def _destinataires_installation(installation):
    """Chefs concernés par une installation (même construction que le
    scope_filter de notify_low_stock : chef de service/secteur dont le
    périmètre correspond, et chef de section si l'installation en a une)."""
    scope_filter = Q(role=Roles.CHEF_SERVICE, service=installation.service) | Q(
        role=Roles.CHEF_SECTEUR, sector=installation.sector
    )
    if installation.section_id:
        scope_filter |= Q(role=Roles.CHEF_SECTION, section=installation.section)
    return UserProfile.objects.filter(scope_filter).select_related("user")


def _signaler_ou_resoudre_derive(content_type, object_id, destinataires, verb, en_derive):
    """Crée/maintient ou résout une alerte de dérive, selon le même cycle de vie
    que notify_low_stock : une notification active tant que la dérive persiste,
    résolue (is_read=True) dès qu'elle disparaît (pas de rappel à chaque
    exécution pour la même dérive déjà signalée)."""
    if not en_derive:
        Notification.objects.filter(
            content_type=content_type, object_id=object_id, is_read=False
        ).update(is_read=True)
        return
    for profile in destinataires:
        Notification.objects.get_or_create(
            user=profile.user,
            content_type=content_type,
            object_id=object_id,
            is_read=False,
            # Dérive détectée AVANT le franchissement réel du seuil : c'est un
            # signal préventif (WARNING), pas encore une alerte critique (DANGER).
            defaults={"verb": verb, "level": NotificationLevel.WARNING},
        )


@shared_task
def detect_installation_drift():
    """Détecte une dérive sur les relevés techniques des installations fixes
    (isolement en Ohms, heures de marche vs seuil d'entretien compteur), par
    régression linéaire simple sur les derniers relevés (assets/trend.py), et
    alerte les chefs concernés AVANT le franchissement réel du seuil.

    Portée : uniquement l'isolement et les heures de marche, qui sont des
    grandeurs continues avec un seuil numérique - la vibration (état qualitatif
    A/B/C) n'a pas de seuil numérique franchissable par régression et n'est
    donc pas concernée ici.

    Le seuil d'isolement (Installation.isolation_seuil_ohms) est optionnel et
    propre à chaque installation : sans seuil renseigné, aucune dérive n'est
    calculée. Le seuil des heures de marche est celui déjà défini sur chaque
    InstallationMaintenance en mode compteur (seuil_heures + derniere_echeance_heures).

    Même cycle de vie que notify_low_stock : une notification active par
    installation/entretien tant que la dérive persiste, résolue dès qu'elle
    disparaît (valeurs stabilisées, améliorées, ou seuil retiré).
    """
    inst_ct = ContentType.objects.get_for_model(Installation)
    maint_ct = ContentType.objects.get_for_model(InstallationMaintenance)

    for installation in Installation.objects.select_related("service", "sector", "section").prefetch_related(
        "isolation_readings", "maintenances", "hour_readings"
    ):
        # Isolement (Ohms) : dérive à la baisse vers le seuil minimal.
        object_id = f"{installation.id}:DERIVE_ISOLEMENT"
        jours = None
        if installation.isolation_seuil_ohms:
            releves = [(r.date, float(r.ohms)) for r in installation.isolation_readings.all()]
            jours = jours_avant_franchissement_seuil(
                releves, float(installation.isolation_seuil_ohms), sens="BAISSE"
            )
        verb = f"Dérive détectée sur l'isolement de {installation.designation} : seuil estimé atteint dans {jours} j"
        _signaler_ou_resoudre_derive(
            inst_ct, object_id, _destinataires_installation(installation), verb, jours is not None
        )

        # Heures de marche : dérive à la hausse vers le seuil de chaque entretien au compteur.
        releves_heures = [(r.date, float(r.hours)) for r in installation.hour_readings.all()]
        for maintenance in installation.maintenances.all():
            if maintenance.mode_declenchement not in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX):
                continue
            if not maintenance.seuil_heures:
                continue
            seuil = float(maintenance.derniere_echeance_heures or 0) + float(maintenance.seuil_heures)
            jours = jours_avant_franchissement_seuil(releves_heures, seuil, sens="HAUSSE")
            object_id = f"{maintenance.id}:DERIVE_HEURES"
            verb = (
                f"Dérive détectée sur les heures de marche de {installation.designation} : "
                f"entretien '{maintenance.title}' - seuil estimé atteint dans {jours} j"
            )
            _signaler_ou_resoudre_derive(
                maint_ct, object_id, _destinataires_installation(installation), verb, jours is not None
            )

    return {"status": "ok"}


def _digest_journee(offset_jours, champ_heure, prefixe, heure_defaut):
    """Construit et envoie le digest quotidien « Ma journée »/« Ma journée de
    demain » : parcourt les marins actifs, compare l'heure courante à leur
    préférence (`champ_heure` sur UserProfile — même pattern que les commandes
    generate_installation_notifications/generate_installation_maintenance_notifications,
    qui comparent déjà UserProfile.notification_time à l'heure courante),
    récupère les événements du jour visé via calendar_app.evenements_utilisateur_jour
    (même agrégation que le calendrier personnel, pas de système parallèle) et
    crée une notification résumée. Aucune notification si la journée est vide
    (pas de rappel pour rien), et pas de doublon en cas d'exécution répétée le
    même jour (get_or_create sur le résumé, qui inclut la date)."""
    today = timezone.localdate()
    target_date = today + timedelta(days=offset_jours)
    now_local = timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0)
    created = 0

    for profile in UserProfile.objects.select_related("user").filter(user__is_active=True):
        pref = getattr(profile, champ_heure, None) or heure_defaut
        if (now_local.hour, now_local.minute) != (pref.hour, pref.minute):
            continue

        evenements = evenements_utilisateur_jour(profile.user, target_date)
        nb_maintenances = len(evenements["maintenances"])
        nb_formations = len(evenements["formations"])
        nb_personnels = len(evenements["personnels"])
        if not (nb_maintenances or nb_formations or nb_personnels):
            continue

        parts = []
        if nb_maintenances:
            parts.append(f"{nb_maintenances} maintenance(s)")
        if nb_formations:
            parts.append(f"{nb_formations} formation(s)")
        if nb_personnels:
            parts.append(f"{nb_personnels} événement(s) personnel(s)")
        verb = f"{prefixe}: {', '.join(parts)} le {target_date.strftime('%d/%m/%Y')}"

        _, cree = Notification.objects.get_or_create(
            user=profile.user, verb=verb, defaults={"level": NotificationLevel.INFO}
        )
        if cree:
            created += 1

    return {"status": "ok", "created": created}


@shared_task
def notify_ma_journee():
    """« Ma journée » : chaque matin, résume au marin ce qui figure à son
    calendrier personnel aujourd'hui (maintenances assignées, formations,
    événements personnels libres), à l'heure choisie dans ses réglages
    (UserProfile.notification_time, par défaut 08:00 — même champ que les
    alertes d'échéance d'installations, qui servent déjà ce même besoin de
    point du matin)."""
    return _digest_journee(
        offset_jours=0,
        champ_heure="notification_time",
        prefixe="Ma journée",
        heure_defaut=dt_time(8, 0),
    )


@shared_task
def notify_ma_journee_demain():
    """« Ma journée de demain » : en fin de journée, anticipe ce qui figure au
    calendrier personnel du marin le lendemain, avant qu'il ne quitte son
    poste. Même principe que notify_ma_journee, décalé d'un jour et sur
    l'heure du soir (UserProfile.notification_time_soir, par défaut 18:00)."""
    return _digest_journee(
        offset_jours=1,
        champ_heure="notification_time_soir",
        prefixe="Ma journée de demain",
        heure_defaut=dt_time(18, 0),
    )
