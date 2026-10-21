"""Workflow des tâches : droits, transitions, notifications et traçabilité.

Un chef (CHEF_SECTION+) attribue une tâche à un marin de son périmètre et de son équipage.
Le fil de discussion est ouvert à l'assigné, au créateur, aux chefs du périmètre et aux
interlocuteurs que le chef ajoute (marins du même navire, y compris l'équipage à terre).
"""
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from absences.models import Absence
from absences.services import marin_dans_perimetre
from accounts.models import AuditLog
from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import seuil_role
from matrix.core.roles import niveau_ecriture, user_role_level
from matrix.core.scopes import equipage_marin_q
from matrix.core.validators import valider_document
from notifications.models import Notification, NotificationLevel
from notifications.services import traiter_actions
from threads.models import Message, Thread
from threads.utils import ajouter_commentaire

from .models import ElementChecklistTache, LotTaches, ParametresTaches, PieceJointeTache, Tache

User = get_user_model()


def peut_superviser(user):
    """Lecture d'équipe : niveau minimal configurable (Réglages > Seuils de rôle, action « tache_attribution »)."""
    return user_role_level(user) >= seuil_role("tache_attribution")


def peut_attribuer(user):
    """Écriture (attribuer, réaffecter, lever un blocage) : même seuil, sur le niveau d'écriture."""
    return niveau_ecriture(user) >= seuil_role("tache_attribution")


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def est_chef_de(user, marin):
    return peut_attribuer(user) and marin_dans_perimetre(user, marin)


def superviseur_de(user, marin):
    return peut_superviser(user) and marin_dans_perimetre(user, marin)


def peut_gerer(user, tache):
    return tache.partagee and user.pk != tache.assigne_id and est_chef_de(user, tache.assigne)


def _est_acteur(user, tache):
    return user.pk in (tache.assigne_id, tache.created_by_id) or tache.participants.filter(pk=user.pk).exists()


def peut_consulter(user, tache):
    if _est_acteur(user, tache):
        return True
    return tache.partagee and user.pk != tache.assigne_id and superviseur_de(user, tache.assigne)


def taches_visibles(user):
    base = Q(assigne=user) | Q(created_by=user) | Q(participants=user)
    if peut_superviser(user):
        base |= build_scope_q(user, "assigne__profile__") & equipage_marin_q(user, "assigne__profile__") & Q(partagee=True)
    return Tache.objects.filter(base).distinct()


def taches_a_suivre(user):
    """Tâches ouvertes dont `user` doit s'occuper : les siennes, et celles qu'il supervise lorsqu'elles sont bloquées."""
    ouvertes = (taches_visibles(user).filter(statut__in=Tache.STATUTS_OUVERTS)
                .select_related("assigne").prefetch_related("elements_checklist"))
    return [
        t for t in ouvertes
        if t.assigne_id == user.pk or (t.statut == Tache.STATUT_BLOQUEE and peut_gerer(user, t))
    ]


def taches_supervisees(user):
    """Tâches des marins du périmètre et de l'équipage d'un chef, hors les siennes."""
    if not peut_superviser(user):
        return Tache.objects.none()
    return Tache.objects.filter(
        build_scope_q(user, "assigne__profile__"), equipage_marin_q(user, "assigne__profile__"), partagee=True,
    ).exclude(assigne=user)


