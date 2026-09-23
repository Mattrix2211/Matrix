"""Génération intelligente d'une proposition de répartition (VISION_MATRIX_2_0.md
§7.3, cahier des charges §11, tâche Notion « Génération intelligente des
listes de service : proposition automatique de répartition »).

Le moteur ne fait JAMAIS d'affectation directe en base : il calcule une
PROPOSITION (pour chaque créneau non affecté d'une liste en brouillon, les
marins éligibles et celui recommandé) affichée au chef de liste, qui
accepte, modifie créneau par créneau (en choisissant un autre marin dans la
liste déroulante) ou refuse intégralement, puis applique explicitement —
cf. quarts/web_views.py::_generer_proposition / _appliquer_proposition.
Rien n'est écrit tant que le chef ne clique pas sur « Appliquer la
proposition » (principe VISION §7.3 : « Matrix ne doit jamais imposer
aveuglément une affectation »).

Heuristique retenue (pas de machine learning — une simple rotation
équitable suffit, cf. cadrage de la tâche) ; choix de cadrage documentés
dans le compte-rendu [Dev] de la tâche Notion, à confirmer/ajuster par le
métier plutôt que tranchés unilatéralement :

- Exclusions STRICTES (le marin n'apparaît jamais dans les éligibles) :
  * absence déclarée chevauchant le créneau (absences.models.Absence,
    déclarée ou déjà validée — même principe que
    quarts.echanges.absences_marin) ;
  * habilitation manquante si la liste l'exige (ServiceGarde.formations_
    requises — Quart ne porte pas ce champ, donc aucune exclusion de ce
    type ne s'applique à une liste de quarts) ;
  * déjà affecté à un autre créneau chevauchant, sur une AUTRE liste déjà
    publiée (quarts.echanges.conflits_marin, réutilisé tel quel) ou sur un
    créneau de CETTE MÊME liste (déjà affecté manuellement, ou proposé un
    peu plus tôt dans ce même calcul — cf. `_intervalles_deja_pris`).
  Hypothèse documentée : les conflits avec une AUTRE liste encore en
  brouillon ne sont pas détectés (même limite déjà acceptée pour les
  échanges de service, cf. quarts/echanges.py) — un brouillon n'est pas
  définitif tant qu'il n'est pas publié.

- Score d'équilibrage parmi les marins restants (le plus faible score est
  proposé en premier) : charge récente déjà connue du marin — réutilise le
  compteur d'équité existant (quarts.services.compteurs_equite) pour une
  liste de services de garde comme demandé par le cadrage ; pour une liste
  de quarts (qui n'a pas cette notion d'équité par catégorie de jour), repli
  générique sur le nombre de créneaux publiés (quarts ET gardes confondus)
  des `FENETRE_CHARGE_GENERIQUE_JOURS` derniers jours — plus un marin a été
  sollicité récemment, plus son score augmente, y compris au fil du calcul
  en cours (un marin proposé une première fois voit son score augmenter
  avant le créneau suivant, pour répartir entre plusieurs marins éligibles
  plutôt que de toujours proposer le même).

- Non-répétition immédiate (contrainte simple, cadrage à confirmer) : le
  marin proposé sur le créneau immédiatement précédent du MÊME poste est
  écarté des candidats préférés pour le créneau suivant du même poste, SAUF
  s'il est le seul marin éligible restant — jamais de créneau laissé vide
  s'il existe au moins un candidat possible.

- Si aucun marin n'est éligible pour un créneau, celui-ci est renvoyé avec
  `propose=None` et `aucun_eligible=True` : à afficher clairement au chef de
  liste plutôt que de forcer une affectation (cf. docstring de module)."""
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.utils import timezone

from .echanges import absences_marin, conflits_marin, habilitations_manquantes
from .models import CreneauQuart, CreneauServiceGarde, ServiceGarde, marins_du_perimetre
from .services import compteurs_equite

User = get_user_model()

# Fenêtre de repli générique (liste de quarts, sans notion d'équité dédiée) :
# nombre de jours sur lesquels compter les créneaux publiés récents d'un
# marin pour estimer sa charge — valeur raisonnable par défaut, pas une
# règle métier figée (aucun impact sur le schéma, ajustable ici si besoin).
FENETRE_CHARGE_GENERIQUE_JOURS = 90


