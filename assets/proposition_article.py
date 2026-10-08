"""Circuit de visas d'une proposition d'article au catalogue : règles, transitions, visibilité.

Machine d'états stricte : chaque transition est revérifiée sous verrou, à l'étape attendue
et pour la bonne personne. Une personne ne peut intervenir qu'à une seule étape d'une proposition.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q

from accounts.models import AuditLog, Roles
from matrix.core.commandants_adjoints import service_de, titulaires_du_service
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.saisie import sans_nul
from matrix.core.scopes import is_master_admin, ship_id_for_user
from notifications.models import Notification

from .models import ArticleCatalogue, ChefResponsableSpecialite, EvenementProposition, PropositionArticle

User = get_user_model()
Etat = PropositionArticle.Etat
Action = EvenementProposition.Action

ETAPES = (Etat.VISA_SECTEUR, Etat.VISA_SERVICE, Etat.VISA_COMA, Etat.VERIFICATION, Etat.VISA_CHEF_SPECIALITE)
ETAPES_VISA = tuple(e for e in ETAPES if e != Etat.VERIFICATION)
ROLES_REDACTEURS = (Roles.CHEF_SECTION, Roles.CHEF_SECTEUR)
# Champs recopiés d'un formulaire vers la proposition (rédaction ou correction).
CHAMPS_ARTICLE = ("designation", "categorie", "marque", "reference", "nno", "duree_vie_mois", "caracteristiques")


class ErreurCircuit(Exception):
    """Transition refusée ; le message est affiché tel quel au marin."""


def chef_specialite_optionnel():
    """Configuration explicite : sans chef désigné, l'étape du chef du responsable est sautée."""
    return getattr(settings, "CATALOGUE_CHEF_SPECIALITE_OPTIONNEL", False)


def circuit(proposition):
    """Étapes de cette proposition : le chef de secteur ne vise pas sa propre proposition."""
    if proposition.role_redacteur == Roles.CHEF_SECTEUR:
        return tuple(e for e in ETAPES if e != Etat.VISA_SECTEUR)
    return ETAPES


def premiere_etape(proposition):
    return circuit(proposition)[0]


def etape_suivante(proposition):
    etapes = circuit(proposition)
    index = etapes.index(proposition.etat)
    return etapes[index + 1] if index + 1 < len(etapes) else Etat.PUBLIEE


def chef_du(responsable_user, specialite_id):
    """Chef désigné du responsable pour cette spécialité, ou None."""
    if responsable_user is None:
        return None
    lien = (ChefResponsableSpecialite.objects.select_related("chef")
            .filter(responsable__user=responsable_user, responsable__specialite_id=specialite_id, chef__is_active=True).first())
    return lien.chef if lien else None


# --- Qui peut quoi ---

def peut_proposer(user):
    """(bool, raison) : seuls un chef de section ou de secteur rattaché à un service, à bord."""
    profil = getattr(user, "profile", None)
    if profil is None or profil.role not in ROLES_REDACTEURS:
        return False, "Seul un chef de section ou un chef de secteur peut proposer un article."
    if equipage_a_terre_lecture_seule(user):
        return False, "Lecture seule : votre équipage est à terre."
    if service_de(user) is None:
        return False, "Votre fiche n'est rattachée à aucun service : proposition impossible."
    if profil.role == Roles.CHEF_SECTION and secteur_de(user) is None:
        return False, "Votre fiche n'est rattachée à aucun secteur : proposition impossible."
    return True, ""


def secteur_de(user):
    profil = user.profile
    if profil.sector_id:
        return profil.sector
    return profil.section.sector if profil.section_id else None


def _etapes_de(proposition, user):
    """Étapes où l'utilisateur est déjà intervenu (visa ou vérification)."""
    return set(proposition.evenements.filter(
        user=user, action__in=[Action.VISEE, Action.VERIFIEE]).values_list("etape", flat=True))


def habilite_coma(user, proposition):
    titulaires = titulaires_du_service(proposition.service, proposition.equipage)
    if titulaires.exists():
        return titulaires.filter(pk=user.pk).exists()
    # Repli sans titulaire : même règle que la validation d'une formation du bord, limitée au bâtiment.
    from training.web_views import peut_valider_proposition_bord

    return (ship_id_for_user(user) == proposition.ship_id
            and peut_valider_proposition_bord(user, proposition.created_by))