def avancement_equipe(user, aujourdhui=None):
    """Synthèse pour le chef : tâches par statut, charge par marin, retards, blocages et conflits d'absence.

    Les tâches terminées ne comptent que sur la durée réglée (jours_terminees_affichees).
    Un conflit est une tâche ouverte dont l'échéance tombe pendant une absence déclarée ou validée de son marin.
    """
    aujourdhui = aujourdhui or timezone.localdate()
    depuis = timezone.now() - timedelta(days=ParametresTaches.courants().jours_terminees_affichees)
    taches = taches_supervisees(user).select_related("assigne")
    ouvertes = list(taches.filter(statut__in=Tache.STATUTS_OUVERTS).prefetch_related("elements_checklist"))
    comptes = {statut: 0 for statut, _ in Tache.STATUT_CHOICES}
    for t in ouvertes:
        comptes[t.statut] += 1
    comptes[Tache.STATUT_TERMINEE] = taches.filter(statut=Tache.STATUT_TERMINEE, terminee_le__gte=depuis).count()

    marins = list(marins_supervises(user))
    absences = list(Absence.objects.filter(
        marin__in=marins, date_fin__gte=aujourdhui).select_related("type_absence").order_by("date_debut"))
    charges = []
    for marin in marins:
        siennes = [t for t in ouvertes if t.assigne_id == marin.pk]
        absent = next((a for a in absences if a.marin_id == marin.pk and a.date_debut <= aujourdhui), None)
        charges.append({
            "marin": marin, "ouvertes": len(siennes), "retards": sum(t.en_retard_au(aujourdhui) for t in siennes),
            "bloquees": sum(t.statut == Tache.STATUT_BLOQUEE for t in siennes), "absent_jusqu_au": absent and absent.date_fin,
        })
    charges.sort(key=lambda c: (-c["ouvertes"], c["marin"].username))
    conflits = [
        {"tache": t, "absence": a}
        for t in ouvertes for a in absences
        if t.echeance and a.marin_id == t.assigne_id and a.date_debut <= t.echeance <= a.date_fin
    ]
    return {
        "comptes": comptes,
        "total": sum(comptes.values()),
        "retards": [t for t in ouvertes if t.en_retard_au(aujourdhui)],
        "blocages": [t for t in ouvertes if t.statut == Tache.STATUT_BLOQUEE],
        "charges": charges,
        "charge_max": max((c["ouvertes"] for c in charges), default=0),
        "conflits": conflits,
        "lots": _avancement_lots(user),
    }


def _avancement_lots(user):
    """Attributions à une unité encore en cours : tâches terminées sur total, pour les marins supervisés."""
    lots = {}
    lignes = taches_supervisees(user).filter(lot__isnull=False).values_list("lot_id", "lot__titre", "lot__libelle", "statut")
    for lot_id, titre, libelle, statut in lignes:
        lot = lots.setdefault(lot_id, {"pk": lot_id, "titre": titre, "libelle": libelle, "total": 0, "terminees": 0})
        lot["total"] += 1
        lot["terminees"] += statut == Tache.STATUT_TERMINEE
    return sorted((lot for lot in lots.values() if lot["terminees"] < lot["total"]), key=lambda lot: -lot["pk"])


def marins_supervises(user):
    """Marins de l'équipe dont `user` suit les tâches et les plannings (lui-même exclu)."""
    if not peut_superviser(user):
        return User.objects.none()
    return User.objects.filter(build_scope_q(user, "profile__"), equipage_marin_q(user)).exclude(pk=user.pk).order_by("username")


def marins_assignables(user):
    """Marins à qui `user` peut attribuer une tâche (lui-même exclu)."""
    return marins_supervises(user) if peut_attribuer(user) else User.objects.none()


def interlocuteurs_possibles(tache):
    """Marins du même navire que l'assigné (équipage à terre compris), hors assigné et participants."""
    navire = getattr(tache.assigne.profile, "ship_id", None)
    if navire is None:
        return User.objects.none()
    return User.objects.filter(profile__ship_id=navire, is_active=True).exclude(
        pk__in=[tache.assigne_id, *tache.participants.values_list("pk", flat=True)]
    ).order_by("username")


def _tracer(tache, acteur, action, extra=""):
    AuditLog.objects.create(
        actor=acteur, action=f"tache_{action}", target_user=tache.assigne,
        details=f"tache={tache.pk}; statut={tache.statut}; echeance={tache.echeance.isoformat() if tache.echeance else 'aucune'}{extra}",
    )


def _message_systeme(tache, corps):
    thread, _ = Thread.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(tache), object_id=str(tache.pk),
    )
    Message.objects.create(thread=thread, author=None, body=corps, is_system=True)


def _destinataires(tache, sauf):
    """Acteurs du dossier à prévenir : assigné, créateur, interlocuteurs du fil."""
    ids = {tache.assigne_id, tache.created_by_id, *tache.participants.values_list("pk", flat=True)}
    ids.discard(sauf.pk)
    ids.discard(None)
    return User.objects.filter(pk__in=ids, is_active=True)


def _notifier(tache, destinataires, verb, niveau=NotificationLevel.INFO, action=False):
    for user in destinataires:
        Notification.objects.create(user=user, verb=verb, level=niveau, target=tache, action_requise=action)


def taches_liees_a(user, annonce):
    """Tâches issues d'une annonce que `user` assigne ou a créées (jamais celles des autres)."""
    return taches_visibles(user).filter(annonce=annonce).filter(
        Q(assigne=user) | Q(created_by=user)).select_related("assigne")