def _charge_recente(liste, marins_ids):
    """Charge récente de chaque marin de `marins_ids`, point de départ du
    score d'équilibrage (plus la valeur est basse, plus le marin est
    prioritaire pour être proposé)."""
    if isinstance(liste, ServiceGarde):
        # Réutilise le compteur d'équité déjà existant (cadrage de la tâche :
        # « regarde le compteur d'équité existant sur ServiceGarde si
        # présent ») : total des 3 catégories sur l'année en cours.
        bruts = compteurs_equite(marins_ids)
        return {marin_id: sum(bruts[marin_id]["annee"].values()) for marin_id in marins_ids}

    depuis = timezone.now() - timezone.timedelta(days=FENETRE_CHARGE_GENERIQUE_JOURS)
    charge = defaultdict(int)
    for modele, statut_lookup in (
        (CreneauQuart, "quart__statut"), (CreneauServiceGarde, "service_garde__statut"),
    ):
        filtres = {statut_lookup: "PUBLIEE", "marin_id__in": marins_ids, "debut__gte": depuis}
        for marin_id in modele.objects.filter(**filtres).values_list("marin_id", flat=True):
            charge[marin_id] += 1
    return {marin_id: charge.get(marin_id, 0) for marin_id in marins_ids}


def _intervalles_deja_pris(liste):
    """Créneaux déjà affectés de CETTE liste (marin non nul), par marin —
    sert à empêcher la proposition de chevaucher une affectation déjà
    présente sur la même liste (manuelle ou fraîchement proposée dans ce
    calcul, cf. proposer_repartition)."""
    intervalles = defaultdict(list)
    for c in liste.creneaux.exclude(marin__isnull=True).only("marin_id", "debut", "fin"):
        intervalles[c.marin_id].append((c.debut, c.fin))
    return intervalles


def _chevauche(intervalles, debut, fin):
    return any(d < fin and f > debut for d, f in intervalles)


def proposer_repartition(liste):
    """Calcule la proposition de répartition des créneaux non affectés de
    `liste` (Quart ou ServiceGarde en brouillon). Ne modifie rien en base.

    Renvoie une liste ordonnée par créneau (`debut` croissant) de dicts :
    {"creneau": ..., "eligibles": [User, ...] (triés par score croissant),
     "propose": User ou None, "aucun_eligible": bool}."""
    creneaux = list(liste.creneaux.select_related("marin").filter(marin__isnull=True).order_by("debut", "pk"))
    if not creneaux:
        return []

    marins = list(User.objects.filter(marins_du_perimetre(liste)).select_related("profile").distinct())
    charge = _charge_recente(liste, [m.pk for m in marins])
    intervalles_liste = _intervalles_deja_pris(liste)

    # Dernier marin affecté par poste (déjà présent sur la liste, ou proposé
    # au fil de ce calcul) : mémoire de la contrainte de non-répétition
    # immédiate, mise à jour créneau après créneau.
    dernier_marin_par_poste = {}
    for c in sorted(
        (c for c in liste.creneaux.all() if c.marin_id), key=lambda c: c.debut,
    ):
        dernier_marin_par_poste[c.poste] = c.marin_id

    proposition = []
    for creneau in creneaux:
        eligibles = []
        for marin in marins:
            if _chevauche(intervalles_liste.get(marin.pk, []), creneau.debut, creneau.fin):
                continue
            if conflits_marin(marin, creneau, ignorer_ids=[]):
                continue
            if isinstance(creneau, CreneauServiceGarde) and habilitations_manquantes(marin, creneau):
                continue
            if absences_marin(marin, creneau):
                continue
            eligibles.append(marin)
        eligibles.sort(key=lambda m: (charge.get(m.pk, 0), (m.get_full_name() or m.username).lower()))

        propose = None
        if eligibles:
            marin_precedent = dernier_marin_par_poste.get(creneau.poste)
            candidats_preferes = [m for m in eligibles if m.pk != marin_precedent]
            propose = (candidats_preferes or eligibles)[0]
            charge[propose.pk] = charge.get(propose.pk, 0) + 1
            intervalles_liste[propose.pk].append((creneau.debut, creneau.fin))

        dernier_marin_par_poste[creneau.poste] = propose.pk if propose else None
        proposition.append({
            "creneau": creneau, "eligibles": eligibles, "propose": propose,
            "aucun_eligible": not eligibles,
        })
    return proposition
