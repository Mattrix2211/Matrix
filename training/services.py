"""Calculs pour la carte / l'arbre de compétences (formations organisées par
niveau de profondeur selon leur chaîne de prérequis, avec l'état de chaque
formation pour un marin donné)."""
from collections import defaultdict

from django.utils import timezone

from .models import TrainingRecord

# États possibles d'une formation pour un marin donné, affichés sur l'arbre de
# compétences (code couleur défini dans matrix/templates/training/arbre_competences.html).
ETAT_VALIDE = "VALIDE"
ETAT_DISPONIBLE = "DISPONIBLE"
ETAT_VERROUILLE = "VERROUILLE"

# Libellé affiché pour les formations sans catégorie (domaine métier) renseignée.
CATEGORIE_NON_RENSEIGNEE = "Non catégorisées"


def calculer_niveaux(courses):
    """Calcule la profondeur topologique de chaque formation (0 = sans
    prérequis, 1 = ne dépend que de formations de niveau 0, etc.) à partir de
    sa chaîne de prérequis. Renvoie un dict {course_id: niveau}.

    Une boucle de prérequis est censée être impossible (protection à
    l'écriture, cf. training/models.py::_verifier_absence_de_cycle_prerequis) ;
    on se protège quand même d'une récursion infinie si une incohérence
    existait déjà en base, en traitant une formation "en cours de calcul"
    comme un prérequis de niveau 0."""
    niveaux = {}
    en_cours = set()

    def niveau_de(course):
        if course.pk in niveaux:
            return niveaux[course.pk]
        if course.pk in en_cours:
            return 0
        en_cours.add(course.pk)
        prerequis = list(course.prerequisites.all())
        n = 0 if not prerequis else 1 + max(niveau_de(p) for p in prerequis)
        en_cours.discard(course.pk)
        niveaux[course.pk] = n
        return n

    for c in courses:
        niveau_de(c)
    return niveaux


def calculer_carte_competences(courses, user, reference_date=None):
    """Calcule, pour chaque formation de `courses`, son niveau de profondeur et
    son état pour `user` (validé / disponible / verrouillé), en un nombre
    minimal de requêtes (une pour les validations en cours, indépendamment du
    nombre de formations affichées — les prérequis sont supposés déjà
    prefetch_related('prerequisites') par l'appelant).

    Renvoie une liste de dicts {course, niveau, etat, prerequis_manquants}."""
    reference_date = reference_date or timezone.localdate()
    courses = list(courses)
    # Les validations à vérifier concernent aussi bien les formations affichées
    # que leurs prérequis (qui peuvent ne pas faire partie de `courses`, par
    # exemple si l'appelant n'a passé qu'un sous-ensemble des formations d'un
    # secteur) — sans cela, un prérequis validé mais absent de `courses` serait
    # à tort compté comme manquant.
    ids_a_verifier = set()
    for c in courses:
        ids_a_verifier.add(c.id)
        ids_a_verifier.update(p.id for p in c.prerequisites.all())
    validees_ids = set(
        TrainingRecord.objects.filter(
            user=user, course_id__in=ids_a_verifier, expires_at__gte=reference_date
        ).values_list("course_id", flat=True)
    )
    niveaux = calculer_niveaux(courses)
    resultats = []
    for c in courses:
        prerequis = list(c.prerequisites.all())
        manquants = [p for p in prerequis if p.id not in validees_ids]
        if c.id in validees_ids:
            etat = ETAT_VALIDE
        elif manquants:
            etat = ETAT_VERROUILLE
        else:
            etat = ETAT_DISPONIBLE
        resultats.append({
            "course": c,
            "niveau": niveaux[c.id],
            "etat": etat,
            "prerequis_manquants": manquants,
        })
    return resultats


def regrouper_par_niveau(carte):
    """Regroupe le résultat de calculer_carte_competences() par niveau, sous
    forme de liste triée [(niveau, [items...]), ...] — pratique pour l'affichage
    en colonnes de l'arbre de compétences."""
    par_niveau = defaultdict(list)
    for item in carte:
        par_niveau[item["niveau"]].append(item)
    return sorted(par_niveau.items())


def regrouper_par_categorie(carte):
    """Regroupe le résultat de calculer_carte_competences() par catégorie de
    formation (domaine métier, TrainingCourse.category), chaque catégorie
    étant à son tour subdivisée par niveau via regrouper_par_niveau() — c'est
    cette fonction qui pilote l'affichage de l'arbre de compétences par
    catégorie. Le calcul du graphe lui-même (niveaux, anti-cycle) reste
    toujours fait sur l'ensemble des formations passées à
    calculer_carte_competences ; seul cet affichage est réparti par catégorie
    (un prérequis d'une autre catégorie garde donc son niveau réel).

    Renvoie une liste triée par ordre alphabétique de tuples
    (nom_categorie, niveaux) ; les formations sans catégorie renseignée sont
    réunies dans un groupe CATEGORIE_NON_RENSEIGNEE toujours affiché en
    dernier plutôt que d'être cachées ou de faire planter l'affichage."""
    par_categorie = defaultdict(list)
    for item in carte:
        categorie = (item["course"].category or "").strip()
        par_categorie[categorie].append(item)
    noms_categories = sorted(c for c in par_categorie if c)
    groupes = [(nom, regrouper_par_niveau(par_categorie[nom])) for nom in noms_categories]
    if "" in par_categorie:
        groupes.append((CATEGORIE_NON_RENSEIGNEE, regrouper_par_niveau(par_categorie[""])))
    return groupes
