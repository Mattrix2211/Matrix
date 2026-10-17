"""Règles métier des annonces : ciblage par périmètre, publication, diffusion, lecture et accusé."""
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.role_thresholds import niveau_pour_action, niveau_requis_pour
from matrix.core.scopes import is_master_admin, navire_q
from notifications.models import Notification, NotificationLevel
from notifications.services import creer_notifications_en_masse, traiter_actions
from org.models import Section, Sector, Service, Ship

from .models import Annonce, LectureAnnonce, ParametresAnnonces, VersionAnnonce

User = get_user_model()
PREFIXE = "Annonce"
PREFIXE_RAPPEL = "Rappel d'accusé"


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def chaine(user):
    """(navire, service, secteur, section) du marin, chacun résolu en remontant la hiérarchie."""
    profil = getattr(user, "profile", None)
    if profil is None:
        return (None,) * 4
    if hasattr(profil, "_chaine"):  # mémorisée sur le profil : une requête par requête HTTP
        return profil._chaine
    p = type(profil).objects.select_related(
        "ship", "service__ship", "sector__service__ship", "section__sector__service__ship").get(pk=profil.pk)
    section = p.section
    sector = p.sector or (section.sector if section else None)
    service = p.service or (sector.service if sector else None)
    ship = p.ship or (service.ship if service else None)
    profil._chaine = tuple(getattr(x, "pk", None) for x in (ship, service, sector, section))
    return profil._chaine


def _noeuds(ship_ids, service_id=None, sector_id=None, section_id=None, libelles=True):
    """Nœuds ciblables sous un niveau de périmètre : [(clé, libellé)] ; sans libellés, une requête d'identifiants par niveau."""
    def liste(cle, prefixe, qs):
        if not libelles:
            return [(f"{cle}:{pk}", "") for pk in qs.values_list("pk", flat=True)]
        return [(f"{cle}:{n.pk}", f"{prefixe}{n}") for n in qs]

    if section_id:
        return liste("section", "Section ", Section.objects.filter(pk=section_id))
    if sector_id:
        secteurs = Sector.objects.filter(pk=sector_id)
        sections = Section.objects.filter(sector_id=sector_id)
        services = Service.objects.none()
    elif service_id:
        services = Service.objects.filter(pk=service_id)
        secteurs = Sector.objects.filter(service_id=service_id)
        sections = Section.objects.filter(sector__service_id=service_id)
    else:
        services = Service.objects.filter(ship_id__in=ship_ids)
        secteurs = Sector.objects.filter(service__ship_id__in=ship_ids)
        sections = Section.objects.filter(sector__service__ship_id__in=ship_ids)
    noeuds = liste("ship", "Tout le bâtiment ", Ship.objects.filter(pk__in=ship_ids)) if not (sector_id or service_id) else []
    noeuds += liste("service", "Service ", services)
    noeuds += liste("sector", "Secteur ", secteurs)
    noeuds += liste("section", "Section ", sections)
    return noeuds


def cibles_autorisees(user, libelles=True):
    """Cibles que `user` peut viser : son niveau de périmètre et tout ce qui en dépend."""
    if is_master_admin(user):
        ship_id = getattr(getattr(user, "profile", None), "ship_id", None)
        return _noeuds([ship_id] if ship_id else list(Ship.objects.values_list("pk", flat=True)), libelles=libelles)
    niveau, ident = user.profile.scope if getattr(user, "profile", None) else (None, None)
    ship_id = user.profile.ship_id if niveau else None
    if niveau == "ship":
        return _noeuds([ident], libelles=libelles)
    if niveau == "service":
        return _noeuds([ship_id], service_id=ident, libelles=libelles)
    if niveau == "sector":
        return _noeuds([ship_id], sector_id=ident, libelles=libelles)
    if niveau == "section":
        return _noeuds([ship_id], section_id=ident, libelles=libelles)
    return []


def peut_publier(user):
    if equipage_a_terre_lecture_seule(user) or niveau_pour_action(user, "annonce_publication") < niveau_requis_pour(user, "annonce_publication"):
        return False
    return bool(cibles_autorisees(user))


