"""Présentation de la carte « À faire » : intitulé court, contexte, état, échéance, nature et partage entre
prioritaires et autres actions.

Logique d'affichage uniquement : elle s'appuie sur les entrées déjà triées de `a_faire` et sur les états et
permissions existants. L'ordre de la liste, les droits et les workflows ne sont jamais modifiés.
"""
from annonces.models import Annonce
from assets.models import Installation
from demandes.models import Demande
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from rondes.models import Ronde
from taches.models import Tache
from training.models import TrainingRecord

# Nombre de lignes prioritaires à partir duquel la section « Autres actions » démarre repliée : au-delà, le bouton
# de la section n'a plus de marge dans un écran 1366×768. Même règle pour tous les profils.
SEUIL_AUTRES_REPLIEES = 6

URGENT, ACTION, SUIVI = "urgent", "action", "suivi"
LIBELLES_NATURE = {URGENT: "Urgent", ACTION: "Action requise", SUIVI: "À suivre"}


def _urgence_declaree(entree, user):
    """Tâche de l'utilisateur marquée « urgente » par son émetteur, en retard ou non."""
    objet = entree["objet"]
    return isinstance(objet, Tache) and objet.assigne_id == user.pk and objet.priorite == Tache.PRIORITE_URGENTE


def est_prioritaire(entree, user):
    return bool(entree["niveau"]) or _urgence_declaree(entree, user)


def _nature(entree, user):
    """Urgence avérée, action de l'utilisateur, suivi d'un tiers, ou rien quand le sens n'est pas établi par les données.

    Un état dont personne n'est désigné pour agir (maintenance « en validation », ticket bloqué) reste descriptif.
    """
    if entree["niveau"] == "danger":
        return URGENT
    if _urgence_declaree(entree, user):
        return ACTION
    if not entree["niveau"]:
        return ""
    objet = entree["objet"]
    if isinstance(objet, Demande):
        return SUIVI if objet.responsable_id == user.pk and objet.etat == Demande.ETAT_EN_ATTENTE else ACTION
    if isinstance(objet, Annonce):
        return ACTION if objet.accuse_requis else ""
    if isinstance(objet, (Tache, TrainingRecord)):
        return ACTION
    if isinstance(objet, (MaintenanceOccurrence, CorrectiveTicket, Ronde)):
        return ""
    # Propositions et fiches « à viser » (déjà filtrées par `peut_agir`) et mentions sans réponse.
    return ACTION


def _repere(entree, user):
    """Criticité élevée ou urgence déclarée : un repère neutre, jamais une urgence avérée."""
    objet = entree["objet"]
    if _urgence_declaree(entree, user):
        return "Urgence déclarée"
    if entree["niveau"] or entree["criticite"] < 4:
        return ""
    if isinstance(objet, Demande):
        return f"Priorité {objet.get_priorite_display().lower()}"
    if isinstance(objet, CorrectiveTicket):
        return f"Gravité {objet.severity}"
    if isinstance(objet, MaintenanceOccurrence):
        return f"Priorité {objet.priority}"
    return "Priorité haute"


def _equipement(equipement):
    """Intitulé et chemin d'un matériel ou d'une installation, à partir de leurs champs (sans découper de texte)."""
    chemin = " / ".join(n.name for n in (equipement.ship, equipement.service, equipement.sector) if n)
    # Un matériel garde son libellé complet (type et identifiant) : sans lui, deux extincteurs seraient indiscernables.
    return (equipement.designation if isinstance(equipement, Installation) else str(equipement)), chemin


def _champs(entree, user):
    objet, niveau = entree["objet"], entree["niveau"]
    base = {"principal": entree["titre"], "contexte": "", "etat": entree["detail"], "echeance": "", "non_assigne": False}
    if isinstance(objet, MaintenanceOccurrence):
        if objet.installation_maintenance_id:
            nom, chemin = _equipement(objet.installation_maintenance.installation)
            nom = f"{nom} - {objet.installation_maintenance.title}"
        else:
            nom, chemin = _equipement(objet.asset)
        if objet.status == "WAITING_VALIDATION":
            etat = "En attente de validation"
        elif niveau == "danger":
            etat = "En retard" + (" · en cours" if objet.status == "IN_PROGRESS" else "")
        else:
            etat = objet.get_status_display()
        base.update(principal=nom, contexte=chemin, etat=etat, echeance=f"{objet.scheduled_for:%d/%m}",
                    non_assigne=not objet.assignees.all())
    elif isinstance(objet, CorrectiveTicket):
        nom, chemin = _equipement(objet.equipement)
        base.update(principal=nom, contexte=chemin, etat=f"Ticket correctif · {objet.get_status_display()}",
                    echeance=f"{objet.planned_for:%d/%m}" if objet.planned_for else "", non_assigne=not objet.assignees.all())
    elif isinstance(objet, Ronde):
        base.update(etat="Ronde en retard" if niveau == "danger" else "Ronde du jour", echeance=f"{objet.date_prevue:%d/%m}")
    elif isinstance(objet, Tache) and objet.assigne_id == user.pk:
        faits, total = objet.avancement_checklist
        etat = "Tâche en retard" if niveau == "danger" else f"Tâche · {objet.get_statut_display()}"
        base.update(etat=etat + (f" · checklist {faits}/{total}" if total else ""),
                    echeance=f"{objet.echeance:%d/%m}" if objet.echeance else "")
    return base


def presenter(entrees, user):
    """Entrées de `a_faire` enrichies des champs d'affichage, ordre conservé, avec leur zone d'affichage."""
    lignes = []
    for entree in entrees:
        nature = _nature(entree, user)
        objet = entree["objet"]
        ligne = {**entree, **_champs(entree, user), "nature": nature, "libelle_nature": LIBELLES_NATURE.get(nature, ""),
                 "repere": _repere(entree, user), "zone": "prioritaire" if est_prioritaire(entree, user) else "autre",
                 "identifiant": f"{objet._meta.label_lower}:{objet.pk}"}
        if nature == SUIVI:
            ligne["classes"] = "mx-afaire__ligne--suivi"
        lignes.append(ligne)
    return lignes


def compteurs(lignes):
    """Total, prioritaires, autres, et état initial de la section secondaire."""
    prioritaires = sum(1 for ligne in lignes if ligne["zone"] == "prioritaire")
    return {
        "nb_actions": len(lignes), "nb_prioritaires": prioritaires, "nb_autres": len(lignes) - prioritaires,
        "autres_repliees": prioritaires >= SEUIL_AUTRES_REPLIEES,
    }
