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


def regrouper_par_composantes_connexes(items):
    """Calcule les composantes connexes du graphe non orienté formé par les
    liens de prérequis ENTRE LES FORMATIONS DE `items` (typiquement toutes
    les formations d'une même catégorie) : deux formations reliées directement
    ou indirectement par un prérequis appartiennent à la même composante ;
    deux formations sans aucun lien commun (même transitif) sont deux branches
    indépendantes et forment donc deux composantes distinctes — c'est ce qui
    permet à l'arbre de compétences de les afficher en sous-colonnes côte à
    côte plutôt que de les empiler verticalement l'une sous l'autre (un
    prérequis vers une formation absente de `items`, ex. une autre catégorie,
    n'est pas pris en compte ici : il n'a pas d'incidence sur la disposition
    au sein de CE groupe).

    Renvoie une liste de listes d'items, dans un ordre stable (celui de
    `items`, lui-même hérité de l'ordre alphabétique des titres posé par
    calculer_carte_competences)."""
    par_id = {item["course"].id: item for item in items}
    voisins = defaultdict(set)
    for item in items:
        course_id = item["course"].id
        for prerequis in item["course"].prerequisites.all():
            if prerequis.id in par_id:
                voisins[course_id].add(prerequis.id)
                voisins[prerequis.id].add(course_id)

    visites = set()
    composantes = []
    for item in items:
        course_id = item["course"].id
        if course_id in visites:
            continue
        # Parcours en profondeur (pile explicite) du graphe non orienté pour
        # récupérer tous les identifiants reliés, directement ou non, à cette
        # formation de départ.
        a_visiter = [course_id]
        ids_composante = set()
        while a_visiter:
            courant = a_visiter.pop()
            if courant in ids_composante:
                continue
            ids_composante.add(courant)
            a_visiter.extend(voisins[courant] - ids_composante)
        visites |= ids_composante
        # L'ordre d'origine de `items` (titre alphabétique) est préservé au
        # sein de la composante plutôt que de suivre l'ordre du parcours.
        composantes.append([it for it in items if it["course"].id in ids_composante])
    return composantes


def regrouper_par_categorie(carte):
    """Regroupe le résultat de calculer_carte_competences() par catégorie de
    formation (domaine métier, TrainingCourse.category) ; au sein de chaque
    catégorie, les formations sont d'abord réparties en composantes connexes
    (regrouper_par_composantes_connexes, ci-dessus) — les branches de
    prérequis totalement indépendantes les unes des autres au sein d'une même
    catégorie — puis chaque composante est à son tour subdivisée par niveau
    via regrouper_par_niveau(). C'est cette fonction qui pilote l'affichage
    de l'arbre de compétences : catégories côte à côte, composantes côte à
    côte au sein d'une catégorie, niveaux empilés au sein d'une composante.
    Le calcul du graphe lui-même (niveaux, anti-cycle) reste toujours fait
    sur l'ensemble des formations passées à calculer_carte_competences ;
    seul cet affichage est réparti par catégorie puis par composante (un
    prérequis d'une autre catégorie garde donc son niveau réel).

    Renvoie une liste triée par ordre alphabétique de tuples
    (nom_categorie, composantes), où `composantes` est une liste de listes de
    niveaux (une entrée par composante connexe, elle-même au format renvoyé
    par regrouper_par_niveau) ; les formations sans catégorie renseignée sont
    réunies dans un groupe CATEGORIE_NON_RENSEIGNEE toujours affiché en
    dernier plutôt que d'être cachées ou de faire planter l'affichage."""
    par_categorie = defaultdict(list)
    for item in carte:
        categorie = (item["course"].category or "").strip()
        par_categorie[categorie].append(item)

    def composantes_par_niveau(items):
        return [regrouper_par_niveau(composante) for composante in regrouper_par_composantes_connexes(items)]

    noms_categories = sorted(c for c in par_categorie if c)
    groupes = [(nom, composantes_par_niveau(par_categorie[nom])) for nom in noms_categories]
    if "" in par_categorie:
        groupes.append((CATEGORIE_NON_RENSEIGNEE, composantes_par_niveau(par_categorie[""])))
    return groupes


def _badge_qualification(record, aujourdhui, seuil_bientot_expiree_jours):
    """Classe de badge + libellé pour une qualification (TrainingRecord)
    validée, même palette que logistics/stock_list.html
    (badge-conforme/text-bg-warning/text-bg-danger) : expirée si la date
    d'expiration est passée, bientôt expirée si elle tombe dans le seuil
    d'alerte passé en paramètre, à jour sinon."""
    if record.expires_at < aujourdhui:
        return "text-bg-danger", "Expirée"
    if record.expires_at <= aujourdhui + timezone.timedelta(days=seuil_bientot_expiree_jours):
        return "text-bg-warning", "Bientôt expirée"
    return "badge-conforme", "À jour"


def qualifications_validees_de(user, reference_date=None):
    """Dernière qualification validée (TrainingRecord) par formation pour
    `user`, triée par date d'expiration croissante, avec un badge de statut
    (à jour / bientôt expirée / expirée) attaché à chaque enregistrement.

    Une seule ligne par formation : en cas de renouvellement, seul le dernier
    enregistrement (le plus récent completed_at, created_at en cas d'égalité)
    est conservé — l'ancien enregistrement expiré n'a pas d'intérêt une fois
    remplacé (arbitrage PO, tâche Notion « Mes qualifications » du tableau de
    bord).

    Factorisé ici pour être appelé à l'identique par la carte « Mes
    qualifications » du tableau de bord (dashboard/web_views.py) ET la
    section qualifications de « Mon profil » (accounts/web_views.py), sans
    dupliquer ni la requête ni la règle de badge."""
    # Import différé : notifications.tasks importe training.models, un import
    # en tête de fichier créerait un cycle training <-> notifications au
    # chargement des modules.
    from notifications.tasks import JOURS_ALERTE_EXPIRATION_FORMATION

    aujourdhui = reference_date or timezone.localdate()
    seuil_jours = max(JOURS_ALERTE_EXPIRATION_FORMATION)
    derniere_par_formation = {}
    for qualification in (
        TrainingRecord.objects.select_related("course")
        .filter(user=user)
        .order_by("-completed_at", "-created_at")
    ):
        derniere_par_formation.setdefault(qualification.course_id, qualification)
    qualifications = sorted(derniere_par_formation.values(), key=lambda q: q.expires_at)
    for qualification in qualifications:
        qualification.badge_classe, qualification.badge_libelle = _badge_qualification(
            qualification, aujourdhui, seuil_jours
        )
    return qualifications
