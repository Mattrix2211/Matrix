"""Circuit de validation d'une version de fiche de maintenance.

Mêmes principes que la proposition d'article (assets/proposition_article.py) : machine d'états
stricte, transitions revérifiées sous verrou, refus motivé qui revient au rédacteur, auto-validation
interdite, une personne n'intervient qu'à une seule étape.

Fiche du bord : rédaction par un chef de section (visa du chef de secteur d'abord) ou un chef de
secteur, puis visa du chef de service et du commandant adjoint. Fiche flotte : mêmes visas du bord,
puis vérification par le responsable de spécialité à terre et visa de son chef ; le responsable peut
aussi rédiger directement (visa de son chef seul).
"""
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog, Roles, SpecialityChoice
from matrix.core.commandants_adjoints import service_de, titulaires_du_service
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin
from notifications.models import Notification

from . import fiche_maintenance
from .models import (
    CategorieCatalogue, ChecklistTemplate, EvenementProposition, Installation, InstallationMaintenance,
)
from .proposition_article import (
    ROLES_REDACTEURS, ErreurCircuit, chef_du, chef_specialite_optionnel, habilite_coma, secteur_de,
)

User = get_user_model()
Etat = ChecklistTemplate.Etat
Action = EvenementProposition.Action

ETAPES_BORD = (Etat.VISA_SECTEUR, Etat.VISA_SERVICE, Etat.VISA_COMA)
ETAPES_FLOTTE = ETAPES_BORD + (Etat.VERIFICATION, Etat.VISA_CHEF_SPECIALITE)
ETAPES = ETAPES_FLOTTE
ETAPES_VISA = tuple(e for e in ETAPES if e != Etat.VERIFICATION)
FONCTIONS = {
    Etat.VISA_SECTEUR: "Chef de secteur", Etat.VISA_SERVICE: "Chef de service", Etat.VISA_COMA: "Commandant adjoint",
    Etat.VERIFICATION: "Responsable de spécialité", Etat.VISA_CHEF_SPECIALITE: "Chef du responsable de spécialité",
}
# Rôle inscrit sur une version rédigée directement par un responsable de spécialité.
ROLE_RESPONSABLE = "RESPONSABLE_SPECIALITE"
DIRECT, PAR_LE_BORD = "direct", "bord"


def est_flotte(version):
    return version.fiche.niveau == "FLOTTE"


def specialite_id_de(version):
    fiche = version.fiche
    return fiche.categorie.specialite_id if fiche.categorie_id else fiche.specialite_id


def circuit(version):
    """Étapes de cette version : le chef de secteur ne vise pas sa propre version, le responsable de
    spécialité qui rédige n'a besoin que du visa de son chef."""
    if not est_flotte(version):
        etapes = ETAPES_BORD
    elif version.role_redacteur == ROLE_RESPONSABLE:
        return (Etat.VISA_CHEF_SPECIALITE,)
    else:
        etapes = ETAPES_FLOTTE
    if version.role_redacteur == Roles.CHEF_SECTEUR:
        return tuple(e for e in etapes if e != Etat.VISA_SECTEUR)
    return etapes


def etape_suivante(version):
    etapes = circuit(version)
    index = etapes.index(version.etat)
    return etapes[index + 1] if index + 1 < len(etapes) else Etat.VALIDEE


def dans_le_perimetre(user, installation):
    return Installation.objects.filter(build_scope_q(user, ""), pk=installation.pk).exists()


def _flotte_visible_q(user):
    """Versions de fiche flotte que l'utilisateur peut consulter : celles qui s'appliquent, les siennes,
    celles de son périmètre de visa et celles de sa spécialité."""
    q = Q(etat=Etat.VALIDEE) | Q(redacteur=user) | Q(evenements__user=user)
    profil = getattr(user, "profile", None)
    if profil is not None:
        if profil.role == Roles.CHEF_SECTEUR and profil.sector_id:
            q |= Q(secteur_origine_id=profil.sector_id)
        if profil.role == Roles.CHEF_SERVICE and profil.service_id:
            q |= Q(service_origine_id=profil.service_id)
        if user_role_level(user) >= RoleLevel.ETAT_MAJOR and profil.ship_id:
            q |= Q(ship_origine_id=profil.ship_id)
    en_aval = [Etat.VERIFICATION, Etat.VISA_CHEF_SPECIALITE]
    q |= Q(fiche__categorie__specialite__responsables__user=user, etat__in=en_aval)
    q |= Q(fiche__specialite__responsables__user=user, etat__in=en_aval)
    q |= Q(verificateur__specialites_dont_il_est_responsable__chef_designe__chef=user, etat=Etat.VISA_CHEF_SPECIALITE)
    return q


