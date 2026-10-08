"""Circuit de validation bord d'une version de fiche de maintenance d'installation.

Mêmes principes que la proposition d'article (assets/proposition_article.py) : machine d'états
stricte, transitions revérifiées sous verrou, refus motivé qui revient au rédacteur, auto-validation
interdite, une personne n'intervient qu'à une seule étape. Rédaction par un chef de section (visa du
chef de secteur d'abord) ou un chef de secteur, puis visa du chef de service et du commandant adjoint.
"""
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog, Roles
from matrix.core.commandants_adjoints import titulaires_du_service
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from notifications.models import Notification

from . import fiche_maintenance
from .models import ChecklistTemplate, EvenementProposition, Installation, InstallationMaintenance
from .proposition_article import ROLES_REDACTEURS, ErreurCircuit, habilite_coma

User = get_user_model()
Etat = ChecklistTemplate.Etat
Action = EvenementProposition.Action

ETAPES = (Etat.VISA_SECTEUR, Etat.VISA_SERVICE, Etat.VISA_COMA)
FONCTIONS = {Etat.VISA_SECTEUR: "Chef de secteur", Etat.VISA_SERVICE: "Chef de service", Etat.VISA_COMA: "Commandant adjoint"}


def circuit(version):
    """Étapes de cette version : le chef de secteur ne vise pas sa propre version."""
    if version.role_redacteur == Roles.CHEF_SECTEUR:
        return tuple(e for e in ETAPES if e != Etat.VISA_SECTEUR)
    return ETAPES


def etape_suivante(version):
    etapes = circuit(version)
    index = etapes.index(version.etat)
    return etapes[index + 1] if index + 1 < len(etapes) else Etat.VALIDEE


def dans_le_perimetre(user, installation):
    return Installation.objects.filter(build_scope_q(user, ""), pk=installation.pk).exists()


def versions_visibles(user):
    """Versions de fiche d'installation de l'espace de travail de l'utilisateur."""
    return (ChecklistTemplate.objects.filter(fiche__isnull=False, fiche__installation__isnull=False)
            .filter(build_scope_q(user, "fiche__installation__"))
            .select_related("fiche__installation__service", "fiche__installation__ship", "redacteur", "qualification"))


# --- Qui peut quoi ---

def peut_rediger(user, installation):
    """(bool, raison) : rédiger ou proposer une version pour cette installation."""
    profil = getattr(user, "profile", None)
    if profil is None or profil.role not in ROLES_REDACTEURS:
        return False, "Seul un chef de section ou un chef de secteur peut rédiger une fiche."
    if user_role_level(user) < niveau_requis_pour(user, "fiche_bord_redaction"):
        return False, "Votre niveau ne permet pas de rédiger une fiche de maintenance."
    if equipage_a_terre_lecture_seule(user):
        return False, "Lecture seule : votre équipage est à terre."
    if not dans_le_perimetre(user, installation):
        return False, "Cette installation est hors de votre périmètre."
    return True, ""


def _etapes_de(version, user):
    return set(version.evenements.filter(user=user, action=Action.VISEE).values_list("etape", flat=True))


def _habilite(user, version):
    profil = getattr(user, "profile", None)
    installation = version.fiche.installation
    if version.etat == Etat.VISA_SECTEUR:
        return profil is not None and profil.role == Roles.CHEF_SECTEUR and profil.sector_id == installation.sector_id
    if version.etat == Etat.VISA_SERVICE:
        return profil is not None and profil.role == Roles.CHEF_SERVICE and profil.service_id == installation.service_id
    if version.etat == Etat.VISA_COMA:
        return habilite_coma(user, version)
    return False


def peut_agir(user, version):
    """(bool, raison) : l'utilisateur peut-il viser ou renvoyer la version à l'étape en cours ?"""
    if version.etat not in ETAPES:
        return False, "Cette version n'est plus en cours de visa."
    if not user.is_active or equipage_a_terre_lecture_seule(user):
        return False, "Vous ne pouvez pas intervenir sur cette version."
    if version.redacteur_id == user.pk:
        return False, "Vous ne pouvez pas viser votre propre version."
    if not _habilite(user, version) or not dans_le_perimetre(user, version.fiche.installation):
        return False, "Vous n'êtes pas le valideur de cette étape."
    if _etapes_de(version, user) - {version.etat}:
        return False, "Vous êtes déjà intervenu à une autre étape de cette version."
    return True, ""