def creer_tache(chef, assigne, titre, echeance=None, description="", priorite=Tache.PRIORITE_NORMALE, partagee=True, annonce=None,
                lot=None, elements=()):
    """Un chef attribue une tâche ; un marin peut aussi se créer la sienne (privée sauf partage de sa part).

    `elements` : textes de la checklist initiale."""
    personnelle = chef.pk == assigne.pk
    if not personnelle and not est_chef_de(chef, assigne):
        raise PermissionError("Vous ne pouvez pas attribuer de tâche à ce marin.")
    tache = Tache(
        titre=titre.strip(), description=description.strip(), echeance=echeance, priorite=priorite,
        partagee=partagee if personnelle else True, assigne=assigne, created_by=chef, updated_by=chef,
        annonce=annonce, lot=lot,
    )
    tache.full_clean(exclude=["assigne"])
    tache.save()
    _tracer(tache, chef, "creation", f"; annonce={annonce.pk}" if annonce else "")
    textes = _textes_checklist(elements)
    ElementChecklistTache.objects.bulk_create(
        ElementChecklistTache(tache=tache, texte=texte, ordre=i) for i, texte in enumerate(textes, 1))
    if not personnelle:
        delai = f" (échéance {echeance:%d/%m/%Y})" if echeance else ""
        _notifier(tache, [assigne], f"{_nom(chef)} vous a attribué la tâche « {tache.titre} »{delai}.", action=True)
    return tache


def _textes_checklist(elements):
    """Textes non vides, tronqués à la longueur du champ."""
    return [t for t in (e.strip()[:ElementChecklistTache._meta.get_field("texte").max_length] for e in elements) if t]


_UNITES = {"section": "section", "secteur": "sector", "service": "service"}


def unites_assignables(user):
    """Unités (section, secteur, service) comptant des marins du périmètre de `user` : [(clé, libellé, nb de marins)]."""
    comptes = {}
    for marin in marins_assignables(user).select_related("profile__section", "profile__sector", "profile__service"):
        for type_, champ in _UNITES.items():
            unite = getattr(marin.profile, champ, None)
            if unite is not None:
                cle = f"{type_}:{unite.pk}"
                libelle, nombre = comptes.get(cle, (f"{unite.name} ({type_})", 0))
                comptes[cle] = (libelle, nombre + 1)
    return [(cle, libelle, nombre) for cle, (libelle, nombre) in sorted(comptes.items(), key=lambda c: c[1][0])]


def attribuer_a_unite(chef, cle_unite, titre, echeance=None, description="", priorite=Tache.PRIORITE_NORMALE, elements=()):
    """Une tâche individuelle par marin de l'unité, dans le périmètre et l'équipage du chef, liées par un lot."""
    type_, _, pk = cle_unite.partition(":")
    if type_ not in _UNITES or not (pk.isascii() and pk.isdigit()):
        raise ValidationError("Unité inconnue.")
    libelle = next((lib for cle, lib, _ in unites_assignables(chef) if cle == cle_unite), None)
    if libelle is None:
        raise PermissionError("Cette unité n'est pas dans votre périmètre.")
    marins = marins_assignables(chef).filter(**{f"profile__{_UNITES[type_]}": int(pk)})
    with transaction.atomic():
        lot = LotTaches.objects.create(libelle=libelle, titre=titre.strip()[:200], created_by=chef, updated_by=chef)
        taches = [
            creer_tache(chef, marin, titre, echeance, description, priorite, lot=lot, elements=elements) for marin in marins
        ]
        AuditLog.objects.create(
            actor=chef, action="tache_attribution_unite", details=f"lot={lot.pk}; unite={cle_unite}; taches={len(taches)}")
    return lot, taches


def peut_editer_checklist(user, tache):
    return tache.ouverte and user.pk in (tache.assigne_id, tache.created_by_id)


def _controler_checklist(tache, user):
    if not peut_editer_checklist(user, tache):
        raise PermissionError("Seuls le marin assigné et le créateur modifient la checklist d'une tâche ouverte.")


