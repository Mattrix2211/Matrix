"""Logique métier des rondes : visibilité par périmètre, création d'une ronde
(instantané des points), enregistrement des réponses avec création d'anomalie
sans doublon, clôture, génération périodique et retards."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog
from logistics.models import Anomalie, AnomalieStatutLog, STATUTS_ANOMALIE_OUVERTS, destinataires_anomalie, niveau_alerte_ticket
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin
from notifications.models import Notification, NotificationLevel

from org.models import Sector, Service, Ship

from .models import Ronde, ResultatPoint, RondeModele, destinataires_ronde

CLE_SEUIL_GESTION = "ronde_gestion"


class RondeImpossible(Exception):
    """Action refusée pour une raison métier (message affichable tel quel)."""


def _position(user):
    """(navire_id, service_id, secteur_id) du profil, remontés depuis le niveau le plus fin."""
    profil = getattr(user, "profile", None)
    if profil is None:
        return None, None, None
    section = profil.section
    sector = profil.sector or (section.sector if section else None)
    service = profil.service or (sector.service if sector else None)
    ship = profil.ship or (service.ship if service else None)
    return (ship.pk if ship else None), (service.pk if service else None), (sector.pk if sector else None)


def perimetre_couvrant_q(user):
    """Q sur un modèle portant ship/service/sector : objets dont le périmètre
    couvre la position du marin (son secteur, son service, son navire), plus,
    selon son rôle, tout ce qui se trouve en dessous (chef de secteur : son
    secteur ; chef de service : son service ; état-major et au-dessus : tout le
    navire). Sans position ni rôle d'administration générale : rien."""
    if is_master_admin(user):
        return Q()
    ship_id, service_id, sector_id = _position(user)
    q = Q(pk__in=[])
    if ship_id:
        q |= Q(ship_id=ship_id, service_id=None)
    if service_id:
        q |= Q(service_id=service_id, sector_id=None)
    if sector_id:
        q |= Q(sector_id=sector_id)
    niveau = user_role_level(user)
    if niveau >= RoleLevel.ETAT_MAJOR and ship_id:
        q |= Q(ship_id=ship_id)
    elif niveau >= RoleLevel.CHEF_SERVICE and service_id:
        q |= Q(service_id=service_id)
    return q


def modeles_visibles(user):
    return RondeModele.objects.filter(perimetre_couvrant_q(user)).select_related("ship", "service", "sector")


def perimetres_gerables(user):
    """Périmètres où `user` peut créer un modèle : [(valeur "type:id", libellé, objet)]."""
    if is_master_admin(user):
        ships, services_qs, sectors = Ship.objects.all(), Service.objects.all(), Sector.objects.all()
    else:
        ship_id, service_id, sector_id = _position(user)
        niveau = user_role_level(user)
        ships = Ship.objects.filter(pk=ship_id) if niveau >= RoleLevel.ETAT_MAJOR else Ship.objects.none()
        if niveau >= RoleLevel.ETAT_MAJOR:
            services_qs = Service.objects.filter(ship_id=ship_id)
            sectors = Sector.objects.filter(service__ship_id=ship_id)
        elif niveau >= RoleLevel.CHEF_SERVICE:
            services_qs = Service.objects.filter(pk=service_id)
            sectors = Sector.objects.filter(service_id=service_id)
        else:
            services_qs = Service.objects.none()
            sectors = Sector.objects.filter(pk=sector_id)
    options = [(f"ship:{s.pk}", f"Unité — {s.name}", s) for s in ships]
    options += [(f"service:{s.pk}", f"Service — {s.name}", s) for s in services_qs.select_related("ship")]
    options += [(f"sector:{s.pk}", f"Secteur — {s.name}", s) for s in sectors.select_related("service__ship")]
    return options


def modeles_gerables(user):
    """Modèles modifiables par `user` : ceux dont le périmètre correspond exactement
    à un périmètre où il peut en créer (même règle, perimetres_gerables)."""
    q = Q(pk__in=[])
    for _, _, obj in perimetres_gerables(user):
        if isinstance(obj, Ship):
            q |= Q(ship=obj, service=None)
        elif isinstance(obj, Service):
            q |= Q(service=obj, sector=None)
        else:
            q |= Q(sector=obj)
    return RondeModele.objects.filter(q)


def rondes_visibles(user):
    return Ronde.objects.filter(perimetre_couvrant_q(user)).select_related("ship", "service", "sector", "modele")


def peut_gerer_modeles(user):
    return user_role_level(user) >= niveau_requis_pour(user, CLE_SEUIL_GESTION)