def equipages_du_navire(user):
    """Équipages réels du bâtiment du marin : ceux de ses marins et celui à bord."""
    navire = getattr(getattr(user, "profile", None), "ship", None)
    if navire is None:
        return []
    codes = set(User.objects.filter(profile__ship=navire).exclude(profile__equipage="").values_list("profile__equipage", flat=True))
    if navire.equipage_a_bord:
        codes.add(navire.equipage_a_bord)
    return sorted(codes)


def resoudre_cible(cible):
    """Annonce(ship, service, sector, section) pour une clé « type:identifiant »."""
    modele, _, pk = (cible or "").partition(":")
    classe = {"ship": Ship, "service": Service, "sector": Sector, "section": Section}.get(modele)
    noeud = classe.objects.filter(pk=pk).first() if classe and pk.isdigit() else None
    if noeud is None:
        raise ValidationError("Choisissez le public visé.")
    champs = {"ship": None, "service": None, "sector": None, "section": None}
    if modele == "section":
        champs["section"] = noeud
        champs["sector"] = noeud.sector
        champs["service"] = noeud.sector.service
        champs["ship"] = noeud.sector.service.ship
    elif modele == "sector":
        champs.update(sector=noeud, service=noeud.service, ship=noeud.service.ship)
    elif modele == "service":
        champs.update(service=noeud, ship=noeud.ship)
    else:
        champs["ship"] = noeud
    return champs


def cible_permise(user, cible):
    return any(cle == cible for cle, _ in cibles_autorisees(user))


def filtre_public(annonce):
    """Q (sur User) des marins visés par l'annonce."""
    if annonce.section_id:
        public = Q(profile__section_id=annonce.section_id)
    elif annonce.sector_id:
        public = Q(profile__sector_id=annonce.sector_id) | Q(profile__section__sector_id=annonce.sector_id)
    elif annonce.service_id:
        public = (Q(profile__service_id=annonce.service_id) | Q(profile__sector__service_id=annonce.service_id)
                  | Q(profile__section__sector__service_id=annonce.service_id))
    else:
        public = navire_q(annonce.ship_id, "profile__")
    if annonce.equipage:
        public &= Q(profile__equipage=annonce.equipage)
    return public


def destinataires(annonce):
    return User.objects.filter(filtre_public(annonce), is_active=True).distinct()


def _concerne(user, annonce):
    return destinataires(annonce).filter(pk=user.pk).exists()


def filtre_ciblage(user):
    """Q (sur un modèle ciblé : ship, service, sector, section, equipage) des objets qui visent `user`."""
    ship, service, sector, section = chaine(user)
    profil = getattr(user, "profile", None)
    visees = Q(ship_id=ship) & (Q(service__isnull=True) | Q(service_id=service)) \
        & (Q(sector__isnull=True) | Q(sector_id=sector)) & (Q(section__isnull=True) | Q(section_id=section))
    visees &= Q(equipage="") | Q(equipage=getattr(profil, "equipage", "") or "\0")
    return visees if ship else Q(pk__in=[])


def _filtre_visibles(user):
    """Q (sur Annonce) : annonces qui visent `user`, ou qu'il a publiées."""
    visees = filtre_ciblage(user) & Q(date_effet__lte=timezone.localdate())  # avant sa date d'effet, seuls l'auteur et les gérants la voient
    return visees | Q(auteur=user)


def annonces_visibles(user):
    return Annonce.objects.filter(_filtre_visibles(user)).distinct()


def filtre_gestion(user):
    """Q (sur un modèle ciblé) des objets rattachés aux nœuds que `user` peut viser, dans son bâtiment."""
    cles = [cle for cle, _ in cibles_autorisees(user, libelles=False)]
    filtre = Q(pk__in=[])
    ship = chaine(user)[0]
    for modele in ("ship", "service", "sector", "section"):
        ids = [int(c.split(":")[1]) for c in cles if c.startswith(f"{modele}:")]
        if ids:
            filtre |= Q(**{f"{modele}_id__in": ids}) & (Q(ship_id=ship) if modele != "ship" else Q())
    return filtre


def annonces_gerees(user):
    """Annonces dont `user` suit la lecture : celles qu'il a publiées et celles de son périmètre de publication."""
    if not peut_publier(user):
        return Annonce.objects.none()
    return Annonce.objects.filter(Q(auteur=user) | filtre_gestion(user)).distinct()