def _candidats(version, etat):
    """Candidats probables d'une étape (filtrés ensuite par peut_agir)."""
    installation = version.fiche.installation
    actifs = User.objects.filter(is_active=True)
    if etat == Etat.VISA_SECTEUR:
        return actifs.filter(profile__role=Roles.CHEF_SECTEUR, profile__sector_id=installation.sector_id)
    if etat == Etat.VISA_SERVICE:
        return actifs.filter(profile__role=Roles.CHEF_SERVICE, profile__service_id=installation.service_id)
    titulaires = titulaires_du_service(installation.service, version.equipage)
    if titulaires.exists():
        return titulaires
    return actifs.filter(profile__ship_id=installation.ship_id, profile__role__in=[
        Roles.CHEF_SERVICE, Roles.ETAT_MAJOR, Roles.COMMANDANT_EN_SECOND, Roles.COMMANDANT, Roles.ADMIN_NAVIRE])


def valideurs(version):
    """Personnes pouvant agir maintenant (notifications et affichage de l'attente)."""
    if version.etat not in ETAPES:
        return []
    return [u for u in _candidats(version, version.etat).distinct() if peut_agir(u, version)[0]]


def message_blocage(version, candidats=None):
    """Explication quand personne ne peut agir (`candidats` : valideurs déjà calculés)."""
    if candidats is None:
        candidats = valideurs(version)
    if version.etat not in ETAPES or candidats:
        return ""
    return f"Aucun valideur disponible pour l'étape « {version.get_etat_display()} » : signalez-le au commandant ou à l'administrateur."


def nom(user):
    return (user.get_full_name() or user.username) if user else "—"


# --- Frise ---

def frise(version):
    """Étapes avec organisme, fonction, service et titulaire : état faite, actuelle, refusee ou avenir."""
    installation = version.fiche.installation
    etapes = circuit(version)
    refus = version.evenements.filter(action=Action.REFUSEE).order_by("created_at").last()
    validee, refusee = version.etat == Etat.VALIDEE, version.etat == Etat.REFUSEE
    courante = refus.etape if refusee and refus else version.etat
    visas = {e.etape: e.user for e in version.evenements.filter(action=Action.VISEE).select_related("user")}
    organisme = installation.ship.name
    elements = [{"libelle": "Rédaction", "etat": "faite", "organisme": organisme, "fonction": version.role_redacteur and Roles(version.role_redacteur).label,
                 "service": installation.service.name, "titulaire": nom(version.redacteur)}]
    for etape in etapes:
        if validee or (courante in etapes and etapes.index(etape) < etapes.index(courante)):
            etat = "faite"
        elif etape == courante:
            etat = "refusee" if refusee else "actuelle"
        else:
            etat = "avenir"
        fonction = FONCTIONS[etape]
        if etape == Etat.VISA_COMA and installation.service.commandant_adjoint:
            fonction = f"{fonction} ({installation.service.commandant_adjoint})"
        titulaire = nom(visas[etape]) if etape in visas else ", ".join(
            nom(u) for u in _candidats(version, etape).distinct()[:3]) or "Non désigné"
        elements.append({"libelle": FONCTIONS[etape], "etat": etat, "organisme": organisme, "fonction": fonction,
                         "service": installation.service.name, "titulaire": titulaire})
    elements.append({"libelle": "Validée", "etat": "faite" if validee else "avenir"})
    return elements


# --- Transitions ---

def _tracer(version, user, action, etape="", motif=""):
    EvenementProposition.objects.create(version=version, action=action, etape=etape, user=user, motif=motif)
    AuditLog.objects.create(
        actor=user, action=f"fiche.version.{action}",
        details=f"« {version.name} » v{version.numero} ({version.pk}); étape={etape or '—'}" + (f"; {motif}" if motif else ""))


def _notifier(version, destinataires, texte):
    cible = ContentType.objects.get_for_model(ChecklistTemplate)
    for destinataire in destinataires:
        Notification.objects.create(user=destinataire, verb=texte, content_type=cible, object_id=str(version.pk))


def _notifier_etape(version):
    _notifier(version, valideurs(version),
              f"Fiche de maintenance « {version.name} » v{version.numero} ({version.fiche.installation.designation}) : "
              f"{version.get_etat_display().lower()} attendu(e).")


def _verrouiller(pk, etat_attendu):
    version = (ChecklistTemplate.objects.select_for_update(of=("self",))
               .select_related("fiche__installation__service", "fiche__installation__ship", "redacteur").get(pk=pk, fiche__isnull=False))
    if version.etat != etat_attendu:
        raise ErreurCircuit("Cette version n'est plus à cette étape : actualisez la page.")
    return version


def _controler(user, version):
    autorise, raison = peut_agir(user, version)
    if not autorise:
        raise ErreurCircuit(raison)