def rondes_du_marin(user, jusqu_au=None):
    """Rondes ouvertes que le marin peut faire, échues à `jusqu_au` (aujourd'hui
    par défaut) : celles qui lui sont assignées, ou non assignées et visibles."""
    jusqu_au = jusqu_au or timezone.localdate()
    return (
        rondes_visibles(user)
        .filter(statut__in=Ronde.STATUTS_OUVERTS, date_prevue__lte=jusqu_au)
        .filter(Q(assigne_a=user) | Q(assigne_a=None))
    )


def progression(ronde):
    """(nombre de points répondus, total, pourcentage, nombre non conformes)."""
    resultats = list(ronde.resultats.all())
    total = len(resultats)
    repondus = sum(1 for r in resultats if r.resultat)
    non_conformes = sum(1 for r in resultats if r.resultat == ResultatPoint.NON_CONFORME)
    return repondus, total, (round(repondus / total * 100) if total else 0), non_conformes


@transaction.atomic
def creer_ronde(modele, date_prevue=None, assigne_a=None, acteur=None, notifier=False):
    """Crée une ronde à partir du modèle, en copiant ses points (instantané)."""
    points = list(modele.points.select_related("installation", "asset"))
    if not points:
        raise RondeImpossible("Ce modèle n'a aucun point de contrôle : ajoutez-en avant de lancer la ronde.")
    ronde = Ronde.objects.create(
        modele=modele, version_modele=modele.version, nom=modele.nom,
        ship=modele.ship, service=modele.service, sector=modele.sector,
        date_prevue=date_prevue or timezone.localdate(), assigne_a=assigne_a or modele.responsable,
    )
    ResultatPoint.objects.bulk_create([
        ResultatPoint(
            ronde=ronde, ordre=i, libelle=p.libelle, consigne=p.consigne,
            installation=p.installation, asset=p.asset,
            equipement_libelle=str(p.installation.designation if p.installation else (p.asset or "")),
            avec_mesure=p.avec_mesure, unite_mesure=p.unite_mesure, gravite=p.gravite,
        )
        for i, p in enumerate(points, start=1)
    ])
    AuditLog.objects.create(actor=acteur, action="create_ronde", details=f"ronde={ronde.pk}; modele={modele.pk}")
    if notifier:
        _notifier_ronde(ronde, f"Ronde à faire : {ronde.nom} ({ronde.date_prevue:%d/%m/%Y})", NotificationLevel.INFO)
    return ronde


def _notifier_ronde(ronde, verbe, niveau):
    """Marin désigné s'il y en a un, sinon les chefs du périmètre."""
    if ronde.assigne_a_id:
        destinataires = [ronde.assigne_a]
    else:
        destinataires = [p.user for p in destinataires_ronde(ronde)]
    for user in destinataires:
        Notification.objects.create(user=user, verb=verbe, level=niveau)


def ronde_ouverte_du_modele(modele):
    return modele.rondes.filter(statut__in=Ronde.STATUTS_OUVERTS).order_by("date_prevue").first()


def generer_rondes(aujourdhui=None):
    """Crée la ronde du jour de chaque modèle actif dont la périodicité est
    atteinte et qui n'a pas déjà une ronde ouverte. Renvoie le nombre créé."""
    aujourdhui = aujourdhui or timezone.localdate()
    creees = 0
    for modele in RondeModele.objects.filter(actif=True).prefetch_related("points"):
        if not modele.points.exists() or ronde_ouverte_du_modele(modele):
            continue
        derniere = modele.rondes.order_by("-date_prevue").first()
        if derniere and derniere.date_prevue + timedelta(days=modele.periodicite_jours) > aujourdhui:
            continue
        creer_ronde(modele, aujourdhui, notifier=True)
        creees += 1
    return creees


def marquer_rondes_en_retard(aujourdhui=None):
    """Passe en retard les rondes ouvertes dont la date est dépassée et
    prévient une seule fois (le changement de statut évite tout doublon)."""
    aujourdhui = aujourdhui or timezone.localdate()
    en_retard = list(
        Ronde.objects.filter(statut__in=[Ronde.A_FAIRE, Ronde.EN_COURS], date_prevue__lt=aujourdhui)
    )
    for ronde in en_retard:
        ronde.statut = Ronde.EN_RETARD
        ronde.save(update_fields=["statut", "updated_at"])
        _notifier_ronde(ronde, f"Ronde en retard : {ronde.nom} (prévue le {ronde.date_prevue:%d/%m/%Y})", NotificationLevel.WARNING)
    return len(en_retard)