def peut_consulter(user, annonce):
    return annonces_visibles(user).filter(pk=annonce.pk).exists() or annonces_gerees(user).filter(pk=annonce.pk).exists()


def peut_gerer(user, annonce):
    return annonces_gerees(user).filter(pk=annonce.pk).exists()


def _tracer(annonce, acteur, action):
    AuditLog.objects.create(actor=acteur, action=f"annonce_{action}", details=f"annonce={annonce.pk}; version={annonce.version}")


def _valider(titre, corps, niveau, date_effet, date_fin):
    if not titre.strip() or not corps.strip():
        raise ValidationError("Le titre et le message sont obligatoires.")
    if niveau not in NotificationLevel.values:
        raise ValidationError("Niveau inconnu.")
    if date_fin and date_fin < date_effet:
        raise ValidationError("La date de fin précède la date d'effet.")


def publier(auteur, titre, corps, niveau, cible, equipage="", accuse_requis=False, date_effet=None, date_fin=None):
    if not peut_publier(auteur):
        raise PermissionError("Vous ne pouvez pas publier d'annonce.")
    if not cible_permise(auteur, cible):
        raise PermissionError("Ce public est hors de votre périmètre.")
    date_effet = date_effet or timezone.localdate()
    _valider(titre, corps, niveau, date_effet, date_fin)
    if equipage.strip() and equipage.strip() not in equipages_du_navire(auteur):
        raise ValidationError("Cet équipage n'existe pas sur votre bâtiment.")
    annonce = Annonce(
        titre=titre.strip(), corps=corps.strip(), niveau=niveau, accuse_requis=accuse_requis, date_effet=date_effet,
        date_fin=date_fin, equipage=equipage.strip(), auteur=auteur, created_by=auteur, updated_by=auteur,
        **resoudre_cible(cible),
    )
    annonce.save()
    VersionAnnonce.objects.create(annonce=annonce, numero=1, titre=annonce.titre, corps=annonce.corps, niveau=niveau, auteur=auteur)
    _tracer(annonce, auteur, "publiee")
    if date_effet <= timezone.localdate():
        diffuser(annonce)
    return annonce


def modifier(user, annonce, titre, corps, niveau, date_fin=None):
    """Nouvelle version conservée ; le public déjà informé est prévenu et les accusés sont à renouveler."""
    if not peut_gerer(user, annonce) or annonce.archivee:
        raise PermissionError("Vous ne pouvez pas modifier cette annonce.")
    _valider(titre, corps, niveau, annonce.date_effet, date_fin)
    annonce.titre, annonce.corps, annonce.niveau, annonce.date_fin = titre.strip(), corps.strip(), niveau, date_fin
    annonce.version += 1
    annonce.updated_by = user
    annonce.save()
    VersionAnnonce.objects.create(annonce=annonce, numero=annonce.version, titre=annonce.titre, corps=annonce.corps, niveau=niveau, auteur=user)
    _tracer(annonce, user, "modifiee")
    if annonce.diffusee_le:
        traiter_actions(annonce)
        _notifier(annonce, f"{PREFIXE} mise à jour (v{annonce.version}) : {annonce.titre}")
    return annonce


def archiver(user, annonce):
    if not peut_gerer(user, annonce):
        raise PermissionError("Vous ne pouvez pas archiver cette annonce.")
    annonce.archivee, annonce.updated_by = True, user
    annonce.save(update_fields=["archivee", "updated_by", "updated_at"])
    traiter_actions(annonce)
    _tracer(annonce, user, "archivee")


def _notifier(annonce, verb):
    creer_notifications_en_masse(
        Notification(user=u, verb=verb, level=annonce.niveau, target=annonce, action_requise=annonce.accuse_requis)
        for u in destinataires(annonce).exclude(pk=annonce.auteur_id)
    )


def diffuser(annonce):
    """Notifie le public visé, une seule fois, à la date d'effet."""
    if annonce.diffusee_le:
        return
    _notifier(annonce, f"{PREFIXE} : {annonce.titre}")
    annonce.diffusee_le = timezone.now()
    annonce.save(update_fields=["diffusee_le"])


