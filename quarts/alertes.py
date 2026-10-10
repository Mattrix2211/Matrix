"""Organisation d'alerte (sécurité et protection-défense) de la feuille de service.

Trois responsabilités :
- résoudre, pour un jour donné, qui tient chaque poste de chaque scénario
  (même résolution fonction -> titulaire que le personnel de service) ;
- signaler sur la feuille et par notification tout poste OBLIGATOIRE non armé,
  sans jamais réaffecter quelqu'un automatiquement ;
- faire passer toute modification structurelle de l'organisation par une
  validation de l'autorité configurée (le BSC propose, il ne modifie pas seul
  une organisation permanente), avec trace complète dans l'AuditLog.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.commandants_adjoints import titulaires_commandant_adjoint
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import ship_id_for_user
from notifications.models import Notification, NotificationLevel
from org.models import CommandantAdjoint

from .models import (
    FonctionFeuilleService,
    ModificationOrganisationAlerte as Modification,
    PosteAlerte,
    ScenarioAlerte,
    titulaire_du_jour,
)

User = get_user_model()

CLE_VALIDATION = "alerte_organisation_validation"
CLE_PROPOSITION = "feuille_service_configuration"


def _meme_navire(user, ship):
    return user_role_level(user) >= RoleLevel.MASTER_ADMIN or ship_id_for_user(user) == ship.pk


def peut_proposer_organisation_alerte(user, ship):
    """Proposer une modification : même habilitation que la configuration de la
    feuille de service (le BSC, selon le seuil choisi par le navire)."""
    return _meme_navire(user, ship) and user_role_level(user) >= niveau_requis_pour(user, CLE_PROPOSITION)


def peut_valider_organisation_alerte(user, ship):
    """Valider une modification : l'autorité configurée du navire (seuil de rôle)."""
    if not _meme_navire(user, ship):
        return False
    return user_role_level(user) >= niveau_requis_pour(user, CLE_VALIDATION)


def etat_alertes(ship, date_, equipage=""):
    """Scénarios actifs du navire avec, pour chaque poste, le créneau du titulaire
    du jour (ou None) : `arme` est faux quand personne ne tient la fonction."""
    resultat = []
    scenarios = ScenarioAlerte.objects.filter(ship=ship, actif=True).prefetch_related("postes__fonction")
    for scenario in scenarios:
        postes = []
        for poste in scenario.postes.all():
            creneau = (
                titulaire_du_jour(poste.fonction, date_, equipage)
                if poste.fonction_id and poste.fonction.actif else None
            )
            postes.append({"poste": poste, "creneau": creneau, "arme": bool(creneau and creneau.marin_id)})
        resultat.append({
            "scenario": scenario,
            "postes": postes,
            "non_armes": [p for p in postes if p["poste"].obligatoire and not p["arme"]],
        })
    return resultat


def _nom_marin(creneau):
    marin = creneau.marin
    return f"{marin.profile.grade} {marin.get_full_name() or marin.username}".strip()


def figer_alertes(etat):
    """Instantané JSON de l'état d'alerte, conservé avec la version publiée."""
    return [
        {
            "scenario": e["scenario"].libelle,
            "famille": e["scenario"].get_famille_display(),
            "postes": [
                {
                    "role": p["poste"].libelle,
                    "obligatoire": p["poste"].obligatoire,
                    "marin": _nom_marin(p["creneau"]) if p["arme"] else "",
                }
                for p in e["postes"]
            ],
        }
        for e in etat
    ]


def signaler_postes_non_armes(feuille, user):
    """À la publication : prévient le COMA responsable de chaque scénario touché
    et le rédacteur de la feuille, et trace l'alerte. Rien n'est réaffecté."""
    problemes = [
        (e["scenario"], [p["poste"].libelle for p in e["non_armes"]])
        for e in etat_alertes(feuille.ship, feuille.date, feuille.equipage) if e["non_armes"]
    ]
    if not problemes:
        return
    destinataires = {}
    if feuille.created_by_id:
        destinataires[feuille.created_by_id] = feuille.created_by
    for scenario, _ in problemes:
        for coma in titulaires_commandant_adjoint(feuille.ship, scenario.adjoint_responsable, feuille.equipage):
            destinataires[coma.pk] = coma
    detail = " ; ".join(f"{s.libelle} : {', '.join(roles)}" for s, roles in problemes)
    AuditLog.objects.create(
        actor=user, action="feuille_service_postes_alerte_non_armes",
        details=f"Feuille de service du {feuille.date:%d/%m/%Y} ({feuille.ship}) publiée avec des postes "
                f"d'alerte obligatoires non armés — {detail}",
    )
    for destinataire in destinataires.values():
        Notification.objects.create(
            user=destinataire,
            verb=f"Feuille de service du {feuille.date:%d/%m/%Y} : postes d'alerte obligatoires non armés — {detail}",
            level=NotificationLevel.WARNING,
            url=reverse("feuille-service-detail", args=[feuille.ship_id, f"{feuille.date:%Y-%m-%d}"]),
        )


def _donnees_scenario(scenario):
    return {
        "libelle": scenario.libelle, "famille": scenario.famille, "adjoint_sigle": scenario.adjoint_sigle,
        "ordre": scenario.ordre, "actif": scenario.actif,
        "postes": [
            {"libelle": p.libelle, "fonction_id": p.fonction_id, "obligatoire": p.obligatoire, "ordre": p.ordre}
            for p in scenario.postes.all()
        ],
    }


