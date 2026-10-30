"""Maquette : présentation de la carte « À faire » (intitulé court, contexte, état, échéance, nature).

N'utilise que les données et états déjà produits par `a_faire` et par les objets qu'il renvoie ; aucun calcul
métier nouveau : la « nature » est une table de correspondance par source et par état existant.
"""
from assets.models import Installation
from demandes.models import Demande
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from rondes.models import Ronde
from taches.models import Tache

# Nombre de lignes prioritaires à partir duquel la section « Autres actions » démarre repliée : environ 6 lignes
# de 70 px, soit plus de la moitié de la hauteur utile d'un écran 1366×768. Même règle pour tous.
SEUIL_AUTRES_REPLIEES = 6

URGENT, ACTION, SUIVI = "urgent", "action", "suivi"
LIBELLES_NATURE = {URGENT: "Urgent", ACTION: "Action requise", SUIVI: "À suivre"}


def _nature(entree, user):
    """Urgence avérée (niveau danger), action de l'utilisateur, ou suivi d'un élément qui dépend d'un autre acteur."""
    if entree["niveau"] == "danger":
        return URGENT
    if not entree["niveau"]:
        return ""
    objet = entree["objet"]
    if isinstance(objet, MaintenanceOccurrence):
        # L'exécutant attend la validation d'un tiers ; le chef non assigné du périmètre est celui qui doit agir.
        return SUIVI if user in objet.assignees.all() else ACTION
    if isinstance(objet, CorrectiveTicket):
        return SUIVI
    if isinstance(objet, Demande):
        return SUIVI if objet.responsable_id == user.pk and objet.etat == Demande.ETAT_EN_ATTENTE else ACTION
    return ACTION


def _repere(entree):
    """Criticité élevée sans niveau d'alerte : un repère neutre, jamais une urgence."""
    if entree["niveau"] or entree["criticite"] < 4:
        return ""
    objet = entree["objet"]
    if isinstance(objet, (Tache, Demande)):
        return f"Priorité {objet.get_priorite_display().lower()}"
    if isinstance(objet, CorrectiveTicket):
        return f"Gravité {objet.severity}"
    if isinstance(objet, MaintenanceOccurrence):
        return f"Priorité {objet.priority}"
    return "Priorité haute"


def _equipement(equipement):
    """Intitulé court et chemin d'un matériel ou d'une installation, à partir de leurs champs (sans découper de texte)."""
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
        etat = "En attente de validation" if objet.status == "WAITING_VALIDATION" else "En retard" if niveau == "danger" else "Prévue"
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
    """Ajoute à chaque entrée de `a_faire` les champs d'affichage ; l'ordre et le contenu de la liste sont conservés."""
    lignes = []
    for entree in entrees:
        nature = _nature(entree, user)
        ligne = {**entree, **_champs(entree, user), "nature": nature, "libelle_nature": LIBELLES_NATURE.get(nature, ""),
                 "repere": _repere(entree), "zone": "prioritaire" if entree["niveau"] else "autre"}
        if nature == SUIVI:
            ligne["classes"] = "mx-afaire__ligne--suivi"
        lignes.append(ligne)
    return lignes