def _habilite(user, proposition):
    """Le rôle ou le lien de l'utilisateur correspond-il à l'étape en cours ?"""
    profil = getattr(user, "profile", None)
    etat = proposition.etat
    if etat == Etat.VISA_SECTEUR:
        return (profil is not None and profil.role == Roles.CHEF_SECTEUR
                and proposition.secteur_id is not None and profil.sector_id == proposition.secteur_id)
    if etat == Etat.VISA_SERVICE:
        return profil is not None and profil.role == Roles.CHEF_SERVICE and profil.service_id == proposition.service_id
    if etat == Etat.VISA_COMA:
        return habilite_coma(user, proposition)
    if etat == Etat.VERIFICATION:
        return user.specialites_dont_il_est_responsable.filter(specialite_id=proposition.categorie.specialite_id).exists()
    if etat == Etat.VISA_CHEF_SPECIALITE:
        chef = chef_du(proposition.verificateur, proposition.categorie.specialite_id)
        return chef is not None and chef.pk == user.pk
    return False


def peut_agir(user, proposition):
    """(bool, raison) : l'utilisateur peut-il intervenir à l'étape en cours de la proposition ?"""
    if proposition.etat not in ETAPES:
        return False, "Cette proposition n'est plus en cours de visa."
    if not user.is_active or equipage_a_terre_lecture_seule(user):
        return False, "Vous ne pouvez pas intervenir sur cette proposition."
    if proposition.created_by_id == user.pk:
        return False, "Vous ne pouvez pas viser votre propre proposition."
    if not _habilite(user, proposition):
        return False, "Vous n'êtes pas le valideur de cette étape."
    if _etapes_de(proposition, user) - {proposition.etat}:
        return False, "Vous êtes déjà intervenu à une autre étape de cette proposition."
    return True, ""


def _pool(proposition):
    """Candidats probables de l'étape en cours (filtrés ensuite par peut_agir)."""
    etat = proposition.etat
    actifs = User.objects.filter(is_active=True)
    if etat == Etat.VISA_SECTEUR:
        return actifs.filter(profile__role=Roles.CHEF_SECTEUR, profile__sector_id=proposition.secteur_id)
    if etat == Etat.VISA_SERVICE:
        return actifs.filter(profile__role=Roles.CHEF_SERVICE, profile__service_id=proposition.service_id)
    if etat == Etat.VISA_COMA:
        titulaires = titulaires_du_service(proposition.service, proposition.equipage)
        if titulaires.exists():
            return titulaires
        return actifs.filter(profile__ship_id=proposition.ship_id, profile__role__in=[
            Roles.CHEF_SERVICE, Roles.ETAT_MAJOR, Roles.COMMANDANT_EN_SECOND, Roles.COMMANDANT, Roles.ADMIN_NAVIRE])
    if etat == Etat.VERIFICATION:
        return actifs.filter(specialites_dont_il_est_responsable__specialite_id=proposition.categorie.specialite_id)
    if etat == Etat.VISA_CHEF_SPECIALITE:
        chef = chef_du(proposition.verificateur, proposition.categorie.specialite_id)
        return actifs.filter(pk=chef.pk) if chef else actifs.none()
    return actifs.none()


def valideurs(proposition):
    """Personnes pouvant agir maintenant (sert aux notifications et à l'affichage de l'attente)."""
    return [u for u in _pool(proposition).distinct() if peut_agir(u, proposition)[0]]


def message_blocage(proposition):
    """Explication quand personne ne peut agir à l'étape en cours, sinon chaîne vide."""
    if proposition.etat not in ETAPES or valideurs(proposition):
        return ""
    if proposition.etat == Etat.VISA_CHEF_SPECIALITE:
        return ("Aucun chef n'est désigné pour le responsable de spécialité qui a vérifié cet article : "
                "l'administrateur doit le renseigner.")
    return f"Aucun valideur disponible pour l'étape « {proposition.get_etat_display()} » : signalez-le au commandant ou à l'administrateur."


# --- Visibilité ---

def propositions_visibles(user):
    """Propositions que l'utilisateur peut consulter : les siennes, celles de son périmètre, celles de sa spécialité."""
    qs = PropositionArticle.objects.select_related("ship", "service", "categorie__specialite", "created_by")
    if is_master_admin(user):
        return qs
    profil = getattr(user, "profile", None)
    q = Q(created_by=user) | Q(evenements__user=user)
    if profil is not None:
        if profil.role == Roles.CHEF_SECTEUR and profil.sector_id:
            q |= Q(secteur_id=profil.sector_id)
        if profil.role == Roles.CHEF_SERVICE and profil.service_id:
            q |= Q(service_id=profil.service_id)
        if user_role_level(user) >= RoleLevel.ETAT_MAJOR and profil.ship_id:
            q |= Q(ship_id=profil.ship_id)
    en_aval = [Etat.VERIFICATION, Etat.VISA_CHEF_SPECIALITE, Etat.PUBLIEE]
    q |= Q(categorie__specialite__responsables__user=user, etat__in=en_aval)
    q |= Q(verificateur__specialites_dont_il_est_responsable__chef_designe__chef=user,
           etat__in=[Etat.VISA_CHEF_SPECIALITE, Etat.PUBLIEE])
    return qs.filter(q).distinct()


