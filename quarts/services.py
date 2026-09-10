"""Compteurs d'équité par marin sur les services de garde (Phase 2 — Vie
quotidienne, tâche Notion « Services/gardes : compteur d'équité par marin »).

Un compteur EN LECTURE SEULE : il n'automatise aucune répartition (hors
périmètre, explicitement exclu par le cadrage validé sur la tâche Notion). Il
aide le chef de liste à affecter équitablement à la main, et donne à chaque
marin de la transparence sur sa propre situation.

Porte uniquement sur ServiceGarde, pas sur Quart (hypothèse de cadrage
documentée dans le commentaire [Dev] de la tâche Notion, laissée au choix du
dev par le cadrage métier) : les rotations courtes de type barre/passerelle
ne relèvent pas de la même logique d'équité perçue qu'une garde longue, à
réévaluer si le besoin s'étend un jour à Quart.

Trois catégories strictement séparées, jamais un score pondéré unique
(cadrage validé) : semaine (lundi-jeudi), vendredi, week-end (samedi +
dimanche) — classées sur la date de DÉBUT du créneau (un créneau chevauchant
minuit n'est donc compté que sur son jour de début, comme une seule ligne de
tableur ; hypothèse documentée faute de règle métier plus précise dans le
cadrage). Seuls les créneaux affectés à un marin sur une liste déjà PUBLIÉE
comptent, jamais les brouillons (cadrage validé, cohérent avec l'intégration
calendrier déjà livrée)."""
from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import CreneauServiceGarde, ServiceGarde, marins_du_perimetre

User = get_user_model()

CATEGORIE_SEMAINE = "semaine"
CATEGORIE_VENDREDI = "vendredi"
CATEGORIE_WEEKEND = "weekend"


def _categorie_jour(date_):
    """Catégorie d'équité d'une date : semaine (lundi-jeudi), vendredi, ou
    week-end (samedi + dimanche)."""
    jour_semaine = date_.weekday()  # lundi=0 ... dimanche=6
    if jour_semaine == 4:
        return CATEGORIE_VENDREDI
    if jour_semaine >= 5:
        return CATEGORIE_WEEKEND
    return CATEGORIE_SEMAINE


def _debut_journee_locale(date_):
    """Convertit une date en datetime aware au tout début de journée (fuseau
    local), pour borner les requêtes sur le champ `debut` (DateTimeField)."""
    return timezone.make_aware(datetime.combine(date_, time.min))


def _bornes_mois_en_cours(aujourdhui):
    debut = aujourdhui.replace(day=1)
    # Passer par le 28 du mois +4 jours tombe toujours dans le mois suivant,
    # quel que soit le nombre de jours du mois courant (28/29/30/31) : évite
    # de dépendre du module `calendar` pour ce seul calcul.
    fin_exclue = (debut.replace(day=28) + timezone.timedelta(days=4)).replace(day=1)
    return _debut_journee_locale(debut), _debut_journee_locale(fin_exclue)


def _bornes_annee_en_cours(aujourdhui):
    debut = aujourdhui.replace(month=1, day=1)
    fin_exclue = debut.replace(year=debut.year + 1)
    return _debut_journee_locale(debut), _debut_journee_locale(fin_exclue)


def _compteur_vide():
    return {CATEGORIE_SEMAINE: 0, CATEGORIE_VENDREDI: 0, CATEGORIE_WEEKEND: 0}


def _repartir_par_marin(creneaux):
    """Répartit un ensemble de créneaux (marin déjà connu, non nul) par marin
    et par catégorie de jour (date de début, fuseau local)."""
    compteurs = {}
    for creneau in creneaux:
        compteur = compteurs.setdefault(creneau.marin_id, _compteur_vide())
        compteur[_categorie_jour(timezone.localtime(creneau.debut).date())] += 1
    return compteurs


def _creneaux_publies_periode(marins_ids, depuis, jusqu_a_exclu):
    """Créneaux de service de garde à prendre en compte : uniquement les
    listes PUBLIÉES (jamais les brouillons), affectés à l'un des marins
    demandés, dont le début tombe dans la période [depuis, jusqu_a_exclu)."""
    return CreneauServiceGarde.objects.filter(
        service_garde__statut=ServiceGarde.STATUT_PUBLIEE,
        marin_id__in=marins_ids,
        debut__gte=depuis,
        debut__lt=jusqu_a_exclu,
    ).only("marin_id", "debut")