def ajouter_element(tache, user, texte):
    _controler_checklist(tache, user)
    texte = texte.strip()
    if not texte:
        raise ValidationError("Saisissez le texte de l'élément.")
    ordre = tache.elements_checklist.aggregate(m=Max("ordre"))["m"] or 0
    element = ElementChecklistTache(tache=tache, texte=texte, ordre=ordre + 1)
    element.full_clean(exclude=["tache"])
    element.save()
    _tracer(tache, user, "checklist_ajout", f"; element={element.pk}")


def basculer_element(tache, user, element_pk):
    _controler_checklist(tache, user)
    element = get_object_or_404(tache.elements_checklist, pk=element_pk)
    element.fait = not element.fait
    element.save(update_fields=["fait", "updated_at"])
    _tracer(tache, user, "checklist_fait" if element.fait else "checklist_defait", f"; element={element.pk}")


def supprimer_element(tache, user, element_pk):
    _controler_checklist(tache, user)
    element = get_object_or_404(tache.elements_checklist, pk=element_pk)
    _tracer(tache, user, "checklist_suppression", f"; element={element.pk}")
    element.delete()


def peut_joindre(user, tache):
    return tache.ouverte and (_est_acteur(user, tache) or peut_gerer(user, tache))


def peut_supprimer_piece(user, piece):
    return user.pk in (piece.created_by_id, piece.tache.created_by_id)


def joindre_fichier(tache, user, fichier):
    """Ajoute une pièce jointe après contrôle d'extension, de taille et de contenu (validateur commun des documents)."""
    if not peut_joindre(user, tache):
        raise PermissionError("Vous ne pouvez pas joindre de fichier à cette tâche.")
    if not fichier:
        raise ValidationError("Choisissez un fichier.")
    valider_document(fichier)
    piece = PieceJointeTache.objects.create(
        tache=tache, fichier=fichier, nom=fichier.name.replace("\\", "/").rsplit("/", 1)[-1][:255], created_by=user, updated_by=user)
    _tracer(tache, user, "piece_jointe_ajout", f"; piece={piece.pk}")
    return piece


def supprimer_piece(tache, user, piece_pk):
    piece = get_object_or_404(tache.pieces_jointes.select_related("tache"), pk=piece_pk)
    if not peut_supprimer_piece(user, piece):
        raise PermissionError("Seul l'auteur du fichier ou le créateur de la tâche peut le supprimer.")
    _tracer(tache, user, "piece_jointe_suppression", f"; piece={piece.pk}")
    piece.fichier.delete(save=False)
    piece.delete()


def _enregistrer(tache, acteur, action, champs, extra=""):
    tache.updated_by = acteur
    tache.save(update_fields=[*champs, "updated_by", "updated_at"])
    _tracer(tache, acteur, action, extra)


def _date(valeur):
    return f"{valeur:%d/%m/%Y}" if valeur else "aucune"


def peut_modifier(user, tache):
    """Un chef du périmètre modifie une tâche attribuée et ouverte ; jamais la tâche personnelle d'un marin."""
    return tache.ouverte and not tache.personnelle and peut_gerer(user, tache)


def partager(tache, user, partagee):
    """Le marin partage sa tâche personnelle avec ses chefs, ou la reprend en privé (les interlocuteurs sont retirés)."""
    if not tache.personnelle or user.pk != tache.assigne_id:
        raise PermissionError("Seul le marin peut modifier le partage de sa tâche personnelle.")
    if tache.partagee == partagee:
        raise ValidationError("Le partage est déjà dans cet état.")
    tache.partagee = partagee
    if not partagee:
        tache.participants.clear()
    _enregistrer(tache, user, "partage" if partagee else "retrait_partage", ["partagee"])


