"""Confirmation explicite des validations critiques (web et API).

Les textes acceptés par le valideur sont définis ici, à un seul endroit, avec un
numéro de version à incrémenter à chaque modification. Ce n'est pas une signature
électronique : la personne est déjà authentifiée, la confirmation et sa trace
(utilisateur, texte, version, canal) attestent seulement qu'elle a validé en connaissance de cause.
"""
from accounts.models import AuditLog

CANAL_WEB = "web"
CANAL_API = "api"

TEXTES = {
    "maintenance_critique": (1, "Je confirme avoir vérifié les informations et valide la clôture de cette maintenance."),
    "remise_en_service": (1, "Je confirme avoir vérifié les informations et valide la remise en service."),
    "pret_appareillage": (
        1, "Je confirme avoir vérifié les informations de cette session de préparation à l'appareillage et la clôture.",
    ),
}

MESSAGE_REFUS = "Confirmation requise : cochez la case de confirmation pour valider."
MESSAGE_REFUS_API = (
    "Confirmation requise : envoyez le champ « confirmation » à true pour valider. Texte à confirmer : « {texte} »"
)


def texte_confirmation(cle):
    """(version, texte) de la confirmation demandée pour la validation `cle`."""
    return TEXTES[cle]


def identite_valideur(user):
    """Grade, nom et fonction du valideur, pour le rappel affiché avant de confirmer."""
    profil = getattr(user, "profile", None)
    elements = [getattr(profil, "grade", ""), user.get_full_name() or user.get_username(), getattr(profil, "fonction_service", "")]
    return ", ".join(e for e in (str(e).strip() for e in elements) if e)


def confirmation_web(donnees):
    """Vrai si la case de confirmation est cochée (formulaire HTML)."""
    return donnees.get("confirmation") == "1"


def confirmation_api(donnees):
    """Vrai seulement pour le booléen JSON true : absent, faux ou autre type est refusé."""
    return donnees.get("confirmation") is True


def details_confirmation(cle, canal):
    """Fragment à ajouter au détail de l'AuditLog d'une validation acceptée."""
    version, texte = texte_confirmation(cle)
    return f"; canal={canal}; confirmation_version={version}; confirmation_texte={texte}"


def tracer_refus(acteur, cle, canal, objet):
    """Trace sobre d'un refus pour confirmation absente."""
    AuditLog.objects.create(
        actor=acteur, action="validation_critique_refusee",
        details=f"{objet}; canal={canal}; confirmation_manquante={cle}",
    )
