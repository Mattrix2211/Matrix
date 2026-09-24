"""Construction du contexte d'affichage du catalogue de formations
(training/web_views.py::TrainingCourseListView.get_context_data).

Module extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py ») : cette
fonction reste volumineuse car elle assemble en une seule page tout ce qui
peut être visible sur le catalogue (référents, sessions à venir, files des
trois circuits de validation) — un découpage supplémentaire par circuit
aurait nécessité plusieurs allers-retours en base par sous-fonction, contre
un seul passage ici.

Refactor pur : reproduit exactement le comportement d'origine, `view` est
l'instance de TrainingCourseListView (accès à view.request) et `ctx` le
contexte déjà construit par super().get_context_data(**kwargs)."""
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.utils import timezone

from matrix.core.roles import user_role_level

from .formation_perimetre import (
    NIVEAU_REQUIS_VALIDATION_HIERARCHIE_CANDIDATURE,
    _est_referent_formation,
    _marins_perimetre_demandeur,
    _marins_perimetre_hierarchie,
    _marins_validables,
    _peut_creer_formation,
    _peut_demander_places,
    _peut_gerer_brh,
    _peut_gerer_prerequis,
    _peut_gerer_referent_navire,
    _peut_proposer_formation_bord,
    _peut_valider_candidature_brh,
    _utilisateurs_du_navire_q,
    peut_valider_proposition_bord,
)
from .models import (
    NIVEAU_SUPERVISION_GLOBALE_FORMATION,
    CandidatureFormation,
    DemandePlace,
    PersonnelBRH,
    ReferentFormation,
    ReferentFormationNavire,
    TrainingCourse,
    TrainingSession,
    navire_de,
    peut_valider_formation,
)

User = get_user_model()