def compteurs_equite(marins_ids, aujourdhui=None):
    """Compteurs d'équité (mois en cours + année en cours) pour chaque marin
    de `marins_ids`, sous la forme :
    {marin_id: {"mois": {"semaine": n, "vendredi": n, "weekend": n},
                "annee": {...}}}
    Un marin sans aucun créneau obtient des compteurs à zéro plutôt que
    d'être absent du résultat — "0 garde" reste une information utile pour le
    chef de liste comme pour le marin lui-même."""
    aujourdhui = aujourdhui or timezone.localdate()
    marins_ids = list(marins_ids)

    debut_mois, fin_mois_exclue = _bornes_mois_en_cours(aujourdhui)
    debut_annee, fin_annee_exclue = _bornes_annee_en_cours(aujourdhui)

    par_marin_mois = _repartir_par_marin(_creneaux_publies_periode(marins_ids, debut_mois, fin_mois_exclue))
    par_marin_annee = _repartir_par_marin(_creneaux_publies_periode(marins_ids, debut_annee, fin_annee_exclue))

    return {
        marin_id: {
            "mois": par_marin_mois.get(marin_id, _compteur_vide()),
            "annee": par_marin_annee.get(marin_id, _compteur_vide()),
        }
        for marin_id in marins_ids
    }


def compteur_equite_marin(user, aujourdhui=None):
    """Compteurs d'équité d'un seul marin — son propre total (transparence
    accordée par le cadrage à chaque marin sur sa propre situation, jamais
    celle des autres). Même calcul que compteurs_equite, pour un seul
    utilisateur."""
    return compteurs_equite([user.pk], aujourdhui=aujourdhui)[user.pk]


def _ajouter_visuels(resultat, periode):
    """Ajoute à chaque élément de `resultat` un dictionnaire `<periode>_visuel`
    donnant, pour chaque catégorie, sa valeur ET son pourcentage relatif au
    maximum observé dans le périmètre pour cette période — sert à dimensionner
    les mini jauges visuelles du chef de liste (CLAUDE.md §5 : préférer une
    représentation visuelle à un tableau de chiffres bruts), sans inventer de
    barème arbitraire (le maximum est toujours celui réellement constaté).

    Le maximum est calculé SÉPARÉMENT par catégorie (semaine / vendredi /
    week-end), jamais un maximum global partagé entre les 3 : la catégorie
    "semaine" compte structurellement plus de jours possibles (lundi-jeudi)
    que "vendredi" (1 jour) ou "week-end" (2 jours), donc un maximum global
    serait presque toujours tiré par "semaine" et afficherait des jauges
    "vendredi"/"week-end" trompeusement quasi-vides même pour un marin au
    maximum réellement observé sur SA catégorie (bug signalé par le Tech
    Lead)."""
    maximums = {
        categorie: max((item[periode][categorie] for item in resultat), default=0)
        for categorie in (CATEGORIE_SEMAINE, CATEGORIE_VENDREDI, CATEGORIE_WEEKEND)
    }
    for item in resultat:
        item[f"{periode}_visuel"] = {
            categorie: {
                "valeur": valeur,
                "pourcentage": round(valeur / maximums[categorie] * 100) if maximums[categorie] else 0,
            }
            for categorie, valeur in item[periode].items()
        }


def compteurs_equite_perimetre(liste, aujourdhui=None):
    """Compteurs d'équité détaillés de tous les marins du périmètre d'une
    liste de services de garde (`liste`) — vue réservée au chef de liste
    gérant cette liste (contrôlé côté vue, cf. peut_gerer_liste). Renvoie une
    liste de dicts {"marin": User, "mois": {...}, "annee": {...},
    "mois_visuel": {...}, "annee_visuel": {...}}, triée par nom affiché."""
    marins = list(
        User.objects.filter(marins_du_perimetre(liste)).select_related("profile")
        .order_by("username").distinct()
    )
    bruts = compteurs_equite([marin.pk for marin in marins], aujourdhui=aujourdhui)
    resultat = [
        {"marin": marin, "mois": bruts[marin.pk]["mois"], "annee": bruts[marin.pk]["annee"]}
        for marin in marins
    ]
    resultat.sort(key=lambda item: (item["marin"].get_full_name() or item["marin"].username).lower())
    _ajouter_visuels(resultat, "mois")
    _ajouter_visuels(resultat, "annee")
    return resultat
