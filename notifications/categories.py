"""Icône et libellé de catégorie d'une notification : la couleur dit la priorité, l'icône dit la catégorie.

On réutilise les concepts de la table centrale des icônes (matrix/core/icones.py) ; aucune catégorie métier nouvelle.
La catégorie est déduite de l'objet visé, ou lue sur la notification quand il n'y en a pas."""
from matrix.core.icones import classe_icone

CATEGORIE_PAR_DEFAUT = "notifications"

# Modèle de l'objet visé → concept d'icône.
_PAR_MODELE = {
    "echangeservice": "echange",
    "tache": "tache", "demande": "tache",
    "annonce": "annonce", "evenementprogramme": "calendrier",
    "installationmaintenance": "maintenance", "installation": "maintenance", "maintenanceoccurrence": "maintenance",
    "maintenanceexecution": "maintenance", "checklisttemplate": "maintenance", "correctiveticket": "maintenance",
    "anomalie": "anomalie",
    "message": "discussion", "thread": "discussion",
    "document": "document", "versiondocument": "document", "retex": "document",
    "trainingsession": "formation", "trainingcourse": "formation", "candidatureformation": "formation", "demandeplace": "formation",
    "absence": "absence",
}

LIBELLES = {
    "quart": "Quarts", "calendrier": "Services et calendrier", "echange": "Échange de tour", "maintenance": "Maintenance",
    "tache": "Tâches", "discussion": "Messagerie", "document": "Documents", "anomalie": "Alerte", "terminee": "Validation",
    "formation": "Formation", "absence": "Absence", "annonce": "Annonce", CATEGORIE_PAR_DEFAUT: "Notification",
}


def categorie_de(notification):
    if notification.categorie in LIBELLES:
        return notification.categorie
    modele = notification.content_type.model if notification.content_type_id else ""
    return _PAR_MODELE.get(modele, CATEGORIE_PAR_DEFAUT)


def enrichir_categorie(notification):
    """Pose `categorie_cle`, `icone` et `categorie_libelle` sur la notification (affichage seulement)."""
    cle = categorie_de(notification)
    notification.categorie_cle = cle
    notification.icone = classe_icone(cle)
    notification.categorie_libelle = LIBELLES[cle]
    return notification