def diffuser_du_jour():
    """Diffuse les annonces dont la date d'effet est arrivée (tâche quotidienne)."""
    a_diffuser = Annonce.objects.filter(diffusee_le__isnull=True, archivee=False, date_effet__lte=timezone.localdate())
    for annonce in a_diffuser:
        diffuser(annonce)
    return a_diffuser.count()


def rappeler_accuses(aujourdhui=None):
    """Rappelle une seule fois chaque destinataire n'ayant pas accusé une annonce en cours, N jours après sa diffusion.

    Le rappel mémorisé est la notification elle-même : la tâche quotidienne reste idempotente."""
    delai = ParametresAnnonces.courants().jours_rappel_accuse
    if not delai:
        return 0
    aujourdhui = aujourdhui or timezone.localdate()
    seuil = timezone.make_aware(datetime.combine(aujourdhui - timedelta(days=delai), time.max))
    creees = 0
    for annonce in Annonce.objects.filter(
        accuse_requis=True, archivee=False, date_effet__lte=aujourdhui, diffusee_le__lte=seuil,
    ).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=aujourdhui)):
        accuses = set(annonce.lectures.filter(accuse=True, version_lue__gte=annonce.version).values_list("user_id", flat=True))
        deja = set(Notification.objects.filter(
            content_type=ContentType.objects.get_for_model(annonce), object_id=str(annonce.pk),
            verb__startswith=PREFIXE_RAPPEL).values_list("user_id", flat=True))
        a_relancer = destinataires(annonce).exclude(pk=annonce.auteur_id).exclude(pk__in=accuses | deja)
        creees += len(creer_notifications_en_masse(
            Notification(user=u, verb=f"{PREFIXE_RAPPEL} : {annonce.titre}", level=NotificationLevel.WARNING,
                         target=annonce, action_requise=True)
            for u in a_relancer
        ))
    return creees


def lecture_de(user, annonce):
    return LectureAnnonce.objects.filter(annonce=annonce, user=user).first()


def marquer_lue(user, annonce):
    """Ouvrir l'annonce suffit quand aucun accusé n'est requis."""
    lecture, _ = LectureAnnonce.objects.get_or_create(annonce=annonce, user=user, defaults={"version_lue": annonce.version})
    if lecture.version_lue < annonce.version:
        lecture.version_lue = annonce.version
        lecture.save(update_fields=["version_lue", "updated_at"])


def accuser(user, annonce):
    if not _concerne(user, annonce):
        raise PermissionError("Cette annonce ne vous est pas destinée.")
    if not annonce.accuse_requis:
        raise ValidationError("Aucun accusé n'est demandé pour cette annonce.")
    if not annonce.active_au(timezone.localdate()):
        raise ValidationError("Cette annonce n'est pas en cours.")
    LectureAnnonce.objects.update_or_create(
        annonce=annonce, user=user, defaults={"accuse": True, "version_lue": annonce.version},
    )
    traiter_actions(annonce, [user])


def a_lire(user, jour):
    """Annonces actives qui visent `user` et restent à lire (ou à accuser pour la version courante)."""
    lues = {l.annonce_id: l for l in LectureAnnonce.objects.filter(user=user)}
    retenues = []
    for annonce in annonces_visibles(user).exclude(auteur=user).filter(archivee=False, date_effet__lte=jour).filter(
            Q(date_fin__isnull=True) | Q(date_fin__gte=jour)).select_related("ship"):
        lecture = lues.get(annonce.pk)
        if annonce.accuse_requis:
            if lecture is None or not lecture.accuse or lecture.version_lue < annonce.version:
                retenues.append(annonce)
        elif lecture is None or lecture.version_lue < annonce.version:
            retenues.append(annonce)
    return retenues


def suivi_lecture(annonce):
    """Qui a lu, accusé ou n'a rien fait, pour le publiant."""
    lectures = {l.user_id: l for l in annonce.lectures.all()}
    lignes = []
    for user in destinataires(annonce).exclude(pk=annonce.auteur_id).order_by("username"):
        lecture = lectures.get(user.pk)
        etat = "Non lu"
        if lecture and lecture.version_lue >= annonce.version:
            etat = "Accusé" if lecture.accuse else "Lu"
        lignes.append({"user": user, "etat": etat})
    return lignes