def _anomalie_ouverte_existante(resultat, titre, ronde):
    filtre = Q(statut__in=STATUTS_ANOMALIE_OUVERTS)
    if resultat.installation_id:
        filtre &= Q(installation_id=resultat.installation_id)
    elif resultat.asset_id:
        filtre &= Q(asset_id=resultat.asset_id)
    else:
        filtre &= Q(titre=titre, installation=None, asset=None, sector_id=ronde.sector_id, service_id=ronde.service_id)
    return Anomalie.objects.filter(filtre).order_by("-created_at").first()


def _creer_anomalie(resultat, ronde, user):
    """Anomalie liée au point non conforme, sans doublon : une anomalie encore
    ouverte sur le même équipement (ou même point/lieu) est réutilisée."""
    titre = f"Ronde « {ronde.nom} » : {resultat.libelle}"[:150]
    existante = _anomalie_ouverte_existante(resultat, titre, ronde)
    if existante:
        return existante
    anomalie = Anomalie(
        titre=titre, description=resultat.commentaire, gravite=resultat.gravite,
        installation=resultat.installation, asset=resultat.asset,
        localisation="" if resultat.equipement_lie else resultat.libelle,
        created_by=user, updated_by=user,
    )
    if resultat.equipement_lie:
        anomalie.rattacher_a()
    else:
        anomalie.ship, anomalie.service, anomalie.sector = ronde.ship, ronde.service, ronde.sector
    anomalie.save()
    AnomalieStatutLog.objects.create(
        anomalie=anomalie, ancien_statut="SIGNALEE", nouveau_statut="SIGNALEE", user=user,
        note=f"Créée automatiquement par la ronde « {ronde.nom} » du {ronde.date_prevue:%d/%m/%Y}",
    )
    AuditLog.objects.create(actor=user, action="create_anomalie", details=f"anomalie={anomalie.pk}; ronde={ronde.pk}")
    niveau = niveau_alerte_ticket(anomalie.gravite)
    for profil in destinataires_anomalie(anomalie):
        if profil.user_id != user.id:
            Notification.objects.create(user=profil.user, level=niveau, verb=f"Anomalie signalée : {anomalie.titre}")
    return anomalie


@transaction.atomic
def enregistrer_resultat(resultat, user, valeur, mesure="", commentaire=""):
    """Enregistre la réponse à un point. Renvoie l'anomalie créée/réutilisée
    (ou None). La réponse peut être corrigée tant que la ronde n'est pas terminée."""
    ronde = resultat.ronde
    if not ronde.est_ouverte:
        raise RondeImpossible("Cette ronde est terminée : ses résultats ne peuvent plus être modifiés.")
    if valeur not in dict(ResultatPoint.RESULTATS):
        raise RondeImpossible("Réponse invalide : choisissez Conforme ou Non conforme.")
    mesure_decimale = None
    if resultat.avec_mesure and str(mesure).strip():
        try:
            mesure_decimale = Decimal(str(mesure).strip().replace(",", "."))
        except InvalidOperation:
            raise RondeImpossible("La valeur relevée doit être un nombre.")
    commentaire = commentaire.strip()
    if valeur == ResultatPoint.NON_CONFORME and not commentaire:
        raise RondeImpossible("Indiquez en quelques mots ce qui ne va pas (commentaire obligatoire si non conforme).")
    resultat.resultat, resultat.mesure, resultat.commentaire = valeur, mesure_decimale, commentaire
    resultat.saisi_par, resultat.saisi_le = user, timezone.now()
    anomalie = None
    if valeur == ResultatPoint.NON_CONFORME and not resultat.anomalie_id:
        anomalie = _creer_anomalie(resultat, ronde, user)
        resultat.anomalie = anomalie
    resultat.save()
    if ronde.statut == Ronde.A_FAIRE:
        ronde.statut, ronde.debut = Ronde.EN_COURS, timezone.now()
        ronde.save(update_fields=["statut", "debut", "updated_at"])
    return anomalie


@transaction.atomic
def terminer_ronde(ronde, user):
    if not ronde.est_ouverte:
        raise RondeImpossible("Cette ronde est déjà terminée.")
    restants = ronde.resultats.filter(resultat="").count()
    if restants:
        raise RondeImpossible(f"Il reste {restants} point(s) à renseigner avant de terminer la ronde.")
    ronde.statut, ronde.fin, ronde.realisee_par = Ronde.TERMINEE, timezone.now(), user
    ronde.debut = ronde.debut or ronde.fin
    ronde.save(update_fields=["statut", "fin", "realisee_par", "debut", "updated_at"])
    non_conformes = ronde.resultats.filter(resultat=ResultatPoint.NON_CONFORME).count()
    AuditLog.objects.create(
        actor=user, action="terminer_ronde", details=f"ronde={ronde.pk}; non_conformes={non_conformes}",
    )
    return non_conformes