def propositions_a_viser(user):
    """Propositions visibles où l'utilisateur peut intervenir maintenant."""
    return [p for p in propositions_visibles(user).filter(etat__in=ETAPES) if peut_agir(user, p)[0]]


# --- Frise ---

def frise(proposition):
    """Étapes pour la frise d'avancement : {libelle, etat} avec etat faite, actuelle, refusee ou avenir."""
    etapes = circuit(proposition)
    refus = proposition.evenements.filter(action=Action.REFUSEE).order_by("created_at").last()
    publiee = proposition.etat == Etat.PUBLIEE
    refusee = proposition.etat == Etat.REFUSEE
    courante = refus.etape if refusee and refus else proposition.etat
    elements = [{"libelle": "Rédaction", "etat": "faite"}]
    for etape in etapes:
        if publiee or (courante in etapes and etapes.index(etape) < etapes.index(courante)):
            etat = "faite"
        elif etape == courante:
            etat = "refusee" if refusee else "actuelle"
        else:
            etat = "avenir"
        libelle = etape.label.replace("Visa du ", "").replace("Vérification par le ", "Vérification : ").capitalize()
        if etape == Etat.VISA_COMA and proposition.service.commandant_adjoint:
            libelle = f"Commandant adjoint ({proposition.service.commandant_adjoint})"
        elements.append({"libelle": libelle, "etat": etat})
    elements.append({"libelle": "Publication", "etat": "faite" if publiee else "avenir"})
    return elements


# --- Transitions ---

def _tracer(proposition, user, action, etape="", motif=""):
    EvenementProposition.objects.create(proposition=proposition, action=action, etape=etape, user=user, motif=motif)
    AuditLog.objects.create(
        actor=user, action=f"catalogue.proposition.{action}",
        details=f"« {proposition.designation} » ({proposition.pk}); étape={etape or '—'}" + (f"; {motif}" if motif else ""))


def _notifier(proposition, destinataires, texte):
    cible = ContentType.objects.get_for_model(PropositionArticle)
    for destinataire in destinataires:
        Notification.objects.create(user=destinataire, verb=texte, content_type=cible, object_id=str(proposition.pk))


def _notifier_etape(proposition):
    _notifier(proposition, valideurs(proposition),
              f"Proposition d'article « {proposition.designation} » ({proposition.service.name}) : "
              f"{proposition.get_etat_display().lower()} attendu(e).")


def _verrouiller(pk, etat_attendu):
    """Charge la proposition sous verrou et refuse si elle n'est plus à l'étape attendue."""
    proposition = (PropositionArticle.objects.select_for_update(of=("self",))
                   .select_related("service", "ship", "categorie__specialite", "created_by").get(pk=pk))
    if proposition.etat != etat_attendu:
        raise ErreurCircuit("Cette proposition n'est plus à cette étape : actualisez la page.")
    return proposition


def _controler(user, proposition):
    autorise, raison = peut_agir(user, proposition)
    if not autorise:
        raise ErreurCircuit(raison)


@transaction.atomic
def soumettre(user, proposition):
    """Enregistre la proposition d'un chef de section ou de secteur et lance le circuit."""
    autorise, raison = peut_proposer(user)
    if not autorise:
        raise ErreurCircuit(raison)
    service = service_de(user)
    proposition.service, proposition.ship = service, service.ship
    proposition.secteur = secteur_de(user)
    proposition.role_redacteur = user.profile.role
    proposition.equipage = user.profile.equipage
    proposition.created_by = proposition.updated_by = user
    proposition.etat = premiere_etape(proposition)
    proposition.save()
    _tracer(proposition, user, Action.SOUMISE, proposition.etat)
    _notifier_etape(proposition)
    return proposition


def _copier(proposition, formulaire):
    """Applique les champs du formulaire ; renvoie le texte des changements."""
    changements = []
    for champ in (c for c in CHAMPS_ARTICLE if c in formulaire._meta.fields or c == "caracteristiques"):
        avant, apres = getattr(proposition, champ), getattr(formulaire.instance, champ)
        if avant != apres:
            changements.append(f"{PropositionArticle._meta.get_field(champ).verbose_name} : {avant or '—'} → {apres or '—'}")
            setattr(proposition, champ, apres)
    if "photo" in formulaire._meta.fields:
        proposition.photo = formulaire.instance.photo
    return "; ".join(changements)