def versions_visibles(user):
    """Versions de fiche de l'espace de travail de l'utilisateur (installations du bord et fiches flotte)."""
    bord = Q(fiche__installation__isnull=False) & build_scope_q(user, "fiche__installation__")
    flotte = Q(fiche__installation__isnull=True) & (Q() if is_master_admin(user) else _flotte_visible_q(user))
    return (ChecklistTemplate.objects.filter(fiche__isnull=False).filter(bord | flotte).distinct()
            .select_related("fiche__installation__service", "fiche__installation__ship", "fiche__categorie__specialite",
                            "fiche__specialite", "service_origine", "ship_origine", "redacteur", "qualification"))


def fiches_visibles(user):
    """Fiches consultables : celles des installations du périmètre, et les fiches flotte ayant une version visible."""
    flotte = versions_visibles(user).filter(fiche__installation__isnull=True)
    return (InstallationMaintenance.objects
            .filter((Q(installation__isnull=False) & build_scope_q(user, "installation__")) | Q(pk__in=flotte.values("fiche_id")))
            .select_related("installation__service", "installation__ship", "categorie__specialite", "specialite"))


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


def peut_proposer_flotte(user):
    """(bool, raison) : le bord propose une fiche flotte ou sa modification (chef de section ou de secteur)."""
    profil = getattr(user, "profile", None)
    if profil is None or profil.role not in ROLES_REDACTEURS:
        return False, "Seul un chef de section ou un chef de secteur peut proposer une fiche flotte."
    if user_role_level(user) < niveau_requis_pour(user, "fiche_flotte_proposition"):
        return False, "Votre niveau ne permet pas de proposer une fiche flotte."
    if equipage_a_terre_lecture_seule(user):
        return False, "Lecture seule : votre équipage est à terre."
    if service_de(user) is None:
        return False, "Votre fiche n'est rattachée à aucun service : proposition impossible."
    if profil.role == Roles.CHEF_SECTION and secteur_de(user) is None:
        return False, "Votre fiche n'est rattachée à aucun secteur : proposition impossible."
    return True, ""


def est_responsable(user, specialite_id):
    return (user.is_active and specialite_id is not None
            and user.specialites_dont_il_est_responsable.filter(specialite_id=specialite_id).exists())


def mode_redaction_flotte(user, specialite_id):
    """(mode, raison) : DIRECT pour le responsable de la spécialité, PAR_LE_BORD pour un chef de section ou de secteur."""
    if est_responsable(user, specialite_id):
        if equipage_a_terre_lecture_seule(user):
            return None, "Lecture seule : votre équipage est à terre."
        return DIRECT, ""
    autorise, raison = peut_proposer_flotte(user)
    return (PAR_LE_BORD, "") if autorise else (None, raison)


def _etapes_de(version, user):
    return set(version.evenements.filter(user=user, action__in=[Action.VISEE, Action.VERIFIEE]).values_list("etape", flat=True))


def _habilite(user, version):
    profil = getattr(user, "profile", None)
    if version.etat == Etat.VISA_SECTEUR:
        return (profil is not None and profil.role == Roles.CHEF_SECTEUR
                and version.secteur_id is not None and profil.sector_id == version.secteur_id)
    if version.etat == Etat.VISA_SERVICE:
        return (profil is not None and profil.role == Roles.CHEF_SERVICE
                and version.service is not None and profil.service_id == version.service.pk)
    if version.etat == Etat.VISA_COMA:
        return version.ship_id is not None and habilite_coma(user, version)
    if version.etat == Etat.VERIFICATION:
        return est_responsable(user, specialite_id_de(version))
    if version.etat == Etat.VISA_CHEF_SPECIALITE:
        chef = chef_du(version.verificateur, specialite_id_de(version))
        return chef is not None and chef.pk == user.pk
    return False


