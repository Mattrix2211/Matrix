from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from assets.fiche_flotte import chaine, cle_gamme, descendants, fiches_applicables
from assets.fiche_maintenance import jours_de_gamme
from assets.models import Asset, CategorieCatalogue, InstallationMaintenance
from .models import MaintenancePlan, MaintenanceOccurrence


def _creer_occurrences(plan, asset, today, until):
    """Occurrences du plan pour ce matériel jusqu'à `until`, dans le prolongement de la dernière déjà planifiée :
    relancer la génération chaque jour ne décale donc pas la grille et ne crée rien de plus."""
    derniere = (MaintenanceOccurrence.objects.filter(plan=plan, asset=asset).exclude(status="CANCELLED")
                .order_by("-scheduled_for").values_list("scheduled_for", flat=True).first())
    pas = timedelta(days=plan.every_n_days or 90)
    d = today if derniere is None else max(today, derniere + pas)
    while d <= until:
        MaintenanceOccurrence.objects.get_or_create(plan=plan, asset=asset, scheduled_for=d, defaults={"status": "PLANNED"})
        d += pas


def retirer_occurrences_remplacees(fiche, today=None):
    """Une sous-catégorie vient de publier sa propre fiche pour cette gamme : les occurrences futures non commencées
    du parent, pour les articles de cette sous-catégorie, sont annulées (les commencées et terminées restent)."""
    cle = cle_gamme(fiche)
    if cle is None:
        return 0
    today = today or timezone.localdate()
    noeuds = chaine(fiche.categorie)
    total = 0
    for parent in InstallationMaintenance.objects.filter(niveau="FLOTTE", categorie_id__in=[n.pk for n in noeuds[1:]]):
        if cle_gamme(parent) != cle:
            continue
        for categorie in CategorieCatalogue.objects.filter(pk__in=descendants(fiche.categorie)):
            if fiches_applicables(categorie).get(cle) != fiche:
                continue
            total += MaintenanceOccurrence.objects.filter(
                plan__fiche=parent, asset__article_catalogue__categorie=categorie, status__in=["PLANNED", "ASSIGNED"],
                scheduled_for__gte=today, execution__isnull=True).update(status="CANCELLED")
    return total


def generer_occurrences_fiches_flotte(today, until):
    """Occurrences du matériel suivi par une fiche flotte : chaque exemplaire reçoit la fiche de la
    catégorie la plus proche de son article, gamme par gamme."""
    fiches = InstallationMaintenance.objects.filter(niveau="FLOTTE", categorie__isnull=False, mode_declenchement="CALENDRIER")
    for fiche in fiches.select_related("categorie"):
        cle = cle_gamme(fiche)
        if cle is None:
            continue
        plan, _ = MaintenancePlan.objects.update_or_create(
            fiche=fiche, scope="FICHE",
            defaults={"name": fiche.title, "every_n_days": jours_de_gamme(fiche), "expected_duration_min": fiche.planned_duration_min or 30})
        retenue = {}
        exemplaires = Asset.objects.filter(article_catalogue__categorie_id__in=descendants(fiche.categorie))
        for asset in exemplaires.select_related("article_catalogue__categorie"):
            categorie = asset.article_catalogue.categorie
            if categorie.pk not in retenue:
                retenue[categorie.pk] = fiches_applicables(categorie).get(cle) == fiche
            if retenue[categorie.pk]:
                _creer_occurrences(plan, asset, today, until)


@shared_task
def generate_occurrences(days_ahead: int = 90):
    today = timezone.localdate()
    until = today + timedelta(days=days_ahead)
    for plan in MaintenancePlan.objects.all():
        # naive generation: every_n_days from today for assets in scope
        if plan.scope == "ASSET_TYPE" and plan.asset_type:
            assets = plan.asset_type.assets.all()
        elif plan.scope == "ASSET" and plan.asset:
            assets = [plan.asset]
        else:
            continue
        for asset in assets:
            _creer_occurrences(plan, asset, today, until)
    generer_occurrences_fiches_flotte(today, until)
    return {"status": "ok"}

@shared_task
def compute_overdue():
    today = timezone.localdate()
    qs = MaintenanceOccurrence.objects.filter(status__in=["PLANNED", "ASSIGNED"], scheduled_for__lt=today)
    return qs.update(status="OVERDUE")

@shared_task
def generate_installation_occurrences(days_ahead: int = 90):
    """Génère les occurrences de maintenance (calendrier et/ou compteur) pour les
    installations fixes, équivalent de generate_occurrences pour le matériel mobile.

    Enveloppe la commande de gestion du même nom (qui porte toute la logique métier
    et ses tests) afin de la rendre planifiable quotidiennement via Celery Beat.
    """
    call_command("generate_installation_occurrences", days_ahead=days_ahead)
    return {"status": "ok"}