def modifier_tache(chef, tache, assigne, echeance, priorite):
    """Réaffecte, replanifie ou change la priorité ; chaque changement est tracé dans le fil et l'audit.

    La tâche réaffectée repart « À faire » chez son nouveau titulaire, sans motif de blocage.
    """
    if not peut_modifier(chef, tache):
        raise PermissionError("Vous ne pouvez pas modifier cette tâche.")
    changements, champs, ancien = [], ["echeance", "priorite"], tache.assigne
    if assigne.pk != tache.assigne_id:
        if assigne.pk == chef.pk or not est_chef_de(chef, assigne):
            raise PermissionError("Vous ne pouvez pas confier la tâche à ce marin.")
        tache.assigne = assigne
        tache.statut, tache.motif_blocage = Tache.STATUT_A_FAIRE, ""
        champs += ["assigne", "statut", "motif_blocage"]
        changements.append(f"réaffectée de {_nom(ancien)} à {_nom(assigne)}")
    if echeance != tache.echeance:
        changements.append(f"échéance du {_date(tache.echeance)} au {_date(echeance)}")
    if priorite != tache.priorite:
        changements.append(f"priorité {tache.get_priorite_display().lower()} → {dict(Tache.PRIORITE_CHOICES).get(priorite, priorite).lower()}")
    if not changements:
        raise ValidationError("Aucune modification à enregistrer.")
    tache.echeance, tache.priorite = echeance, priorite
    tache.full_clean(exclude=["assigne"])
    resume = "; ".join(changements)
    _enregistrer(tache, chef, "modification", champs, extra=f"; modifications={resume}")
    _message_systeme(tache, f"{_nom(chef)} a modifié la tâche : {resume}.")
    if tache.assigne_id != ancien.pk:
        traiter_actions(tache, [ancien])
        _notifier(tache, [tache.assigne], f"{_nom(chef)} vous a confié la tâche « {tache.titre} » ({resume}).", action=True)
        _notifier(tache, [ancien], f"La tâche « {tache.titre} » ne vous est plus attribuée : {resume}.")
    else:
        _notifier(tache, [tache.assigne], f"{_nom(chef)} a modifié « {tache.titre} » : {resume}.")


def demarrer(tache, user):
    if user.pk != tache.assigne_id:
        raise PermissionError("Seul le marin assigné peut démarrer la tâche.")
    if tache.statut != Tache.STATUT_A_FAIRE:
        raise ValidationError("La tâche est déjà démarrée.")
    tache.statut = Tache.STATUT_EN_COURS
    _enregistrer(tache, user, "demarrage", ["statut"])


def signaler_blocage(tache, user, motif):
    if user.pk != tache.assigne_id:
        raise PermissionError("Seul le marin assigné peut signaler un blocage.")
    motif = motif.strip()
    if not motif or not tache.ouverte:
        raise ValidationError("Indiquez le motif du blocage d'une tâche ouverte.")
    tache.statut = Tache.STATUT_BLOQUEE
    tache.motif_blocage = motif
    _enregistrer(tache, user, "blocage", ["statut", "motif_blocage"])
    _message_systeme(tache, f"{_nom(user)} signale un blocage : {motif}")
    # Dès le blocage : les acteurs du dossier, puis les chefs du périmètre qui peuvent le lever (alerte d'action).
    acteurs = list(_destinataires(tache, user))
    verbe = f"{PREFIXE_BLOCAGE} {_nom(user)} est bloqué sur « {tache.titre} » : {motif}"
    _notifier(tache, acteurs, verbe, NotificationLevel.WARNING, action=True)
    deja = {a.pk for a in acteurs}
    _notifier(
        tache, [c for c in _destinataires_relance(tache, ParametresTaches.courants()) if c.pk not in deja and c.pk != user.pk],
        verbe, NotificationLevel.WARNING, action=True,
    )


def repondre(tache, user, corps):
    if not peut_consulter(user, tache):
        raise PermissionError("Vous n'avez pas accès au fil de cette tâche.")
    corps = corps.strip()
    if not corps:
        raise ValidationError("Le message ne peut pas être vide.")
    ajouter_commentaire(tache, user, corps)
    _notifier(tache, _destinataires(tache, user), f"{_nom(user)} a répondu sur « {tache.titre} ».")


def ajouter_participant(tache, chef, user):
    if not peut_gerer(chef, tache):
        raise PermissionError("Seul un chef du périmètre peut ajouter un interlocuteur.")
    if not interlocuteurs_possibles(tache).filter(pk=user.pk).exists():
        raise ValidationError("Cet interlocuteur n'appartient pas au navire de la tâche.")
    tache.participants.add(user)
    _tracer(tache, chef, "interlocuteur")
    _message_systeme(tache, f"{_nom(chef)} a ajouté {_nom(user)} au fil.")
    _notifier(tache, [user], f"{_nom(chef)} vous a ajouté au fil de la tâche « {tache.titre} ».")