def peut_agir(user, version):
    """(bool, raison) : l'utilisateur peut-il viser, vérifier ou renvoyer la version à l'étape en cours ?"""
    if version.etat not in ETAPES:
        return False, "Cette version n'est plus en cours de visa."
    if not user.is_active or equipage_a_terre_lecture_seule(user):
        return False, "Vous ne pouvez pas intervenir sur cette version."
    if version.redacteur_id == user.pk:
        return False, "Vous ne pouvez pas viser votre propre version."
    if not _habilite(user, version):
        return False, "Vous n'êtes pas le valideur de cette étape."
    if not est_flotte(version) and not dans_le_perimetre(user, version.fiche.installation):
        return False, "Vous n'êtes pas le valideur de cette étape."
    if _etapes_de(version, user) - {version.etat}:
        return False, "Vous êtes déjà intervenu à une autre étape de cette version."
    return True, ""


def _candidats(version, etat):
    """Candidats probables d'une étape (filtrés ensuite par peut_agir)."""
    actifs = User.objects.filter(is_active=True)
    if etat == Etat.VISA_SECTEUR:
        return actifs.filter(profile__role=Roles.CHEF_SECTEUR, profile__sector_id=version.secteur_id) if version.secteur_id else actifs.none()
    if etat == Etat.VISA_SERVICE:
        service = version.service
        return actifs.filter(profile__role=Roles.CHEF_SERVICE, profile__service_id=service.pk) if service else actifs.none()
    if etat == Etat.VERIFICATION:
        return actifs.filter(specialites_dont_il_est_responsable__specialite_id=specialite_id_de(version))
    if etat == Etat.VISA_CHEF_SPECIALITE:
        if version.verificateur_id is None:
            # Avant la vérification : les chefs de tous les responsables de la spécialité.
            return actifs.filter(responsables_specialite_diriges__responsable__specialite_id=specialite_id_de(version))
        chef = chef_du(version.verificateur, specialite_id_de(version))
        return actifs.filter(pk=chef.pk) if chef else actifs.none()
    if version.ship_id is None:
        return actifs.none()
    titulaires = titulaires_du_service(version.service, version.equipage)
    if titulaires.exists():
        return titulaires
    return actifs.filter(profile__ship_id=version.ship_id, profile__role__in=[
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
    if version.etat == Etat.VISA_CHEF_SPECIALITE:
        return "Aucun chef n'est désigné pour le responsable de spécialité de cette fiche : l'administrateur doit le renseigner."
    return f"Aucun valideur disponible pour l'étape « {version.get_etat_display()} » : signalez-le au commandant ou à l'administrateur."


def versions_a_viser(user):
    """Versions visibles où l'utilisateur doit intervenir maintenant (liste « Fiches à valider »)."""
    return [v for v in versions_visibles(user).filter(etat__in=ETAPES) if peut_agir(user, v)[0]]


def nom(user):
    return (user.get_full_name() or user.username) if user else "—"


# --- Frise ---

def _noms_candidats(version, etape):
    return ", ".join(nom(u) for u in _candidats(version, etape).distinct()[:3]) or "Non désigné"


def frise(version):
    """Étapes avec organisme, fonction, service et titulaire : état faite, actuelle, refusee ou avenir."""
    flotte = est_flotte(version)
    service = version.service
    nom_service = service.name if service else "—"
    organisme = version.ship_origine.name if flotte and version.ship_origine_id else (
        "Terre" if flotte else version.fiche.installation.ship.name)
    etapes = circuit(version)
    refus = version.evenements.filter(action=Action.REFUSEE).order_by("created_at").last()
    validee, refusee = version.etat == Etat.VALIDEE, version.etat == Etat.REFUSEE
    courante = refus.etape if refusee and refus else version.etat
    visas = {e.etape: e.user for e in version.evenements.filter(action__in=[Action.VISEE, Action.VERIFIEE]).select_related("user")}
    fonction = "Responsable de spécialité" if version.role_redacteur == ROLE_RESPONSABLE else (
        version.role_redacteur and Roles(version.role_redacteur).label)
    elements = [{"libelle": "Rédaction", "etat": "faite", "organisme": organisme, "fonction": fonction,
                 "service": nom_service if service else "Spécialité", "titulaire": nom(version.redacteur)}]
    for etape in etapes:
        if validee or (courante in etapes and etapes.index(etape) < etapes.index(courante)):
            etat = "faite"
        elif etape == courante:
            etat = "refusee" if refusee else "actuelle"
        else:
            etat = "avenir"
        fonction = FONCTIONS[etape]
        if etape == Etat.VISA_COMA and service and service.commandant_adjoint:
            fonction = f"{fonction} ({service.commandant_adjoint})"
        terre = etape in (Etat.VERIFICATION, Etat.VISA_CHEF_SPECIALITE)
        titulaire = nom(visas[etape]) if etape in visas else _noms_candidats(version, etape)
        elements.append({"libelle": FONCTIONS[etape], "etat": etat, "organisme": "Terre" if terre else organisme,
                         "fonction": fonction, "service": "Spécialité" if terre else nom_service, "titulaire": titulaire})
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


def notifier_fiche(fiche, destinataires, texte):
    """Notification liée à la fiche elle-même (signalement, fiche flotte d'origine modifiée)."""
    cible = ContentType.objects.get_for_model(InstallationMaintenance)
    for destinataire in {u.pk: u for u in destinataires}.values():
        Notification.objects.create(user=destinataire, verb=texte, content_type=cible, object_id=str(fiche.pk))


def _libelle_cible(version):
    return version.fiche.installation.designation if not est_flotte(version) else f"fiche flotte · {version.fiche.cible}"


def _notifier_etape(version):
    _notifier(version, valideurs(version),
              f"Fiche de maintenance « {version.name} » v{version.numero} ({_libelle_cible(version)}) : "
              f"{version.get_etat_display().lower()} attendu(e).")


def _verrouiller(pk, etat_attendu):
    version = (ChecklistTemplate.objects.select_for_update(of=("self",))
               .select_related("fiche__installation__service", "fiche__installation__ship", "fiche__categorie__specialite",
                               "fiche__specialite", "service_origine", "ship_origine", "redacteur", "verificateur")
               .get(pk=pk, fiche__isnull=False))
    if version.etat != etat_attendu:
        raise ErreurCircuit("Cette version n'est plus à cette étape : actualisez la page.")
    return version


def _controler(user, version):
    autorise, raison = peut_agir(user, version)
    if not autorise:
        raise ErreurCircuit(raison)


def _controler_contenu(contenu, installation, fiche, voisines, exiger_resume=False):
    """Contrôles communs à toutes les fiches ; `voisines` : fiches qui se partagent le même jeu de gammes."""
    fiche_maintenance.verifier_contenu(contenu, installation, fiche)
    if not contenu["name"].strip():
        raise ErreurCircuit("Le titre de la fiche est obligatoire.")
    gamme = fiche_maintenance.libelle_gamme(contenu["mode_declenchement"], contenu["intervalle"], contenu["unite_intervalle"], contenu["seuil_heures"])
    if gamme == "—":
        raise ErreurCircuit("Indiquez la gamme : une périodicité, un nombre d'heures de marche, ou les deux.")
    if gamme in fiche_maintenance.gammes_des_fiches(voisines, sauf=fiche):
        raise ErreurCircuit(f"Une fiche existe déjà pour la gamme « {gamme} » : modifiez-la plutôt.")
    if exiger_resume and not contenu["resume_modifications"].strip():
        raise ErreurCircuit("Indiquez en une phrase ce qui change par rapport à la version validée.")


def voisines_de(fiche_ou_cible):
    """Fiches qui se partagent les gammes : celles de l'installation, de la catégorie ou de l'équipement visé."""
    if isinstance(fiche_ou_cible, InstallationMaintenance):
        fiche = fiche_ou_cible
        if fiche.installation_id:
            return fiche.installation.maintenances.all()
        cible = {"categorie": fiche.categorie} if fiche.categorie_id else {
            "equipement": fiche.equipement, "reference_equipement": fiche.reference_equipement, "classe_navire": fiche.classe_navire}
    else:
        cible = fiche_ou_cible
    if cible.get("categorie") is not None:
        return InstallationMaintenance.objects.filter(niveau="FLOTTE", categorie=cible["categorie"])
    return InstallationMaintenance.objects.filter(
        niveau="FLOTTE", categorie__isnull=True, equipement__iexact=cible["equipement"],
        reference_equipement__iexact=cible.get("reference_equipement", ""), classe_navire__iexact=cible.get("classe_navire", ""))


def _controler_contenu_bord(contenu, installation, fiche=None, exiger_resume=False):
    _controler_contenu(contenu, installation, fiche, installation.maintenances.all(), exiger_resume)


def _controler_contenu_flotte(contenu, fiche_ou_cible, fiche=None, exiger_resume=False):
    """`fiche_ou_cible` : la fiche existante, ou la cible d'une nouvelle fiche (catégorie, ou équipement et spécialité)."""
    materiel = bool(fiche.categorie_id) if fiche else fiche_ou_cible.get("categorie") is not None
    # Le matériel n'a pas de compteur d'heures : sa fiche est calendaire.
    if materiel and (contenu["mode_declenchement"] != "CALENDRIER" or not contenu["intervalle"]):
        raise ErreurCircuit("Une fiche de matériel est calendaire : indiquez une périodicité.")
    if fiche is None and not materiel:
        equipement = fiche_ou_cible.get("equipement", "").strip()
        if not equipement or max(len(equipement), len(fiche_ou_cible.get("reference_equipement", "")),
                                 len(fiche_ou_cible.get("classe_navire", ""))) > 100:
            raise ErreurCircuit("Indiquez l'installation visée (désignation de 100 caractères au plus).")
    _controler_contenu(contenu, None, fiche, voisines_de(fiche or fiche_ou_cible), exiger_resume)


def _lier_signalement(signalement, fiche, version):
    if signalement is None:
        return
    if signalement.fiche_id != fiche.pk:
        raise ErreurCircuit("Ce signalement concerne une autre fiche.")
    signalement.traite, signalement.version_proposee = True, version
    signalement.save(update_fields=["traite", "version_proposee", "updated_at"])


@transaction.atomic
def soumettre(user, installation, contenu, fiche=None, origine=None, signalement=None):
    """Lance le circuit pour une nouvelle fiche (fiche=None) ou une nouvelle version de la fiche donnée.
    `origine` : fiche flotte dont la nouvelle fiche est l'adaptation locale."""
    autorise, raison = peut_rediger(user, installation)
    if not autorise:
        raise ErreurCircuit(raison)
    # Verrou de l'installation : deux soumissions concurrentes de la même gamme se suivent.
    Installation.objects.select_for_update().get(pk=installation.pk)
    if fiche is not None:
        fiche = InstallationMaintenance.objects.select_for_update().get(pk=fiche.pk, installation=installation)
        if fiche.version_en_cours:
            raise ErreurCircuit("Une version de cette fiche est déjà en cours de validation.")
    _controler_contenu_bord(contenu, installation, fiche, exiger_resume=fiche is not None)
    if fiche is None:
        champs = {}
        if origine is not None:
            champs = {"origine": origine, "origine_numero": origine.version_validee.numero}
        fiche = InstallationMaintenance.objects.create(
            installation=installation, title=contenu["name"], periodicity="—", created_by=user, updated_by=user, **champs)
    version = fiche_maintenance.creer_version(
        fiche, contenu, user, role_redacteur=user.profile.role, equipage=user.profile.equipage)
    version.etat = circuit(version)[0]
    version.save(update_fields=["etat"])
    _lier_signalement(signalement, fiche, version)
    _tracer(version, user, Action.SOUMISE, version.etat)
    _notifier_etape(version)
    return version


@transaction.atomic
def soumettre_flotte(user, contenu, cible=None, fiche=None, signalement=None):
    """Lance le circuit d'une fiche flotte : nouvelle fiche (`cible` : catégorie, ou équipement et spécialité) ou
    nouvelle version de `fiche`. Le responsable de spécialité rédige directement ; le bord propose."""
    if fiche is not None:
        fiche = InstallationMaintenance.objects.select_for_update(of=("self",)).select_related("categorie__specialite", "specialite").get(
            pk=fiche.pk, niveau="FLOTTE")
        if fiche.version_en_cours:
            raise ErreurCircuit("Une version de cette fiche est déjà en cours de validation.")
        specialite_id = fiche.specialite_visee.pk
    else:
        categorie = cible.get("categorie")
        if categorie is not None:
            # Verrou de la catégorie : deux propositions concurrentes de la même gamme se suivent.
            categorie = CategorieCatalogue.objects.select_for_update(of=("self",)).select_related("specialite").get(pk=categorie.pk)
            cible = {"categorie": categorie}
            specialite_id = categorie.specialite_id
        else:
            # Verrou de la spécialité : même garantie pour les fiches flotte d'installation.
            specialite_id = SpecialityChoice.objects.select_for_update().get(pk=cible["specialite"].pk).pk
    mode, raison = mode_redaction_flotte(user, specialite_id)
    if mode is None:
        raise ErreurCircuit(raison)
    _controler_contenu_flotte(contenu, fiche or cible, fiche, exiger_resume=fiche is not None)
    chef = chef_du(user, specialite_id) if mode == DIRECT else None
    if mode == DIRECT and chef is None and not chef_specialite_optionnel():
        raise ErreurCircuit("Aucun chef n'est désigné pour votre responsabilité de spécialité : "
                            "demandez à l'administrateur de le renseigner avant de rédiger.")
    if fiche is None:
        fiche = InstallationMaintenance.objects.create(
            niveau="FLOTTE", title=contenu["name"], periodicity="—", created_by=user, updated_by=user, **cible)
    champs = {"role_redacteur": ROLE_RESPONSABLE if mode == DIRECT else user.profile.role, "equipage": user.profile.equipage}
    if mode == DIRECT:
        champs["verificateur"] = user
    else:
        service = service_de(user)
        champs.update(ship_origine=service.ship, service_origine=service, secteur_origine=secteur_de(user))
    version = fiche_maintenance.creer_version(fiche, contenu, user, **champs)
    version.etat = circuit(version)[0]
    version.save(update_fields=["etat"])
    _lier_signalement(signalement, fiche, version)
    _tracer(version, user, Action.SOUMISE, version.etat)
    if mode == DIRECT and chef is None:
        _tracer(version, user, Action.VERIFIEE, Etat.VERIFICATION, "Étape du chef sautée : aucun chef désigné (configuration explicite).")
        _publier(version, user)
    else:
        _notifier_etape(version)
    return version


@transaction.atomic
def resoumettre(user, pk, contenu):
    """Le rédacteur corrige une version renvoyée et relance le circuit."""
    version = _verrouiller(pk, Etat.REFUSEE)
    if version.redacteur_id != user.pk:
        raise ErreurCircuit("Seul le rédacteur peut corriger sa version.")
    resume = version.numero > 1
    if est_flotte(version):
        if version.role_redacteur == ROLE_RESPONSABLE:
            mode, raison = mode_redaction_flotte(user, specialite_id_de(version))
            if mode != DIRECT:
                raise ErreurCircuit(raison or "Vous n'êtes plus responsable de cette spécialité.")
        else:
            autorise, raison = peut_proposer_flotte(user)
            if not autorise:
                raise ErreurCircuit(raison)
        _controler_contenu_flotte(contenu, version.fiche, version.fiche, exiger_resume=resume)
    else:
        autorise, raison = peut_rediger(user, version.fiche.installation)
        if not autorise:
            raise ErreurCircuit(raison)
        _controler_contenu_bord(contenu, version.fiche.installation, version.fiche, exiger_resume=resume)
    fiche_maintenance.remplacer_contenu(version, contenu)
    version.motif_refus = ""
    version.etat = circuit(version)[0]
    version.save(update_fields=["motif_refus", "etat"])
    _tracer(version, user, Action.RESOUMISE)
    _notifier_etape(version)


def _publier(version, user):
    """Dernier visa : la fiche prend le contenu de la version, le rédacteur est prévenu."""
    version.etat, version.valide_le = Etat.VALIDEE, timezone.now()
    version.save(update_fields=["etat", "valide_le", "verificateur"])
    fiche_maintenance.appliquer_a_la_fiche(version)
    _tracer(version, user, Action.PUBLIEE)
    _notifier(version, [version.redacteur] if version.redacteur else [],
              f"Votre fiche « {version.name} » v{version.numero} est validée : elle s'applique désormais.")
    for adaptation in version.fiche.adaptations.select_related("installation"):
        adaptation.origine_en_attente = version.numero
        adaptation.save(update_fields=["origine_en_attente", "updated_at"])
        notifier_fiche(adaptation, responsables_bord(adaptation.installation),
                       f"La fiche flotte « {version.name} » est passée en v{version.numero} : "
                       f"reprendre les changements ou garder votre adaptation ({adaptation.installation.designation}) ?")


def responsables_bord(installation):
    """Chefs de secteur de l'installation (ceux qui décident de ses fiches), à défaut son chef de service."""
    actifs = User.objects.filter(is_active=True)
    chefs = list(actifs.filter(profile__role=Roles.CHEF_SECTEUR, profile__sector_id=installation.sector_id))
    return chefs or list(actifs.filter(profile__role=Roles.CHEF_SERVICE, profile__service_id=installation.service_id))


@transaction.atomic
def viser(user, pk, etat_attendu):
    """Donne le visa de l'étape en cours ; le dernier visa valide la version."""
    if etat_attendu not in ETAPES_VISA:
        raise ErreurCircuit("Cette étape n'est pas un visa.")
    version = _verrouiller(pk, etat_attendu)
    _controler(user, version)
    _tracer(version, user, Action.VISEE, version.etat)
    version.etat = etape_suivante(version)
    if version.etat == Etat.VALIDEE:
        _publier(version, user)
    else:
        version.save(update_fields=["etat"])
        _notifier_etape(version)


@transaction.atomic
def verifier(user, pk, contenu=None):
    """Le responsable de spécialité corrige éventuellement la fiche, puis la transmet à son chef."""
    version = _verrouiller(pk, Etat.VERIFICATION)
    _controler(user, version)
    fiche = version.fiche
    if contenu is not None:
        _controler_contenu_flotte(contenu, fiche, fiche)
        avant = fiche_maintenance.contenu_de(version)
        fiche_maintenance.remplacer_contenu(version, contenu)
        if fiche_maintenance.contenu_de(version) != avant:
            _tracer(version, user, Action.CORRIGEE, Etat.VERIFICATION, "Contenu corrigé par le responsable de spécialité.")
    chef = chef_du(user, specialite_id_de(version))
    if chef is None and not chef_specialite_optionnel():
        raise ErreurCircuit("Aucun chef n'est désigné pour votre responsabilité de spécialité : "
                            "demandez à l'administrateur de le renseigner avant de transmettre.")
    acteurs = set(version.evenements.filter(action__in=[Action.VISEE, Action.VERIFIEE]).values_list("user_id", flat=True))
    if chef is not None and (chef.pk == version.redacteur_id or chef.pk in acteurs):
        raise ErreurCircuit("Le chef désigné est déjà intervenu sur cette version : elle ne peut pas lui être transmise.")
    version.verificateur = user
    _tracer(version, user, Action.VERIFIEE, Etat.VERIFICATION,
            "" if chef else "Étape du chef sautée : aucun chef désigné (configuration explicite).")
    if chef is None:
        _publier(version, user)
        return
    version.etat = Etat.VISA_CHEF_SPECIALITE
    version.save(update_fields=["etat", "verificateur"])
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