@transaction.atomic
def resoumettre(user, pk, formulaire):
    """Le rédacteur corrige une proposition renvoyée et relance le circuit."""
    proposition = _verrouiller(pk, Etat.REFUSEE)
    if proposition.created_by_id != user.pk:
        raise ErreurCircuit("Seul le rédacteur peut corriger sa proposition.")
    autorise, raison = peut_proposer(user)
    if not autorise:
        raise ErreurCircuit(raison)
    _copier(proposition, formulaire)
    proposition.motif_refus = ""
    proposition.updated_by = user
    proposition.etat = premiere_etape(proposition)
    proposition.save()
    _tracer(proposition, user, Action.RESOUMISE)
    _notifier_etape(proposition)


@transaction.atomic
def viser(user, pk, etat_attendu):
    """Donne le visa de l'étape en cours (hors vérification) et passe à la suivante ; le dernier visa publie."""
    if etat_attendu not in ETAPES_VISA:
        raise ErreurCircuit("Cette étape n'est pas un visa.")
    proposition = _verrouiller(pk, etat_attendu)
    _controler(user, proposition)
    _tracer(proposition, user, Action.VISEE, proposition.etat)
    _avancer(proposition, user)


def _avancer(proposition, user):
    proposition.etat = etape_suivante(proposition)
    proposition.updated_by = user
    if proposition.etat == Etat.PUBLIEE:
        _publier(proposition, user)
    proposition.save()
    if proposition.etat == Etat.PUBLIEE:
        _notifier(proposition, [proposition.created_by],
                  f"Votre proposition « {proposition.designation} » est publiée au catalogue : vous pouvez équiper le bâtiment.")
    else:
        _notifier_etape(proposition)


def _publier(proposition, chef):
    from .catalogue_web import journaliser

    article = ArticleCatalogue.objects.create(
        categorie=proposition.categorie, designation=proposition.designation, marque=proposition.marque,
        reference=proposition.reference, nno=proposition.nno, photo=proposition.photo or None,
        caracteristiques=proposition.caracteristiques, duree_vie_mois=proposition.duree_vie_mois,
        created_by=proposition.created_by, updated_by=chef)
    proposition.article = article
    journaliser(chef, "creation", article)
    _tracer(proposition, chef, Action.PUBLIEE)


@transaction.atomic
def verifier(user, pk, formulaire=None):
    """Le responsable de spécialité corrige éventuellement l'article puis le transmet à son chef."""
    proposition = _verrouiller(pk, Etat.VERIFICATION)
    _controler(user, proposition)
    if formulaire is not None:
        changements = _copier(proposition, formulaire)
        if changements:
            _tracer(proposition, user, Action.CORRIGEE, Etat.VERIFICATION, changements)
    chef = chef_du(user, proposition.categorie.specialite_id)
    if chef is None and not chef_specialite_optionnel():
        raise ErreurCircuit("Aucun chef n'est désigné pour votre responsabilité de spécialité : "
                            "demandez à l'administrateur de le renseigner avant de transmettre.")
    if chef is not None and (chef.pk == proposition.created_by_id or chef.pk in _acteurs(proposition)):
        raise ErreurCircuit("Le chef désigné est déjà intervenu sur cette proposition : elle ne peut pas lui être transmise.")
    proposition.verificateur = user
    _tracer(proposition, user, Action.VERIFIEE, Etat.VERIFICATION,
            "" if chef else "Étape du chef sautée : aucun chef désigné (configuration explicite).")
    if chef is None:
        proposition.etat = Etat.VISA_CHEF_SPECIALITE
    _avancer(proposition, user)


def _acteurs(proposition):
    return set(proposition.evenements.filter(action__in=[Action.VISEE, Action.VERIFIEE]).values_list("user_id", flat=True))


@transaction.atomic
def refuser(user, pk, etat_attendu, motif):
    """Renvoie la proposition au rédacteur ; le motif est obligatoire."""
    motif = sans_nul(motif).strip()
    if not motif:
        raise ErreurCircuit("Le motif du refus est obligatoire.")
    if etat_attendu not in ETAPES:
        raise ErreurCircuit("Cette proposition n'est plus en cours de visa.")
    proposition = _verrouiller(pk, etat_attendu)
    _controler(user, proposition)
    _tracer(proposition, user, Action.REFUSEE, proposition.etat, motif)
    proposition.etat = Etat.REFUSEE
    proposition.motif_refus = motif
    proposition.updated_by = user
    proposition.save()
    _notifier(proposition, [proposition.created_by],
              f"Votre proposition « {proposition.designation} » est renvoyée : {motif}")