def construire_contexte_formations(view, ctx):
    request = view.request
    ctx["peut_gerer_prerequis"] = _peut_gerer_prerequis(request.user)
    ctx["peut_creer_formation"] = _peut_creer_formation(request.user)

    # Navire de référence de l'appelant (résolu quel que soit le niveau de
    # son profil, cf. navire_de) : sert à la fois au bloc référent
    # formation du navire ci-dessous ET à la gestion des référents PAR
    # FORMATION (ReferentFormation), désormais toujours scopée au navire
    # de la personne qui gère la page — un chef ne désigne des référents
    # que pour SON propre navire, jamais pour un autre.
    navire_courant = navire_de(request.user)
    ctx["navire_courant"] = navire_courant

    # Référent formation du navire (ReferentFormationNavire) : géré ici
    # pour le NAVIRE DE L'APPELANT uniquement (pas la flotte entière),
    # cohérent avec le principe "espace personnel par marin" — un
    # COMMANDANT+ ne gère que son propre bord.
    ctx["peut_gerer_referent_navire"] = _peut_gerer_referent_navire(request.user)
    if ctx["peut_gerer_referent_navire"] and navire_courant is not None:
        ctx["referent_formation_navire"] = ReferentFormationNavire.objects.filter(
            ship=navire_courant
        ).select_related("user").first()
        ctx["candidats_referent_navire"] = (
            User.objects.filter(_utilisateurs_du_navire_q(navire_courant), is_active=True)
            .select_related("profile")
            .order_by("last_name", "first_name", "username")
            .distinct()
        )

    # Personnels BRH du navire (Circuit B — Candidature individuelle) :
    # géré ici pour le NAVIRE DE L'APPELANT uniquement, même principe que
    # le référent formation du navire ci-dessus, mais PLUSIEURS personnes
    # possibles par navire (PersonnelBRH, FK simple répétable).
    ctx["peut_gerer_brh"] = _peut_gerer_brh(request.user)
    if ctx["peut_gerer_brh"] and navire_courant is not None:
        ctx["personnels_brh"] = list(
            PersonnelBRH.objects.filter(ship=navire_courant).select_related("user")
        )
        ctx["candidats_brh"] = (
            User.objects.filter(_utilisateurs_du_navire_q(navire_courant), is_active=True)
            .select_related("profile")
            .order_by("last_name", "first_name", "username")
            .distinct()
        )

    # Candidats prérequis : catalogue global des formations ACTIVE
    # uniquement (une formation « bord » en attente de validation ou
    # refusée ne peut pas encore servir de prérequis à une autre, cf.
    # Circuit C), l'exclusion de la formation elle-même étant faite côté
    # client (JS, cf. formations.html) puisqu'une seule liste sert à
    # toutes les cartes.
    toutes_formations = list(TrainingCourse.objects.filter(statut_validation="ACTIVE").order_by("title"))
    ctx["candidats_prerequis"] = toutes_formations

    # Catégories déjà utilisées (formations ACTIVE uniquement) : sert à
    # l'autocomplétion du champ catégorie (datalist HTML natif) pour
    # limiter les doublons/fautes de frappe sans imposer de liste fermée,
    # et au filtre déroulant en tête de page.
    ctx["categories_existantes"] = sorted({
        c for c in TrainingCourse.objects.filter(statut_validation="ACTIVE")
        .exclude(category="").values_list("category", flat=True)
    })

    # Candidats référents (ReferentFormation) : les utilisateurs visibles
    # sur le NAVIRE de l'appelant — un chef ne peut désigner de référent
    # que pour son propre navire (cf. navire_courant ci-dessus).
    candidats_referents = []
    if navire_courant is not None:
        candidats_referents = list(
            User.objects.filter(_utilisateurs_du_navire_q(navire_courant))
            .select_related("profile")
            .order_by("username")
            .distinct()
        )
    ctx["candidats_referents"] = candidats_referents

    # Référents déjà désignés, POUR LE NAVIRE DE L'APPELANT uniquement
    # (un autre navire peut avoir désigné d'autres référents pour la même
    # formation globale, non affichés ici) — regroupés par formation pour
    # un accès direct côté template.
    formations = list(ctx["formations"])
    referents_par_formation = defaultdict(list)
    if navire_courant is not None:
        referents_qs = ReferentFormation.objects.filter(
            course_id__in=[f.id for f in formations], ship=navire_courant
        ).select_related("user")
        for r in referents_qs:
            referents_par_formation[r.course_id].append(r.user)
    ctx["referents_par_formation"] = dict(referents_par_formation)

    # Sessions à venir (planifiées, pas encore passées) de chaque formation
    # affichée, avec la place restante et l'état de réservation du marin
    # connecté — réservation self-service (T-FORM), page la plus naturelle
    # pour ça puisque c'est déjà ici que le marin consulte ses formations.
    sessions_qs = (
        TrainingSession.objects.filter(
            course_id__in=[f.id for f in formations],
            status="PLANNED",
            scheduled_at__gte=timezone.now(),
        )
        .select_related("instructor")
        .prefetch_related("reservations", "liste_attente")
        .order_by("scheduled_at")
    )
    sessions_par_formation = defaultdict(list)
    for s in sessions_qs:
        s.deja_reserve = request.user in s.reservations.all()
        # Liste d'attente (T-ATTENTE) : entrées déjà triées FIFO par le
        # prefetch (Meta.ordering de TrainingWaitlistEntry = created_at),
        # aucune requête supplémentaire par session.
        entrees_attente = list(s.liste_attente.all())
        s.nb_en_attente = len(entrees_attente)
        s.mon_entree_attente = next(
            (e for e in entrees_attente if e.user_id == request.user.id), None
        )
        s.ma_position_attente = (
            entrees_attente.index(s.mon_entree_attente) + 1 if s.mon_entree_attente else None
        )
        sessions_par_formation[s.course_id].append(s)
    # Suivi des validations (T-FORM) : compteurs à jour/expirées et
    # dernières validations par formation, affichés directement sur
    # chaque carte sans navigation supplémentaire.
    aujourdhui = timezone.localdate()
    # Circuit B — Candidature individuelle : la candidature la PLUS
    # RÉCENTE du marin connecté pour chaque formation, affichée sur la
    # carte à la place du bouton « Candidater » tant qu'elle est active
    # (cf. candidature_actions.py::_action_candidater_formation, qui
    # bloque un nouveau dépôt tant que la précédente n'est pas allée à son
    # terme). Le queryset est trié du plus récent au plus ancien (Meta.ordering
    # de CandidatureFormation) : setdefault garde la PREMIÈRE occurrence
    # rencontrée par formation, donc la plus récente, plutôt que la dernière
    # (ce que ferait un simple dict comprehension, qui écraserait avec la
    # plus ancienne).
    mes_candidatures_par_course = {}
    for c in CandidatureFormation.objects.filter(marin=request.user).select_related("course"):
        mes_candidatures_par_course.setdefault(c.course_id, c)
    for f in formations:
        f.sessions_a_venir = sessions_par_formation.get(f.id, [])
        f.mes_referents = referents_par_formation.get(f.id, [])
        f.ma_candidature = mes_candidatures_par_course.get(f.id)
        records = list(f.records.all())
        f.nb_a_jour = sum(1 for r in records if r.expires_at >= aujourdhui)
        f.nb_expires = sum(1 for r in records if r.expires_at < aujourdhui)
        f.dernieres_validations = sorted(records, key=lambda r: r.completed_at, reverse=True)[:5]
    ctx["formations"] = formations

    # Peut valider une formation : rôle de supervision globale
    # (COMMANDANT+, comme training.models.peut_valider_formation) OU
    # statut de référent (formation précise ou navire entier) — SANS le
    # seuil générique CHEF_SECTION+ historique, qui autorisait à tort
    # tout chef de section (et au-dessus) à valider n'importe quelle
    # formation de son périmètre sans en être désigné référent (faille
    # corrigée, tâche Notion « Sécurité : la validation de formation
    # contourne le contrôle par référent »). Un référent de rang
    # inférieur (ex. EQUIPIER) voit quand même le bouton, cf.
    # _est_referent_formation.
    peut_valider = (
        user_role_level(request.user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION
        or _est_referent_formation(request.user)
    )
    ctx["peut_valider"] = peut_valider
    if peut_valider:
        # Catalogue global : toutes les formations sont proposables dans
        # la modale de validation (l'autorité réelle est revalidée côté
        # serveur par ValiderFormationView, au regard du navire du marin
        # ciblé — cf. peut_valider_formation). Les marins proposés
        # respectent le périmètre organisationnel de l'appelant, élargi
        # pour un référent (cf. _marins_validables).
        ctx["marins"] = _marins_validables(request.user)
        ctx["formations_validables"] = toutes_formations

    # Circuit A — Demande et attribution de places (T-FORM demande de
    # places) : un chef de secteur (CHEF_SECTION+) peut formuler une
    # demande pour son propre bord (navire_courant, résolu ci-dessus).
    ctx["peut_demander_places"] = _peut_demander_places(request.user) and navire_courant is not None
    if ctx["peut_demander_places"]:
        ctx["mes_demandes_places"] = list(
            DemandePlace.objects.filter(created_by=request.user)
            .select_related("course", "session")
            .order_by("-created_at")
        )
        # Marins proposables pour l'affectation des places attribuées :
        # même périmètre organisationnel que celui revalidé côté serveur
        # dans demande_place_actions.py::_action_affecter_place_demandee.
        ctx["marins_demande"] = _marins_perimetre_demandeur(request.user)

    # Demandes à traiter par l'organisme de formation (référent de la
    # formation POUR SON PROPRE NAVIRE, ou supervision globale) : même
    # autorisation que l'attribution/le refus (peut_valider_formation).
    demandes_en_attente = list(
        DemandePlace.objects.filter(statut="REQUESTED").select_related("course", "ship")
    )
    demandes_a_traiter = [
        d for d in demandes_en_attente
        if peut_valider_formation(request.user, d.course, navire_courant)
    ]
    for d in demandes_a_traiter:
        d.sessions_disponibles = list(
            TrainingSession.objects.filter(course=d.course, status="PLANNED").order_by("scheduled_at")
        )
    ctx["demandes_a_traiter"] = demandes_a_traiter

    # Circuit B — Candidature individuelle : trois files de traitement
    # distinctes, une par niveau de validation (hiérarchie, BRH,
    # organisme), chacune filtrée selon l'autorité réelle de l'appelant
    # (même principe que demandes_a_traiter ci-dessus pour le Circuit A).
    if user_role_level(request.user) >= NIVEAU_REQUIS_VALIDATION_HIERARCHIE_CANDIDATURE:
        marins_perimetre_ids = _marins_perimetre_hierarchie(request.user).values_list("pk", flat=True)
        ctx["candidatures_hierarchie_a_traiter"] = list(
            CandidatureFormation.objects.filter(
                statut="PENDING_APPROVAL",
                hierarchie_validee_par__isnull=True,
                marin_id__in=marins_perimetre_ids,
            ).select_related("course", "marin", "marin__profile")
        )
    else:
        ctx["candidatures_hierarchie_a_traiter"] = []

    candidatures_brh_en_attente = list(
        CandidatureFormation.objects.filter(
            statut="PENDING_APPROVAL", brh_validee_par__isnull=True,
        ).select_related("course", "marin", "marin__profile")
    )
    ctx["candidatures_brh_a_traiter"] = [
        c for c in candidatures_brh_en_attente
        if _peut_valider_candidature_brh(request.user, navire_de(c.marin))
    ]

    # Autorisation calquée sur le Circuit A (demandes_a_traiter
    # ci-dessus) : navire de référence = celui de L'ORGANISME (l'appelant
    # lui-même, navire_courant, résolu plus haut), PAS celui de chaque
    # marin candidat — un référent d'école traite les candidatures reçues
    # par son propre établissement, quel que soit le bord d'origine du
    # candidat.
    candidatures_transmises = list(
        CandidatureFormation.objects.filter(statut="TRANSMITTED")
        .select_related("course", "marin", "marin__profile")
    )
    ctx["candidatures_organisme_a_traiter"] = [
        c for c in candidatures_transmises
        if peut_valider_formation(request.user, c.course, navire_courant)
    ]

    # Circuit C — Circuit d'approbation chef de secteur -> chef de service
    # (formations « gérées par le bord ») : un chef de secteur propose,
    # invisible du catalogue général (get_queryset) tant qu'un chef de
    # service de son périmètre (ou supervision globale) ne l'a pas
    # validée — même pattern d'état explicite que WAITING_VALIDATION sur
    # les occurrences de maintenance (maintenance/models.py).
    ctx["peut_proposer_formation_bord"] = _peut_proposer_formation_bord(request.user)
    if ctx["peut_proposer_formation_bord"]:
        # Mes propres propositions (création ou modification), qu'elles
        # soient encore en attente ou déjà refusées : permet au chef de
        # secteur de suivre l'état de ce qu'il a soumis, et de reprendre
        # une proposition refusée pour la corriger et la soumettre à
        # nouveau (cf. formation_bord_actions.py::_action_proposer_formation_bord).
        ctx["mes_propositions_bord"] = list(
            TrainingCourse.objects.filter(
                gere_par_le_bord=True,
                updated_by=request.user,
                statut_validation__in=["WAITING_VALIDATION", "REFUSED"],
            ).order_by("-updated_at")
        )
    # Propositions à valider par l'appelant (CHEF_SERVICE+ du périmètre du
    # proposeur, ou supervision globale) : même principe que
    # candidatures_brh_a_traiter ci-dessus, filtrage Python sur l'autorité
    # réelle après un premier filtre côté requête sur le statut.
    propositions_en_attente = list(
        TrainingCourse.objects.filter(
            gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
        ).select_related("updated_by")
    )
    ctx["formations_bord_a_valider"] = [
        c for c in propositions_en_attente
        if peut_valider_proposition_bord(request.user, c.updated_by)
    ]

    # Objet date (pas de chaîne) : comparé tel quel à r.expires_at dans le
    # template pour le badge À jour/Expirée. Le rendu template d'un objet
    # date appelle str(), qui produit déjà le format ISO AAAA-MM-JJ attendu
    # par l'attribut value de l'input type="date" du formulaire.
    ctx["aujourdhui"] = aujourdhui
    return ctx