def reprendre(tache, chef):
    """Le chef lève le blocage une fois la solution donnée dans le fil."""
    if not peut_gerer(chef, tache):
        raise PermissionError("Seul un chef du périmètre peut lever un blocage.")
    if tache.statut != Tache.STATUT_BLOQUEE:
        raise ValidationError("La tâche n'est pas bloquée.")
    tache.statut = Tache.STATUT_EN_COURS
    _enregistrer(tache, chef, "reprise", ["statut"])
    traiter_actions(tache, prefixe_verbe=PREFIXE_BLOCAGE)
    _message_systeme(tache, f"{_nom(chef)} lève le blocage : la tâche reprend.")
    _notifier(tache, [tache.assigne], f"Blocage levé sur « {tache.titre} » : vous pouvez reprendre.")


def rendre_compte(tache, user, compte_rendu):
    if user.pk != tache.assigne_id:
        raise PermissionError("Seul le marin assigné peut rendre compte.")
    compte_rendu = compte_rendu.strip()
    if not compte_rendu or not tache.ouverte:
        raise ValidationError("Rédigez le compte rendu d'une tâche ouverte.")
    tache.statut = Tache.STATUT_TERMINEE
    tache.compte_rendu = compte_rendu
    tache.terminee_le = timezone.now()
    _enregistrer(tache, user, "compte_rendu", ["statut", "compte_rendu", "terminee_le"])
    _message_systeme(tache, f"{_nom(user)} a rendu compte : {compte_rendu}")
    traiter_actions(tache)
    if tache.demande_id:
        from demandes.services import action_terminee  # import différé : demandes dépend de taches

        action_terminee(tache)
    _notifier(tache, _destinataires(tache, user), f"{_nom(user)} a terminé « {tache.titre} » et rendu compte.")


PREFIXE_RELANCE = "Tâche en retard"
PREFIXE_BLOCAGE = "Blocage :"


def _relances(tache):
    return Notification.objects.filter(
        content_type=ContentType.objects.get_for_model(tache), object_id=str(tache.pk), verb__startswith=PREFIXE_RELANCE,
    )


def _destinataires_relance(tache, parametres):
    """Tâche bloquée : les chefs qui peuvent lever le blocage ; sinon l'assigné et le chef qui l'a attribuée."""
    if tache.statut == Tache.STATUT_BLOQUEE:
        if not parametres.relancer_chefs_si_blocage or not tache.partagee:
            return []
        candidats = User.objects.filter(is_active=True, profile__ship_id=getattr(tache.assigne.profile, "ship_id", None))
        return [u for u in candidats if u.pk != tache.assigne_id and est_chef_de(u, tache.assigne)]
    ids = set()
    if parametres.relancer_assigne:
        ids.add(tache.assigne_id)
    if parametres.relancer_chef_attributeur and tache.created_by_id:
        ids.add(tache.created_by_id)
    return list(User.objects.filter(pk__in=ids, is_active=True))


def relancer_echeances_depassees(aujourdhui=None):
    """Relance les acteurs d'une tâche en retard, tous les `jours_entre_relances` jours tant qu'elle n'est pas traitée.

    Le dédoublonnage ignore l'état de lecture : une relance lue n'est pas une tâche faite.
    Les relances encore non lues d'une tâche terminée sont soldées.
    """
    parametres = ParametresTaches.courants()
    aujourdhui = aujourdhui or timezone.localdate()
    creees = 0
    if parametres.jours_entre_relances:
        depuis = aujourdhui - timedelta(days=parametres.jours_entre_relances - 1)
        debut = timezone.make_aware(datetime.combine(depuis, time.min))
        for tache in Tache.objects.filter(
            statut__in=Tache.STATUTS_OUVERTS, echeance__lt=aujourdhui, assigne__is_active=True,
        ).select_related("assigne"):
            jours = (aujourdhui - tache.echeance).days
            etat = " (bloquée)" if tache.statut == Tache.STATUT_BLOQUEE else ""
            for user in _destinataires_relance(tache, parametres):
                if _relances(tache).filter(user=user, created_at__gte=debut).exists():
                    continue
                qui = f" de {_nom(tache.assigne)}" if user.pk != tache.assigne_id else ""
                _notifier(
                    tache, [user],
                    f"{PREFIXE_RELANCE}{etat} : « {tache.titre} »{qui}, échéance dépassée de {jours} j.",
                    NotificationLevel.WARNING, action=True,
                )
                creees += 1
    for terminee in Tache.objects.filter(statut=Tache.STATUT_TERMINEE, terminee_le__gte=timezone.now() - timedelta(days=2)):
        traiter_actions(terminee, prefixe_verbe=PREFIXE_RELANCE)
    return creees
