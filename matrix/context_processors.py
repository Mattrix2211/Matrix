from datetime import timedelta, date
from django.utils import timezone
from django.urls import reverse
from accounts.models import Roles
from assets.models import Installation, InstallationIsolationReading, InstallationVibrationReading
from matrix.core.contexte_batiment import batiment_courant, selecteur_batiment
from matrix.core.navigation import construire_navigation
from notifications.models import Notification


def _add_months(d: date, months: int) -> date:
    # Ajoute un nombre de mois en conservant le jour autant que possible
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    # Ajuste le jour en fonction du mois résultant
    from calendar import monthrange
    day = min(d.day, monthrange(y, m)[1])
    return date(y, m, day)


def _human_delta(days: int) -> str:
    if days == 0:
        return "aujourd’hui"
    if days > 0:
        return f"dans {days} j"
    return f"depuis {-days} j"


def _dernier_par_installation(queryset, champ_installation="installation_id"):
    """Retourne {installation_id: dernier enregistrement} à partir d'un queryset
    déjà trié du plus récent au plus ancien (ordering par défaut des modèles de
    relevés d'installation) — une seule requête groupée quel que soit le nombre
    d'installations, au lieu d'une requête par installation (même pattern que
    reports/services.py::_dernier_par_installation et
    assets/web_views.py::InstallationListView.get_context_data)."""
    resultat = {}
    for obj in queryset:
        cle = getattr(obj, champ_installation)
        if cle not in resultat:
            resultat[cle] = obj
    return resultat


def installations_notifications(request):
    """
    Construit une liste de notifications d’échéance pour les installations
    - Vibration: selon le dernier état A/B/C et les paramètres vib_days_*
    - Isolement: selon la périodicité et la dernière mesure
    Affiche les items dont l’échéance est dans 7 jours (warning) ou passée (danger).
    """
    notifs = []
    try:
        today = timezone.localdate()
        # Requêtes groupées (installation_id__in=...) plutôt qu'un .first() par
        # installation : ce context processor s'exécute sur CHAQUE page du site,
        # le nombre de requêtes ne doit donc pas dépendre du nombre d'installations.
        installations = list(Installation.objects.all())
        installation_ids = [inst.id for inst in installations]
        derniers_vibrations = _dernier_par_installation(
            InstallationVibrationReading.objects.filter(installation_id__in=installation_ids)
        )
        derniers_isolements = _dernier_par_installation(
            InstallationIsolationReading.objects.filter(installation_id__in=installation_ids)
        )

        for inst in installations:
            # Vibration
            vib = derniers_vibrations.get(inst.id)
            if vib:
                days_map = {
                    "A": getattr(inst, "vib_days_a", 180),
                    "B": getattr(inst, "vib_days_b", 90),
                    "C": getattr(inst, "vib_days_c", 30),
                }
                delta_days = days_map.get(vib.state, 90)
                next_date = vib.date + timedelta(days=delta_days)
                days = (next_date - today).days
                if days <= 7:
                    level = "danger" if days <= 0 else "warning"
                    notifs.append({
                        "level": level,
                        "title": f"Vibration — {inst.designation}",
                        "subtitle": f"Échéance le {next_date.strftime('%d/%m/%Y')} ({_human_delta(days)})",
                        "url": f"/installations/{inst.id}/?tab=vibration",
                        "days": days,
                    })
            # Isolement
            iso = derniers_isolements.get(inst.id)
            if iso:
                per = getattr(inst, "iso_periodicity", "M")
                months = 1 if per == "M" else 3 if per == "T" else 12
                next_date = _add_months(iso.date, months)
                days = (next_date - today).days
                if days <= 7:
                    level = "danger" if days <= 0 else "warning"
                    notifs.append({
                        "level": level,
                        "title": f"Isolement — {inst.designation}",
                        "subtitle": f"Échéance le {next_date.strftime('%d/%m/%Y')} ({_human_delta(days)})",
                        "url": f"/installations/{inst.id}/?tab=isolement",
                        "days": days,
                    })
    except Exception:
        # Ne pas bloquer le rendu si un souci survient
        pass
    # Dédoublonnage par (title, url)
    seen = set()
    dedup = []
    for n in notifs:
        key = (n.get("title"), n.get("url"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(n)
    dedup.sort(key=lambda n: n.get("days", 9999))
    return {
        "notifications": dedup,
        "notifications_count": len(dedup),
    }


def compteur_notifications(request):
    """Notifications non lues du marin connecté : une seule requête COUNT,
    aucune pour un anonyme."""
    utilisateur = getattr(request, "user", None)
    if not utilisateur or not utilisateur.is_authenticated:
        return {}
    return {"notifications_non_lues": Notification.objects.filter(user=utilisateur, is_read=False).count()}


def theme_utilisateur(request):
    """Thème d'affichage du marin connecté (« clair » par défaut, « sombre » sur choix manuel)."""
    utilisateur = getattr(request, "user", None)
    profil = getattr(utilisateur, "profile", None) if utilisateur and utilisateur.is_authenticated else None
    return {"theme_utilisateur": profil.theme if profil else "clair"}


def navigation_laterale(request):
    """Barre latérale (docs/UX.md §7) : groupes visibles selon les droits et les
    modules du bâtiment, entrée courante, état replié mémorisé dans le profil."""
    utilisateur = getattr(request, "user", None)
    if not utilisateur or not utilisateur.is_authenticated:
        return {}
    profil = getattr(utilisateur, "profile", None)
    return {
        "navigation_laterale": construire_navigation(utilisateur, request.path),
        "barre_laterale_repliee": bool(profil and profil.barre_laterale_repliee),
    }


def barre_superieure(request):
    """Identité et contexte de la barre supérieure (docs/UX.md §8) : nom, grade et
    rôle du marin connecté, bâtiment courant et, pour un utilisateur à terre qui
    suit plusieurs bâtiments, la liste des bâtiments de son périmètre."""
    utilisateur = getattr(request, "user", None)
    if not utilisateur or not utilisateur.is_authenticated:
        return {}
    profil = getattr(utilisateur, "profile", None)
    if utilisateur.is_superuser:
        role = Roles.MASTER_ADMIN.label
    else:
        role = profil.get_role_display() if profil and profil.role else Roles.EQUIPIER.label
    batiments = selecteur_batiment(utilisateur)
    return {
        "identite_utilisateur": {
            "nom": utilisateur.get_full_name() or utilisateur.username,
            "grade": profil.grade if profil else "",
            "role": role,
            "fonction": profil.fonction_service if profil else "",
        },
        "batiment_courant": batiment_courant(request, batiments),
        "batiments_selectionnables": batiments,
    }