def _verifier_contenu(contenu, installation, fiche=None, exiger_resume=False):
    fiche_maintenance.verifier_contenu(contenu, installation, fiche)
    if not contenu["name"].strip():
        raise ErreurCircuit("Le titre de la fiche est obligatoire.")
    gamme = fiche_maintenance.libelle_gamme(contenu["mode_declenchement"], contenu["intervalle"], contenu["unite_intervalle"], contenu["seuil_heures"])
    if gamme == "—":
        raise ErreurCircuit("Indiquez la gamme : une périodicité, un nombre d'heures de marche, ou les deux.")
    if gamme in fiche_maintenance.gammes_prises(installation, sauf=fiche):
        raise ErreurCircuit(f"Une fiche existe déjà pour la gamme « {gamme} » sur cette installation : modifiez-la plutôt.")
    if exiger_resume and not contenu["resume_modifications"].strip():
        raise ErreurCircuit("Indiquez en une phrase ce qui change par rapport à la version validée.")


@transaction.atomic
def soumettre(user, installation, contenu, fiche=None):
    """Lance le circuit pour une nouvelle fiche (fiche=None) ou une nouvelle version de la fiche donnée."""
    autorise, raison = peut_rediger(user, installation)
    if not autorise:
        raise ErreurCircuit(raison)
    # Verrou de l'installation : deux soumissions concurrentes de la même gamme se suivent.
    Installation.objects.select_for_update().get(pk=installation.pk)
    if fiche is not None:
        fiche = InstallationMaintenance.objects.select_for_update().get(pk=fiche.pk, installation=installation)
        if fiche.version_en_cours:
            raise ErreurCircuit("Une version de cette fiche est déjà en cours de validation.")
    _verifier_contenu(contenu, installation, fiche, exiger_resume=fiche is not None)
    if fiche is None:
        fiche = InstallationMaintenance.objects.create(
            installation=installation, title=contenu["name"], periodicity="—", created_by=user, updated_by=user)
    version = fiche_maintenance.creer_version(
        fiche, contenu, user, role_redacteur=user.profile.role, equipage=user.profile.equipage)
    version.etat = circuit(version)[0]
    version.save(update_fields=["etat"])
    _tracer(version, user, Action.SOUMISE, version.etat)
    _notifier_etape(version)
    return version


@transaction.atomic
def resoumettre(user, pk, contenu):
    """Le rédacteur corrige une version renvoyée et relance le circuit."""
    version = _verrouiller(pk, Etat.REFUSEE)
    if version.redacteur_id != user.pk:
        raise ErreurCircuit("Seul le rédacteur peut corriger sa version.")
    autorise, raison = peut_rediger(user, version.fiche.installation)
    if not autorise:
        raise ErreurCircuit(raison)
    _verifier_contenu(contenu, version.fiche.installation, version.fiche, exiger_resume=version.numero > 1)
    fiche_maintenance.remplacer_contenu(version, contenu)
    version.motif_refus = ""
    version.etat = circuit(version)[0]
    version.save(update_fields=["motif_refus", "etat"])
    _tracer(version, user, Action.RESOUMISE)
    _notifier_etape(version)


@transaction.atomic
def viser(user, pk, etat_attendu):
    """Donne le visa de l'étape en cours ; le dernier visa valide la version."""
    if etat_attendu not in ETAPES:
        raise ErreurCircuit("Cette étape n'est pas un visa.")
    version = _verrouiller(pk, etat_attendu)
    _controler(user, version)
    _tracer(version, user, Action.VISEE, version.etat)
    version.etat = etape_suivante(version)
    if version.etat == Etat.VALIDEE:
        version.valide_le = timezone.now()
        version.save(update_fields=["etat", "valide_le"])
        fiche_maintenance.appliquer_a_la_fiche(version)
        _tracer(version, user, Action.PUBLIEE)
        _notifier(version, [version.redacteur] if version.redacteur else [],
                  f"Votre fiche « {version.name} » v{version.numero} est validée : elle s'applique désormais.")
    else:
        version.save(update_fields=["etat"])
        _notifier_etape(version)


@transaction.atomic
def refuser(user, pk, etat_attendu, motif):
    """Renvoie la version au rédacteur ; le motif est obligatoire. La version validée reste appliquée."""
    motif = (motif or "").strip()
    if not motif:
        raise ErreurCircuit("Le motif du refus est obligatoire.")
    if etat_attendu not in ETAPES:
        raise ErreurCircuit("Cette version n'est plus en cours de visa.")
    version = _verrouiller(pk, etat_attendu)
    _controler(user, version)
    _tracer(version, user, Action.REFUSEE, version.etat, motif)
    version.etat, version.motif_refus = Etat.REFUSEE, motif
    version.save(update_fields=["etat", "motif_refus"])
    _notifier(version, [version.redacteur] if version.redacteur else [],
              f"Votre fiche « {version.name} » v{version.numero} est renvoyée : {motif}")


@transaction.atomic
def dupliquer(user, version, installation_cible):
    """Copie indépendante de la fiche vers une autre installation : nouvelle fiche, nouvelles lignes, même circuit."""
    contenu = fiche_maintenance.contenu_de(version) | {"resume_modifications": ""}
    for ligne in contenu["lignes"]:
        ligne["cle"] = None
    return soumettre(user, installation_cible, contenu)