def _valider_donnees(ship, donnees):
    """Message d'erreur si la définition proposée est incohérente, sinon None."""
    if not donnees["libelle"]:
        return "Le nom du scénario est obligatoire."
    if donnees["famille"] not in dict(ScenarioAlerte.FAMILLE_CHOICES):
        return "Famille inconnue."
    if donnees["adjoint_sigle"] and donnees["adjoint_sigle"] not in CommandantAdjoint.values:
        return "COMA responsable inconnu."
    if not donnees["postes"]:
        return "Un scénario doit comporter au moins un poste."
    fonctions = set(FonctionFeuilleService.objects.filter(ship=ship).values_list("pk", flat=True))
    if any(p["fonction_id"] is not None and p["fonction_id"] not in fonctions for p in donnees["postes"]):
        return "Fonction de service inconnue sur cette unité."
    return None


def _controler_application(ship, donnees, scenario):
    """Message d'erreur si la définition ne peut pas être appliquée maintenant
    (données incohérentes, fonction disparue, nom déjà pris), sinon None."""
    erreur = _valider_donnees(ship, donnees)
    if erreur:
        return erreur
    existe = ScenarioAlerte.objects.filter(ship=ship, libelle=donnees["libelle"])
    if scenario is not None:
        existe = existe.exclude(pk=scenario.pk)
    if existe.exists():
        return "Un scénario porte déjà ce nom."
    return None


def proposer_modification(user, ship, action, donnees=None, scenario=None):
    """Enregistre une modification de l'organisation d'alerte. Appliquée tout de
    suite si l'auteur est lui-même l'autorité de validation, sinon mise en
    attente et notifiée à l'autorité. Retourne (modification, erreur)."""
    if action == Modification.ACTION_SUPPRIMER:
        donnees = _donnees_scenario(scenario)
    else:
        erreur = _controler_application(ship, donnees, scenario)
        if erreur:
            return None, erreur
    modification = Modification.objects.create(
        ship=ship, scenario=scenario, action=action, donnees=donnees, proposee_par=user,
    )
    AuditLog.objects.create(
        actor=user, action="alerte_organisation_proposee",
        details=f"{modification} : modification de l'organisation d'alerte proposée.",
    )
    if peut_valider_organisation_alerte(user, ship):
        erreur = valider(modification, user)
        if erreur:
            return modification, erreur
    else:
        for destinataire in User.objects.filter(is_active=True, profile__ship=ship):
            if destinataire.pk != user.pk and peut_valider_organisation_alerte(destinataire, ship):
                Notification.objects.create(
                    user=destinataire,
                    verb=f"Organisation d'alerte ({ship}) : {modification} attend votre validation.",
                    level=NotificationLevel.WARNING,
                    url=reverse("feuille-service-alertes"),
                )
    return modification, None


@transaction.atomic
def valider(modification, user):
    """Applique la modification demandée au scénario en vigueur. L'état du navire
    a pu changer depuis la proposition : tout est revérifié avant d'écrire.
    Retourne un message d'erreur (la modification reste en attente, rien n'est
    écrit) ou None si elle est appliquée."""
    donnees = modification.donnees
    scenario = modification.scenario
    if modification.action != Modification.ACTION_SUPPRIMER:
        if modification.action == Modification.ACTION_MODIFIER and scenario is None:
            return "Le scénario à modifier n'existe plus : refusez cette modification."
        erreur = _controler_application(modification.ship, donnees, scenario)
        if erreur:
            return f"{erreur} Refusez cette modification ou faites-la corriger."
    if modification.action == Modification.ACTION_SUPPRIMER:
        if scenario is not None:
            scenario.delete()
        modification.scenario = None
    else:
        if scenario is None:
            scenario = ScenarioAlerte(ship=modification.ship)
        scenario.libelle, scenario.famille = donnees["libelle"], donnees["famille"]
        scenario.adjoint_sigle, scenario.ordre, scenario.actif = (
            donnees["adjoint_sigle"], donnees["ordre"], donnees["actif"],
        )
        scenario.save()
        scenario.postes.all().delete()
        PosteAlerte.objects.bulk_create([
            PosteAlerte(
                scenario=scenario, libelle=p["libelle"], fonction_id=p["fonction_id"],
                obligatoire=p["obligatoire"], ordre=p["ordre"],
            )
            for p in donnees["postes"]
        ])
        modification.scenario = scenario
    modification.statut = Modification.STATUT_VALIDEE
    modification.decidee_par, modification.decidee_le = user, timezone.now()
    modification.save(update_fields=["scenario", "statut", "decidee_par", "decidee_le", "updated_at"])
    AuditLog.objects.create(
        actor=user, action="alerte_organisation_validee",
        details=f"{modification} : validée et appliquée (navire {modification.ship}).",
    )
    _prevenir_auteur(modification, user, f"validée : {modification}.")
    return None


def refuser(modification, user, motif):
    modification.statut = Modification.STATUT_REFUSEE
    modification.decidee_par, modification.decidee_le, modification.motif_refus = user, timezone.now(), motif
    modification.save(update_fields=["statut", "decidee_par", "decidee_le", "motif_refus", "updated_at"])
    AuditLog.objects.create(
        actor=user, action="alerte_organisation_refusee",
        details=f"{modification} : refusée (navire {modification.ship}). Motif : {motif}",
    )
    _prevenir_auteur(modification, user, f"refusée : {modification}. Motif : {motif}")


def _prevenir_auteur(modification, user, message):
    auteur = modification.proposee_par
    if auteur is not None and auteur.pk != user.pk:
        Notification.objects.create(
            user=auteur, verb=f"Organisation d'alerte : modification {message}", level=NotificationLevel.INFO,
            url=reverse("feuille-service-alertes"),
        )
