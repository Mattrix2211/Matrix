"""Quarts et services de garde/quai (Phase 2 — Vie quotidienne, cf. cahier des charges
Notion §8/§9 et tâche Notion « Quarts/services »).

Décision de cadrage confirmée le 09/09/2026 (corrige un cadrage antérieur du
06/09) : Quart (rotation de postes, créneaux courts répétés, ex. 4h) et
ServiceGarde (affectation longue, ex. garde 24h) sont DEUX MODÈLES DJANGO
DISTINCTS, chacun avec sa propre table — PAS un modèle générique unique avec
un champ « type ». Ce qui est réellement commun aux deux (désignation du chef
de liste, statut brouillon/publiée, affectation marin/créneau) est factorisé
via les classes abstraites ci-dessous (ListeServiceAbstract, CreneauAbstract),
partagées par les deux modèles concrets sans dupliquer le code.

Aucune durée n'est codée en dur (CLAUDE.md §6) : `duree_creneau_heures` sur
chaque modèle concret n'est qu'une VALEUR PAR DÉFAUT éditable, pré-remplissant
le formulaire d'ajout d'un créneau pour aller plus vite qu'un tableur Excel —
elle ne conditionne aucune règle de code figée. Un service de garde porte en
plus `type_service`, texte libre (garde 24h, garde de nuit, permanence...),
même principe que AssetType.category (assets/models.py) : la nomenclature des
types de garde n'est pas une liste fermée à décider à la place de la Marine.

Le rôle de « chef de liste » (ChefDeListe) est un rôle ANNEXE, indépendant du
rang hiérarchique (RoleLevel) — même pattern que ReferentFormation
(training/models.py) : une désignation explicite par utilisateur + périmètre
(navire/service/secteur/section), pas un seuil de rôle générique. Un chef de
liste ne gère (créer/modifier/publier) que les listes dont le périmètre
correspond EXACTEMENT à celui pour lequel il est désigné (pas de cascade
hiérarchique implicite vers les sous-niveaux : décision produit volontairement
simple, cf. tâche Notion « Quarts/services », point (b) du cadrage) — hormis
la supervision globale (COMMANDANT et au-dessus), qui passe outre comme
partout ailleurs dans le projet (cf. peut_valider_formation, training/models.py).

Correction majeure de cadrage du 09/09/2026 (l'utilisateur — ancien chef de
secteur — a signalé après coup une dimension métier manquante et essentielle) :
les listes de quarts/gardes doivent être organisables par FONCTION, transversale
aux secteurs/services, pas seulement par périmètre organisationnel. Concrètement
: `Quart.fonction` (nouveau référentiel configurable `FonctionQuartChoice`,
même pattern que `ServiceFunctionChoice` déjà existant dans accounts/models.py
pour le profil marin) et `ServiceGarde.fonction` (réutilise directement
`ServiceFunctionChoice`, qui existait déjà mais n'était jamais utilisé en
relation — seulement comme source d'un champ texte libre sur le profil marin)
sont désormais des champs OBLIGATOIRES de chaque liste (nullables en base par
cohérence avec ship/service/sector/section ci-dessous — la contrainte
"obligatoire" est portée par la validation du formulaire, pas par le schéma,
pour rester rétrocompatible avec le principe déjà appliqué au périmètre
organisationnel).

Choix d'implémentation retenu pour la portée de la liste (à documenter comme
hypothèse, remonté dans le compte-rendu de la tâche plutôt que tranché sans
recul) : le périmètre organisationnel (ship/service/sector/section, toujours
EXACTEMENT un des quatre, cf. _valider_perimetre_unique) reste inchangé — y
compris le choix déjà existant « Navire seul » (aucun changement de schéma ni
de règle de désignation ChefDeListe/seuils). Ce qui change réellement : une
liste choisissant le périmètre « Navire » est maintenant ORGANISÉE PAR
FONCTION (champ obligatoire), ce qui permet enfin de constituer une liste
transversale à tous les secteurs/services du navire pour une fonction donnée
(ex. « Barre — navire entier ») — cas qui existait déjà techniquement (choix
« Navire » du périmètre) mais n'avait jusqu'ici aucune façon de distinguer les
fonctions entre elles, ni n'était réellement exploitable puisque seule la
supervision globale (COMMANDANT+) peut être désignée chef de liste au niveau
Navire (cf. `_perimetre_autorise_pour_designation`, inchangé). Le seuil de
désignation (CHEF_SERVICE+ borné à son propre périmètre, COMMANDANT+ libre)
n'a donc pas été modifié : il reste cohérent tel quel, un CHEF_SERVICE ne
devant de toute façon pas pouvoir constituer une liste dépassant son propre
service même au nom d'une fonction transversale — seule une autorité de niveau
navire (COMMANDANT+) a la légitimité de faire cohabiter des marins de
secteurs/services différents sur une même liste.

Ajout du 22/09/2026 (tâche Notion « Versionnage des listes de service et
workflow brouillon → proposition → validation → publication », cahier des
charges §31 « configuration versionnée » et §34 « workflow proposer → valider
→ publier ») : deux volets, tous deux concentrés sur Quart/ServiceGarde (pas
de système de version générique réutilisable ailleurs, cf. cadrage de la
tâche) :

1. VERSIONNAGE — chaque publication (première publication, republication
   après correction, ou permutation par un échange de service validé, cf.
   quarts/echanges.py::valider_echange) fige un INSTANTANÉ horodaté des
   créneaux dans VersionQuart/VersionServiceGarde (créneaux_fige, JSON) sans
   jamais réécrire ni supprimer les versions précédentes — inspiré du
   versionnage par instantané déjà utilisé par les rondes (rondes.models.
   RondeModele.version + ResultatPoint qui copie les points du modèle),
   adapté ici en snapshot COMPLET des créneaux (pas un simple compteur
   entier) car l'exemple du cahier des charges (§31 : v1/v2/v3) exige de
   pouvoir consulter la liste ACTIVE à une date donnée, pas seulement
   détecter qu'un changement a eu lieu. `ListeServiceAbstract.
   version_a_la_date` répond à ce besoin.

2. WORKFLOW — un statut intermédiaire STATUT_PROPOSEE s'intercale entre
   Brouillon et Publiée. Proposer (BROUILLON -> PROPOSEE) reste réservé au
   chef de liste actuel (peut_gerer_liste, inchangé). Publier (PROPOSEE ->
   PUBLIEE) exige désormais un rôle DISTINCT (peut_gerer_liste seul ne
   suffit plus) : seuil configurable par navire (matrix/core/role_thresholds.
   py, action "liste_service_publication", défaut CHEF_SERVICE) ET périmètre
   organisationnel personnel couvrant celui de la liste (même construction
   que _perimetre_autorise_pour_designation, web_views.py) — ou supervision
   globale (COMMANDANT+), qui passe toujours outre. Un chef de liste qui
   n'a que le droit de proposer (ex. rôle EQUIPIER désigné ChefDeListe) ne
   peut donc pas publier lui-même. Par souci de ne pas complexifier une
   simple correction mineure (CLAUDE.md §2), la republication d'une liste
   DÉJÀ publiée reste possible directement (sans repasser par "proposer") —
   seule la toute première publication doit obligatoirement transiter par
   l'étape Proposée.

Hypothèses de cadrage documentées dans le compte-rendu [Dev] de la tâche
(non tranchées seules, à confirmer par le métier) : qui exactement doit
recevoir la notification de proposition (périmètre organisationnel EXACT de
la liste uniquement, sans cascade vers les niveaux ancêtres, cf.
publicateurs_a_notifier) ; et l'historique des versions n'est consultable
que par qui gère ou peut publier la liste (pas ouvert à tout marin lecteur
d'une liste publiée).
"""
from datetime import datetime, time as heure_du_jour

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog, FonctionQuartChoice, ServiceFunctionChoice
from matrix.core.models import OwnedModel, TimeStampedModel
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user, ship_id_for_user
from notifications.models import Notification, NotificationLevel
from org.models import Sector, Section, Service, Ship

User = get_user_model()


# Seuil à partir duquel un utilisateur passe outre toute désignation de chef
# de liste (supervision globale) : même niveau que
# training.models.NIVEAU_SUPERVISION_GLOBALE_FORMATION, pour rester cohérent
# avec les autres rôles annexes du projet.
NIVEAU_SUPERVISION_GLOBALE_LISTE = RoleLevel.COMMANDANT

# Seuil générique requis pour accéder à l'écran de désignation d'un chef de
# liste : CHEF_SERVICE et au-dessus, comme d'autres désignations de
# responsabilité déjà existantes dans le projet (ex. validation d'une
# formation « gérée par le bord », training.web_views.NIVEAU_REQUIS_VALIDATION_
# FORMATION_BORD). Le périmètre réellement autorisé (uniquement le sien,
# sauf supervision globale) est contrôlé séparément côté vue
# (quarts/web_views.py::_perimetre_autorise_pour_designation), même principe
# que logistics/web_views.py::_secteur_dans_perimetre.
NIVEAU_REQUIS_DESIGNATION_CHEF_DE_LISTE = RoleLevel.CHEF_SERVICE


def _valider_perimetre_unique(ship_id, service_id, sector_id, section_id, label):
    """Vérifie qu'exactement un des quatre niveaux de périmètre organisationnel
    est renseigné — règle commune à ChefDeListe et ListeServiceAbstract,
    centralisée ici pour ne pas la dupliquer dans les deux classes."""
    renseignes = [n for n in (ship_id, service_id, sector_id, section_id) if n]
    if len(renseignes) != 1:
        raise ValidationError(
            f"{label} doit être rattaché à exactement un périmètre "
            "(unité, service, secteur ou section)."
        )


class ChefDeListe(TimeStampedModel):
    """Désignation explicite d'un marin comme chef de liste pour un périmètre
    précis — rôle annexe indépendant du rang hiérarchique (cf. docstring de
    module). Un même marin peut cumuler plusieurs désignations sur des
    périmètres différents (ex. chef de liste de son secteur ET d'une section
    d'un autre secteur)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="designations_chef_de_liste")
    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.CASCADE, related_name="chefs_de_liste")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name="chefs_de_liste")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.CASCADE, related_name="chefs_de_liste")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.CASCADE, related_name="chefs_de_liste")

    class Meta:
        verbose_name = "Chef de liste"
        verbose_name_plural = "Chefs de liste"
        unique_together = ("user", "ship", "service", "sector", "section")

    def clean(self):
        super().clean()
        _valider_perimetre_unique(self.ship_id, self.service_id, self.sector_id, self.section_id, "Un chef de liste")

    @property
    def perimetre(self):
        return self.ship or self.service or self.sector or self.section

    def __str__(self):
        return f"{self.user} — chef de liste ({self.perimetre})"


def perimetre_correspond(a, b):
    """Vrai si deux objets porteurs d'un périmètre organisationnel (ChefDeListe,
    Quart ou ServiceGarde) désignent EXACTEMENT le même périmètre (même
    niveau, même objet) — pas de correspondance « englobante » (cf. docstring
    de module : décision produit volontairement simple)."""
    return (
        a.ship_id == b.ship_id
        and a.service_id == b.service_id
        and a.sector_id == b.sector_id
        and a.section_id == b.section_id
    )


def utilisateur_autorise_pour_perimetre(user, ship=None, service=None, sector=None, section=None):
    """Vrai si `user` peut créer/modifier/publier une liste (Quart ou
    ServiceGarde) pour le périmètre donné (exactement un des quatre non
    nul) : désigné chef de liste pour EXACTEMENT ce périmètre (ChefDeListe),
    ou supervision globale (COMMANDANT et au-dessus)."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_LISTE:
        return True
    cible = (
        ship.pk if ship else None,
        service.pk if service else None,
        sector.pk if sector else None,
        section.pk if section else None,
    )
    return any(
        (cdl.ship_id, cdl.service_id, cdl.sector_id, cdl.section_id) == cible
        for cdl in ChefDeListe.objects.filter(user=user)
    )


def peut_gerer_liste(user, liste):
    """Vrai si `user` peut gérer CETTE liste précise déjà existante (Quart ou
    ServiceGarde) : modifier ses créneaux et la proposer à la publication —
    cf. utilisateur_autorise_pour_perimetre. Ne couvre PLUS le droit de
    publier depuis le 22/09/2026 (workflow proposer -> valider/publier,
    cf. peut_publier_liste ci-dessous, qui exige un rôle distinct)."""
    return utilisateur_autorise_pour_perimetre(user, liste.ship, liste.service, liste.sector, liste.section)


def _perimetre_dans_scope_utilisateur(user, ship, service, sector, section, niveau_requis):
    """Vrai si `user` atteint `niveau_requis` ET si son propre périmètre
    organisationnel personnel (scope_filters_for_user) couvre EXACTEMENT le
    périmètre donné (ship/service/sector/section) — brique commune à la
    désignation d'un chef de liste (web_views.py::
    _perimetre_autorise_pour_designation) et à la publication d'une liste
    (peut_publier_liste ci-dessous), pour ne jamais faire diverger ces deux
    contrôles de seuil + périmètre."""
    if user_role_level(user) < niveau_requis:
        return False
    filtres = scope_filters_for_user(user)
    if not filtres:
        return True
    (cle, valeur), = filtres.items()
    valeur = str(valeur)
    if cle == "section_id":
        return section is not None and str(section.pk) == valeur
    if cle == "sector_id":
        if sector is not None:
            return str(sector.pk) == valeur
        if section is not None:
            return str(section.sector_id) == valeur
        return False
    if cle == "service_id":
        if service is not None:
            return str(service.pk) == valeur
        if sector is not None:
            return str(sector.service_id) == valeur
        if section is not None:
            return str(section.sector.service_id) == valeur
        return False
    if cle == "ship_id":
        if ship is not None:
            return str(ship.pk) == valeur
        if service is not None:
            return str(service.ship_id) == valeur
        if sector is not None:
            return str(sector.service.ship_id) == valeur
        if section is not None:
            return str(section.sector.service.ship_id) == valeur
        return False
    return False


def peut_publier_liste(user, liste):
    """Vrai si `user` peut publier (valider) CETTE liste précise — rôle
    DISTINCT de celui qui peut la gérer/proposer (cf. peut_gerer_liste),
    cahier des charges §34 : « un utilisateur peut avoir le droit de
    proposer une modification sans avoir le droit de la publier ». Seuil
    configurable par navire (matrix/core/role_thresholds.py, action
    "liste_service_publication") : supervision globale (COMMANDANT et
    au-dessus) toujours autorisée, sinon rôle atteignant le seuil ET
    périmètre organisationnel personnel couvrant celui de la liste (aucune
    cascade implicite, même principe que peut_gerer_liste)."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_LISTE:
        return True
    seuil = niveau_requis_pour(user, "liste_service_publication")
    return _perimetre_dans_scope_utilisateur(user, liste.ship, liste.service, liste.sector, liste.section, seuil)


def publicateurs_a_notifier(liste):
    """Marins habilités à publier CETTE liste (cf. peut_publier_liste),
    notifiés quand elle passe au statut Proposée. Repli sur le créateur de la
    liste si personne n'est identifié — même filet de sécurité que
    quarts.echanges.chefs_de_liste_a_notifier, pour qu'une proposition ne
    reste jamais sans destinataire."""
    destinataires = [
        u for u in User.objects.filter(is_active=True).select_related("profile")
        if peut_publier_liste(u, liste)
    ]
    if not destinataires and liste.created_by_id:
        destinataires = [liste.created_by]
    return destinataires


def marins_du_perimetre(liste):
    """Marins affectables sur un créneau de `liste` (Quart ou ServiceGarde) :
    tout le périmètre visé et tout ce qui en descend (ex. une liste au niveau
    secteur couvre n'importe quel marin d'une section de ce secteur) — à ne
    pas confondre avec la règle de gestion de la liste elle-même
    (peut_gerer_liste), qui ne tolère aucune cascade. Utilisé à la fois pour
    l'affectation d'un créneau (quarts/web_views.py) et pour le compteur
    d'équité par marin (quarts/services.py), qui doit couvrir exactement les
    mêmes marins que ceux affectables sur la liste."""
    if liste.section_id:
        return Q(profile__section_id=liste.section_id)
    if liste.sector_id:
        return Q(profile__sector_id=liste.sector_id) | Q(profile__section__sector_id=liste.sector_id)
    if liste.service_id:
        return (
            Q(profile__service_id=liste.service_id)
            | Q(profile__sector__service_id=liste.service_id)
            | Q(profile__section__sector__service_id=liste.service_id)
        )
    if liste.ship_id:
        return (
            Q(profile__ship_id=liste.ship_id)
            | Q(profile__service__ship_id=liste.ship_id)
            | Q(profile__sector__service__ship_id=liste.ship_id)
            | Q(profile__section__sector__service__ship_id=liste.ship_id)
        )
    return Q(pk__in=[])


class ListeServiceAbstract(TimeStampedModel, OwnedModel):
    """Socle commun à Quart et ServiceGarde : période couverte, périmètre
    organisationnel, statut de publication et affectations des marins sur les
    créneaux — factorisé ici pour ne pas dupliquer cette mécanique entre les
    deux modèles concrets (cf. docstring de module, correction de cadrage du
    09/09/2026)."""

    STATUT_BROUILLON = "BROUILLON"
    STATUT_PROPOSEE = "PROPOSEE"
    STATUT_PUBLIEE = "PUBLIEE"
    STATUT_CHOICES = (
        (STATUT_BROUILLON, "Brouillon"),
        (STATUT_PROPOSEE, "Proposée"),
        (STATUT_PUBLIEE, "Publiée"),
    )

    # Étiquette libre optionnelle (ex. « Semaine du 08/09 ») : purement
    # d'affichage, aucune règle ne repose dessus.
    nom = models.CharField(max_length=255, blank=True, default="")
    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.CASCADE, related_name="%(class)ss")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE, related_name="%(class)ss")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.CASCADE, related_name="%(class)ss")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.CASCADE, related_name="%(class)ss")
    date_debut = models.DateField(verbose_name="Début de période")
    date_fin = models.DateField(verbose_name="Fin de période")
    statut = models.CharField(max_length=16, choices=STATUT_CHOICES, default=STATUT_BROUILLON)
    proposee_le = models.DateTimeField(null=True, blank=True, verbose_name="Proposée le")
    proposee_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="%(class)ss_proposees", verbose_name="Proposée par",
    )
    publiee_le = models.DateTimeField(null=True, blank=True, verbose_name="Publiée le")
    publiee_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="%(class)ss_publiees", verbose_name="Publiée par",
    )

    class Meta:
        abstract = True
        ordering = ("-date_debut",)

    def clean(self):
        super().clean()
        _valider_perimetre_unique(self.ship_id, self.service_id, self.sector_id, self.section_id, str(self._meta.verbose_name).capitalize())
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({"date_fin": "La date de fin ne peut pas précéder la date de début."})

    @property
    def perimetre(self):
        return self.ship or self.service or self.sector or self.section

    def libelle_type(self):
        """Nom métier affiché dans les notifications de publication — surchargé
        par chaque modèle concret (« quart » / « service de garde »)."""
        raise NotImplementedError

    def proposer(self, user):
        """Passe la liste de Brouillon à Proposée (workflow proposer ->
        valider/publier, cahier des charges §34) et notifie les
        publicateurs habilités (cf. peut_publier_liste) qu'une validation
        est attendue. Ne modifie jamais le statut d'une liste qui n'est pas
        en brouillon (contrôlé côté vue, quarts/web_views.py::_proposer)."""
        self.statut = self.STATUT_PROPOSEE
        self.proposee_le = timezone.now()
        self.proposee_par = user
        self.save(update_fields=["statut", "proposee_le", "proposee_par", "updated_at"])
        AuditLog.objects.create(
            actor=user, action="liste_service_proposee",
            details=f"{self.libelle_type()} #{self.pk} ({self.perimetre}) proposé(e) à la publication.",
        )
        for destinataire in publicateurs_a_notifier(self):
            Notification.objects.create(
                user=destinataire,
                verb=(
                    f"Proposition à valider : le {self.libelle_type()} "
                    f"« {self.nom or self.perimetre} » attend votre publication."
                ),
                level=NotificationLevel.WARNING,
            )

    def publier(self, user):
        """Passe la liste au statut Publiée, fige une nouvelle version
        horodatée (cf. creer_version) et notifie chaque marin affecté sur un
        créneau. Republier une liste déjà publiée (après une correction) ne
        renvoie pas de nouvelles notifications aux marins : seule la toute
        première publication les alerte — mais une nouvelle version est bien
        créée à chaque appel (cf. cahier des charges §31, docstring de
        module)."""
        deja_publiee = self.statut == self.STATUT_PUBLIEE
        self.statut = self.STATUT_PUBLIEE
        self.publiee_le = timezone.now()
        self.publiee_par = user
        self.save(update_fields=["statut", "publiee_le", "publiee_par", "updated_at"])
        version = self.creer_version(user)
        AuditLog.objects.create(
            actor=user, action="liste_service_publiee",
            details=f"{self.libelle_type()} #{self.pk} ({self.perimetre}) publié(e), version {version.numero}.",
        )
        if deja_publiee:
            return
        for creneau in self.creneaux.select_related("marin").all():
            if creneau.marin_id:
                Notification.objects.create(
                    user=creneau.marin,
                    verb=(
                        f"Liste publiée : vous êtes affecté(e) au {self.libelle_type()} "
                        f"« {creneau.poste} » le {timezone.localtime(creneau.debut):%d/%m/%Y à %H:%M}."
                    ),
                )

    def creer_version(self, user):
        """Fige une nouvelle version horodatée de la liste (cahier des
        charges §31) : chaque publication (première publication,
        republication après correction, ou permutation via un échange de
        service validé — cf. quarts/echanges.py::valider_echange) enregistre
        un nouvel instantané des créneaux, sans jamais réécrire ni supprimer
        les versions précédentes. `self.versions` est le related_name défini
        sur VersionQuart/VersionServiceGarde (ci-dessous) : fonctionne à
        l'identique pour les deux modèles concrets sans code spécifique ici."""
        dernier_numero = self.versions.aggregate(models.Max("numero"))["numero__max"] or 0
        creneaux_fige = [
            {
                "poste": c.poste,
                "debut": timezone.localtime(c.debut).strftime("%d/%m/%Y %H:%M"),
                "fin": timezone.localtime(c.fin).strftime("%d/%m/%Y %H:%M"),
                "marin_id": c.marin_id,
                "marin_nom": (c.marin.get_full_name() or c.marin.username) if c.marin_id else "",
                "note": c.note,
            }
            for c in self.creneaux.select_related("marin").order_by("debut")
        ]
        return self.versions.create(
            numero=dernier_numero + 1, publiee_le=timezone.now(), publiee_par=user, creneaux_fige=creneaux_fige,
        )

    def version_a_la_date(self, date_):
        """Dernière version de la liste publiée au plus tard le `date_`
        donné (borne de fin de journée locale) — répond à « quelle liste
        était active à telle date » (cahier des charges §31). None si la
        liste n'était pas encore publiée à cette date."""
        limite = timezone.make_aware(datetime.combine(date_, heure_du_jour.max))
        return self.versions.filter(publiee_le__lte=limite).order_by("-numero").first()

    def __str__(self):
        fonction = f" [{self.fonction}]" if self.fonction_id else ""
        return f"{self.nom or self.libelle_type().capitalize()}{fonction} — {self.perimetre} ({self.date_debut} au {self.date_fin})"


class Quart(ListeServiceAbstract):
    """Liste de quarts : rotation de postes à créneaux courts et répétés
    (ex. barre, passerelle, machine — toutes les 4h). `duree_creneau_heures`
    n'est qu'une durée par défaut éditable pré-remplissant le formulaire
    d'ajout d'un créneau (aucune règle codée en dur, CLAUDE.md §6).
    `fonction` (obligatoire, cf. correction de cadrage du 09/09/2026 en tête
    de module) rattache la liste à une fonction de quart transversale aux
    secteurs/services (ex. Barre, Veille, Machine avant)."""

    fonction = models.ForeignKey(
        FonctionQuartChoice, null=True, blank=False, on_delete=models.PROTECT,
        related_name="quarts", verbose_name="Fonction de quart",
    )
    duree_creneau_heures = models.PositiveSmallIntegerField(
        default=4, verbose_name="Durée par défaut d'un créneau (heures)"
    )

    class Meta(ListeServiceAbstract.Meta):
        verbose_name = "Liste de quarts"
        verbose_name_plural = "Listes de quarts"

    def libelle_type(self):
        return "quart"


class ServiceGarde(ListeServiceAbstract):
    """Liste de services à quai/gardes : affectation longue (ex. garde 24h,
    garde de nuit, permanence — cf. cahier des charges Notion §9). `type_service`
    est un texte libre (pas une liste fermée figée dans le code) et
    `duree_creneau_heures` n'est qu'une durée par défaut éditable, même
    principe que Quart.duree_creneau_heures ci-dessus. `fonction` (obligatoire,
    cf. correction de cadrage du 09/09/2026 en tête de module) réutilise le
    référentiel ServiceFunctionChoice déjà existant pour le profil marin
    (accounts.models) — pas de nouveau référentiel dupliqué pour les gardes."""

    fonction = models.ForeignKey(
        ServiceFunctionChoice, null=True, blank=False, on_delete=models.PROTECT,
        related_name="services_garde", verbose_name="Fonction de service",
    )
    type_service = models.CharField(max_length=255, blank=True, default="", verbose_name="Type de service")
    duree_creneau_heures = models.PositiveSmallIntegerField(
        default=24, verbose_name="Durée par défaut d'un créneau (heures)"
    )
    # Règles des échanges de tour (VISION §7.4, CLAUDE.md §6) : configurables
    # par liste, jamais codées en dur. Formations dont le marin qui reprend un
    # tour doit avoir une validation encore valable le jour du tour, et délai
    # minimal (en heures) entre une demande d'échange et le début du tour.
    formations_requises = models.ManyToManyField(
        "training.TrainingCourse", blank=True, related_name="services_garde_exigeant",
        verbose_name="Habilitations requises pour tenir ce service",
    )
    delai_minimal_echange_heures = models.PositiveSmallIntegerField(
        default=0, verbose_name="Délai minimal avant le tour pour demander un échange (heures)"
    )

    class Meta(ListeServiceAbstract.Meta):
        verbose_name = "Liste de services de garde"
        verbose_name_plural = "Listes de services de garde"

    def libelle_type(self):
        return "service de garde"


class CreneauAbstract(TimeStampedModel):
    """Créneau élémentaire d'une liste : un poste, une plage horaire, un marin
    affecté (facultatif tant que l'affectation n'a pas encore été décidée).
    Une même plage horaire/poste nécessitant plusieurs marins se traduit par
    plusieurs créneaux distincts (une ligne par marin, comme dans un tableur
    Excel) plutôt qu'une affectation multiple sur un seul créneau — reste le
    plus simple et le plus rapide à saisir (CLAUDE.md §2)."""

    poste = models.CharField(max_length=255, verbose_name="Poste")
    debut = models.DateTimeField(verbose_name="Début")
    fin = models.DateTimeField(verbose_name="Fin")
    marin = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="%(class)ss_affectes", verbose_name="Marin affecté",
    )
    note = models.TextField(blank=True, default="")

    class Meta:
        abstract = True
        ordering = ("debut",)

    def clean(self):
        super().clean()
        if self.debut and self.fin and self.fin <= self.debut:
            raise ValidationError({"fin": "L'heure de fin doit être postérieure à l'heure de début."})

    def __str__(self):
        return f"{self.poste} — {self.debut:%d/%m/%Y %H:%M}"


class CreneauQuart(CreneauAbstract):
    quart = models.ForeignKey(Quart, on_delete=models.CASCADE, related_name="creneaux")

    class Meta(CreneauAbstract.Meta):
        verbose_name = "Créneau de quart"
        verbose_name_plural = "Créneaux de quart"


class CreneauServiceGarde(CreneauAbstract):
    service_garde = models.ForeignKey(ServiceGarde, on_delete=models.CASCADE, related_name="creneaux")

    class Meta(CreneauAbstract.Meta):
        verbose_name = "Créneau de service de garde"
        verbose_name_plural = "Créneaux de service de garde"


class VersionListeAbstract(TimeStampedModel):
    """Instantané figé d'une liste au moment d'une publication (versionnage,
    cahier des charges §31) : jamais réécrit ni supprimé après coup, même si
    la liste est ensuite corrigée ou republiée — permet de savoir quelle
    affectation était active à une date donnée (cf. ListeServiceAbstract.
    version_a_la_date). Inspiré du versionnage par instantané déjà utilisé
    par les rondes (rondes.models.RondeModele.version + ResultatPoint qui
    copie les points du modèle), adapté ici en snapshot complet des créneaux
    (nécessaire pour répondre à « quelle était la liste active à telle
    date », pas seulement détecter qu'un changement a eu lieu)."""

    numero = models.PositiveIntegerField(verbose_name="Numéro de version")
    publiee_le = models.DateTimeField(verbose_name="Publiée le")
    publiee_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Publiée par",
    )
    # Instantané des créneaux au moment de la publication : liste de dicts
    # {poste, debut, fin (déjà formatés en français), marin_id, marin_nom,
    # note} — snapshot texte plutôt que FK vers les créneaux vivants, pour ne
    # jamais dépendre de leur état futur (un créneau peut être modifié,
    # réaffecté par un échange, ou supprimé après coup).
    creneaux_fige = models.JSONField(default=list, verbose_name="Créneaux figés")

    class Meta:
        abstract = True
        ordering = ("-numero",)

    def __str__(self):
        return f"Version {self.numero} du {self.publiee_le:%d/%m/%Y %H:%M}"


class VersionQuart(VersionListeAbstract):
    quart = models.ForeignKey(Quart, on_delete=models.CASCADE, related_name="versions")

    class Meta(VersionListeAbstract.Meta):
        verbose_name = "Version de liste de quarts"
        verbose_name_plural = "Versions de liste de quarts"
        unique_together = ("quart", "numero")


class VersionServiceGarde(VersionListeAbstract):
    service_garde = models.ForeignKey(ServiceGarde, on_delete=models.CASCADE, related_name="versions")

    class Meta(VersionListeAbstract.Meta):
        verbose_name = "Version de liste de services de garde"
        verbose_name_plural = "Versions de liste de services de garde"
        unique_together = ("service_garde", "numero")


class EchangeService(TimeStampedModel):
    """Échange de deux tours de service de garde d'une même liste (VISION
    §7.4) : le marin A (`demandeur`) propose de céder son créneau contre celui
    du marin B (`cible`). B accepte ou refuse ; si B accepte, le chef de liste
    valide en dernier ; seulement alors les deux affectations sont permutées.

    `demandeur`/`cible` et les libellés de créneaux sont figés à la création :
    ils conservent la situation d'AVANT l'échange (jamais d'écrasement silencieux
    de l'ancienne affectation, même si les créneaux changent ou disparaissent).
    Le déroulé complet vit dans EchangeServiceEvenement."""

    STATUT_DEMANDE = "DEMANDE"
    STATUT_ACCEPTE = "ACCEPTE"
    STATUT_VALIDE = "VALIDE"
    STATUT_REFUSE = "REFUSE"
    STATUT_REJETE = "REJETE"
    STATUT_ANNULE = "ANNULE"
    STATUT_CHOICES = (
        (STATUT_DEMANDE, "En attente de l'accord du marin"),
        (STATUT_ACCEPTE, "En attente du chef de liste"),
        (STATUT_VALIDE, "Échange validé"),
        (STATUT_REFUSE, "Refusé par le marin"),
        (STATUT_REJETE, "Refusé par le chef de liste"),
        (STATUT_ANNULE, "Annulé"),
    )
    STATUTS_EN_COURS = (STATUT_DEMANDE, STATUT_ACCEPTE)

    creneau_demandeur = models.ForeignKey(
        CreneauServiceGarde, null=True, on_delete=models.SET_NULL, related_name="echanges_proposes"
    )
    creneau_cible = models.ForeignKey(
        CreneauServiceGarde, null=True, on_delete=models.SET_NULL, related_name="echanges_recus"
    )
    libelle_creneau_demandeur = models.CharField(max_length=255, default="")
    libelle_creneau_cible = models.CharField(max_length=255, default="")
    demandeur = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="echanges_demandes")
    cible = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="echanges_proposes_a")
    statut = models.CharField(max_length=16, choices=STATUT_CHOICES, default=STATUT_DEMANDE)
    motif = models.TextField(blank=True, default="", verbose_name="Motif de la demande")
    motif_decision = models.TextField(blank=True, default="", verbose_name="Motif du refus")
    accepte_le = models.DateTimeField(null=True, blank=True)
    decide_le = models.DateTimeField(null=True, blank=True)
    decide_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="echanges_decides"
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Échange de service"
        verbose_name_plural = "Échanges de service"

    @property
    def en_cours(self):
        return self.statut in self.STATUTS_EN_COURS

    @property
    def liste(self):
        creneau = self.creneau_demandeur or self.creneau_cible
        return creneau.service_garde if creneau else None

    def __str__(self):
        return f"Échange {self.demandeur} ↔ {self.cible} ({self.get_statut_display()})"


class EchangeServiceEvenement(TimeStampedModel):
    """Historique immuable d'un échange : qui a fait quoi et quand, avec
    l'ancienne et la nouvelle valeur lors de la permutation."""

    echange = models.ForeignKey(EchangeService, on_delete=models.CASCADE, related_name="evenements")
    acteur = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=64)
    detail = models.TextField(blank=True, default="")

    LIBELLES = {
        "demande": "Demande envoyée",
        "acceptation": "Accepté par le marin",
        "refus_marin": "Refusé par le marin",
        "annulation": "Demande annulée",
        "annulation_creneau_supprime": "Annulé (créneau supprimé)",
        "refus_chef": "Refusé par le chef de liste",
        "validation": "Validé par le chef de liste, tours permutés",
    }

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name = "Événement d'échange"
        verbose_name_plural = "Événements d'échange"

    def get_action_libelle(self):
        return self.LIBELLES.get(self.action, self.action)


# ---------------------------------------------------------------------------
# Feuille de service quotidienne (tâche Notion « Feuille de service
# quotidienne — personnel de service et en-tête (à quai) »), périmètre V1
# limité au navire à quai (pas de version « en mer », cf. tâche de suivi).
#
# Pourquoi dans l'app `quarts` plutôt qu'une nouvelle app : la feuille de
# service n'a de sens que parce qu'elle recopie AUTOMATIQUEMENT le personnel
# de service du jour depuis les tours déjà publiés (ServiceGarde/
# CreneauServiceGarde, cf. correspondance ci-dessous) — elle est
# structurellement un CONSOMMATEUR de `quarts`, pas un domaine métier séparé.
# Une nouvelle app aurait imposé soit un import circulaire, soit une
# duplication du référentiel/de la logique de correspondance poste <->
# fonction. Rester ici permet de réutiliser tel quel `RoleThresholdConfig`/
# role_thresholds.py (seuils de visa) et `AuditLog`/`Notification` déjà
# importés dans ce module.
#
# Correspondance fonction de service <-> tour de service publié :
# `ServiceGarde.fonction` (FK ServiceFunctionChoice) porte une fonction pour
# TOUTE une liste (ex. « Gradé coupé »), tandis que `CreneauAbstract.poste`
# (texte libre) distingue les titulaires SIMULTANÉS d'une même fonction un
# jour donné (ex. « Gradé coupé 1 », « Gradé coupé 2 », cf. docstring de
# CreneauAbstract : « une ligne par marin »). La feuille de service a besoin
# de CETTE granularité fine (chaque ligne de la feuille = un poste précis) :
# la correspondance se fait donc sur `poste` (FonctionFeuilleService.
# poste_recherche, comparé sans casse), pas sur `ServiceGarde.fonction`.
# Seuls les créneaux d'une liste PUBLIÉE comptent, et le calcul est fait EN
# DIRECT à chaque affichage (jamais figé sur la feuille elle-même) : si un
# échange de service est validé après publication de la feuille, la page
# reflète immédiatement le nouveau titulaire sans action sur la feuille — la
# trace de l'échange reste dans EchangeServiceEvenement (quarts/echanges.py),
# pas dupliquée ici (CLAUDE.md §2 : pas de sur-ingénierie pour une simple
# lecture). Seul l'INSTANTANÉ figé à la publication (VersionFeuilleService)
# ne bouge plus après coup, comme n'importe quel historique.
#
# Circuit de validation (décision de Matthis du 24/09/2026, même esprit que
# la fiche d'installation — page Notion « Organigramme et rôles », section 4
# — avec un palier de plus car le rédacteur, le BSC, n'est en général qu'un
# opérateur de secteur) :
#
#   BROUILLON --(proposer)--> [VISA_SECTEUR, sauté si le rédacteur est déjà
#   CHEF_SECTEUR ou plus] --> VISA_SERVICE --> VISA_COMAEQ --(le visa COMAEQ
#   vaut publication, un seul clic)--> PUBLIEE
#
# Hypothèse de cadrage à signaler explicitement (reprise dans le
# compte-rendu [Dev] de la tâche) : le rôle COMAEQ (commandant adjoint
# équipage) n'a PAS de modélisation dédiée dans l'application (page Notion
# « Organigramme et rôles », section 3 : ligne « Commandants adjoints »
# marquée 🆕 ; tâche Notion « [CADRAGE @po] Ajouter le niveau des
# commandants adjoints » encore À faire, avec la mention explicite
# « Prérequis du circuit de validation des fiches de maintenance » — cette
# feuille de service a EXACTEMENT le même prérequis manquant). En son
# absence, le visa « COMAEQ » est ici approximé par le seuil de rôle
# ETAT_MAJOR sur le NAVIRE de la feuille (n'importe quel membre de
# l'état-major du bord, pas seulement celui en charge de l'équipage) —
# seuil configurable comme les deux autres visas (matrix/core/
# role_thresholds.py, catégorie « Feuille de service »). À corriger pour
# router précisément vers le COMAEQ le jour où ce niveau existera.
#
# Comme pour ListeServiceAbstract, la publication fige un instantané
# horodaté (VersionFeuilleService) sans jamais réécrire les précédents —
# volontairement PAS une sous-classe de VersionListeAbstract : son champ
# `creneaux_fige` est nommé et documenté pour un instantané de créneaux,
# alors qu'une feuille de service fige un en-tête ET une liste de personnel,
# de forme différente. Dupliquer 4 champs triviaux (numero, publiee_le,
# publiee_par, contenu figé) est plus lisible que de détourner un nom de
# champ qui ne correspond pas au domaine — même PRINCIPE de versionnage par
# instantané (cahier des charges §31), pas la même classe.

NIVEAU_SUPERVISION_GLOBALE_FEUILLE_SERVICE = RoleLevel.COMMANDANT


class RubriqueEnTeteFeuilleService(TimeStampedModel):
    """Rubrique configurable de l'en-tête d'une feuille de service, par
    navire (CLAUDE.md §6 : aucune liste de rubriques codée en dur, la
    répartition fixe/variable dépend du navire et de sa situation). Une
    rubrique FIXE porte une valeur commune à toutes les feuilles du navire
    (ex. mesures de sécurité en vigueur, rarement modifiées) ; une rubrique
    QUOTIDIENNE est ressaisie à chaque feuille (ex. saint du jour)."""

    TYPE_FIXE = "FIXE"
    TYPE_QUOTIDIENNE = "QUOTIDIENNE"
    TYPE_CHOICES = (
        (TYPE_FIXE, "Fixe (valeur du navire)"),
        (TYPE_QUOTIDIENNE, "Saisie chaque jour"),
    )

    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="rubriques_feuille_service")
    ordre = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")
    libelle = models.CharField(max_length=128, verbose_name="Libellé")
    type_saisie = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_QUOTIDIENNE)
    valeur_fixe = models.CharField(max_length=255, blank=True, default="", verbose_name="Valeur (rubrique fixe)")
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("ordre", "pk")
        unique_together = ("ship", "libelle")
        verbose_name = "Rubrique d'en-tête (feuille de service)"
        verbose_name_plural = "Rubriques d'en-tête (feuille de service)"

    def __str__(self):
        return f"{self.libelle} ({self.ship})"


class FonctionFeuilleService(TimeStampedModel):
    """Fonction de service configurable affichée sur la feuille, par navire
    et dans un ordre configurable (ex. officier de garde, gradé coupé 1,
    gradé coupé 2...). `poste_recherche` est le texte à retrouver dans
    `CreneauServiceGarde.poste` pour ce jour (comparaison insensible à la
    casse) — laissé vide, il vaut `libelle` (cas le plus courant où le
    libellé affiché et le poste saisi dans les tours coïncident)."""

    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="fonctions_feuille_service")
    ordre = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")
    libelle = models.CharField(max_length=128, verbose_name="Fonction")
    poste_recherche = models.CharField(
        max_length=255, blank=True, default="",
        verbose_name="Poste correspondant dans les tours de service",
        help_text=(
            "Doit correspondre exactement au champ « Poste » saisi sur le créneau de service de garde "
            "(insensible à la casse). Laisser vide si identique au libellé ci-dessus."
        ),
    )
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("ordre", "pk")
        unique_together = ("ship", "libelle")
        verbose_name = "Fonction de service (feuille de service)"
        verbose_name_plural = "Fonctions de service (feuille de service)"

    def poste_a_rechercher(self):
        return (self.poste_recherche or self.libelle).strip()

    def __str__(self):
        return f"{self.libelle} ({self.ship})"


def titulaire_du_jour(fonction, date_):
    """Créneau de service de garde correspondant à `fonction`
    (FonctionFeuilleService) le jour `date_`, trouvé EN DIRECT parmi les
    créneaux déjà PUBLIÉS du navire (cf. commentaire de section :
    correspondance sur le champ `poste`, jamais figée). Un créneau
    chevauchant minuit (garde 24h) couvre le jour dès lors qu'il commence
    avant la fin de journée ET finit après son début. None si aucun créneau
    ne correspond (la feuille affiche alors « à définir » plutôt qu'une
    valeur erronée)."""
    poste = fonction.poste_a_rechercher()
    if not poste:
        return None
    debut_jour = timezone.make_aware(datetime.combine(date_, heure_du_jour.min))
    fin_jour = timezone.make_aware(datetime.combine(date_, heure_du_jour.max))
    return (
        CreneauServiceGarde.objects.select_related("marin", "marin__profile", "service_garde")
        .filter(
            Q(service_garde__ship_id=fonction.ship_id)
            | Q(service_garde__service__ship_id=fonction.ship_id)
            | Q(service_garde__sector__service__ship_id=fonction.ship_id)
            | Q(service_garde__section__sector__service__ship_id=fonction.ship_id),
            service_garde__statut=ServiceGarde.STATUT_PUBLIEE,
            poste__iexact=poste,
            debut__lte=fin_jour, fin__gte=debut_jour,
        )
        .order_by("debut")
        .first()
    )


def personnel_du_jour(ship, date_):
    """Liste ordonnée (cf. FonctionFeuilleService.Meta.ordering) du personnel
    de service du navire pour `date_` : une entrée par fonction active,
    chacune avec le créneau trouvé (ou None) — cf. titulaire_du_jour."""
    return [
        {"fonction": fonction, "creneau": titulaire_du_jour(fonction, date_)}
        for fonction in FonctionFeuilleService.objects.filter(ship=ship, actif=True)
    ]


class FeuilleService(TimeStampedModel, OwnedModel):
    """Feuille de service quotidienne d'un navire (rubriques d'en-tête +
    personnel de service), à quai (V1). Une par (navire, date) : publiée la
    veille pour le lendemain, lue par tout l'équipage."""

    STATUT_BROUILLON = "BROUILLON"
    STATUT_VISA_SECTEUR = "VISA_SECTEUR"
    STATUT_VISA_SERVICE = "VISA_SERVICE"
    STATUT_VISA_COMAEQ = "VISA_COMAEQ"
    STATUT_PUBLIEE = "PUBLIEE"
    STATUT_CHOICES = (
        (STATUT_BROUILLON, "Brouillon"),
        (STATUT_VISA_SECTEUR, "En attente du visa du chef de secteur"),
        (STATUT_VISA_SERVICE, "En attente du visa du chef de service"),
        (STATUT_VISA_COMAEQ, "En attente du visa du COMAEQ"),
        (STATUT_PUBLIEE, "Publiée"),
    )

    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="feuilles_service")
    date = models.DateField(verbose_name="Date concernée")
    statut = models.CharField(max_length=16, choices=STATUT_CHOICES, default=STATUT_BROUILLON)
    valeurs_entete = models.JSONField(
        default=dict, blank=True, verbose_name="Valeurs des rubriques d'en-tête",
        help_text="Dictionnaire {id de la rubrique : valeur saisie} pour les rubriques « saisie chaque jour ».",
    )
    # Périmètre du rédacteur au moment de la proposition (snapshot) : détermine
    # qui doit viser en secteur/service — cf. commentaire de section.
    secteur_redacteur = models.ForeignKey(
        Sector, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Secteur du rédacteur",
    )
    service_redacteur = models.ForeignKey(
        Service, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Service du rédacteur",
    )
    proposee_le = models.DateTimeField(null=True, blank=True, verbose_name="Proposée le")
    proposee_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Proposée par",
    )
    visa_secteur_le = models.DateTimeField(null=True, blank=True, verbose_name="Visa secteur le")
    visa_secteur_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Visa secteur par",
    )
    visa_service_le = models.DateTimeField(null=True, blank=True, verbose_name="Visa service le")
    visa_service_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Visa service par",
    )
    visa_comaeq_le = models.DateTimeField(null=True, blank=True, verbose_name="Visa COMAEQ le")
    visa_comaeq_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Visa COMAEQ par",
    )
    publiee_le = models.DateTimeField(null=True, blank=True, verbose_name="Publiée le")
    publiee_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Publiée par",
    )
    motif_retour = models.TextField(blank=True, default="", verbose_name="Motif du dernier renvoi en brouillon")

    class Meta:
        unique_together = ("ship", "date")
        ordering = ("-date",)
        verbose_name = "Feuille de service"
        verbose_name_plural = "Feuilles de service"

    def __str__(self):
        return f"Feuille de service du {self.date:%d/%m/%Y} — {self.ship}"

    @property
    def rubriques_affichees(self):
        """Rubriques actives du navire avec leur valeur pour CETTE feuille :
        la valeur fixe du navire pour une rubrique FIXE (toujours à jour,
        jamais figée par feuille), la valeur saisie pour une rubrique
        QUOTIDIENNE."""
        resultat = []
        for rubrique in RubriqueEnTeteFeuilleService.objects.filter(ship_id=self.ship_id, actif=True):
            valeur = (
                rubrique.valeur_fixe if rubrique.type_saisie == rubrique.TYPE_FIXE
                else self.valeurs_entete.get(str(rubrique.pk), "")
            )
            resultat.append({"rubrique": rubrique, "valeur": valeur})
        return resultat

    @property
    def personnel(self):
        return personnel_du_jour(self.ship, self.date)

    def marins_de_la_fraction(self):
        """Marins de la fraction de service du jour (titulaires trouvés dans
        le personnel de service), sans doublon — jamais tout l'équipage
        (cf. tâche Notion)."""
        ids, marins = set(), []
        for entree in self.personnel:
            creneau = entree["creneau"]
            if creneau and creneau.marin_id and creneau.marin_id not in ids:
                ids.add(creneau.marin_id)
                marins.append(creneau.marin)
        return marins

    def validateurs_a_notifier(self):
        """Marins habilités à donner le prochain visa attendu — repli sur le
        rédacteur si personne n'est identifié (même filet de sécurité que
        publicateurs_a_notifier ci-dessus pour Quart/ServiceGarde)."""
        verificateur = {
            self.STATUT_VISA_SECTEUR: peut_viser_secteur,
            self.STATUT_VISA_SERVICE: peut_viser_service,
            self.STATUT_VISA_COMAEQ: peut_viser_comaeq,
        }.get(self.statut)
        if verificateur is None:
            return []
        destinataires = [
            u for u in User.objects.filter(is_active=True, profile__ship_id=self.ship_id).select_related("profile")
            if verificateur(u, self)
        ]
        if not destinataires and self.created_by_id:
            destinataires = [self.created_by]
        return destinataires

    def _notifier_prochain_visa(self):
        for destinataire in self.validateurs_a_notifier():
            Notification.objects.create(
                user=destinataire,
                verb=f"Feuille de service du {self.date:%d/%m/%Y} ({self.ship}) attend votre visa.",
                level=NotificationLevel.WARNING,
            )

    def proposer(self, user):
        """BROUILLON -> premier palier de visa : secteur du rédacteur, SAUF
        si le rédacteur est déjà chef de secteur ou plus, auquel cas le visa
        secteur est sauté (cf. commentaire de section)."""
        profile = user.profile
        self.secteur_redacteur = profile.sector or (profile.section.sector if profile.section_id else None)
        self.service_redacteur = self.secteur_redacteur.service if self.secteur_redacteur else profile.service
        saute_visa_secteur = user_role_level(user) >= RoleLevel.CHEF_SECTEUR
        self.statut = self.STATUT_VISA_SERVICE if saute_visa_secteur else self.STATUT_VISA_SECTEUR
        self.proposee_le = timezone.now()
        self.proposee_par = user
        self.save(update_fields=[
            "secteur_redacteur", "service_redacteur", "statut", "proposee_le", "proposee_par", "updated_at",
        ])
        AuditLog.objects.create(
            actor=user, action="feuille_service_proposee",
            details=f"Feuille de service du {self.date:%d/%m/%Y} ({self.ship}) proposée à la validation.",
        )
        self._notifier_prochain_visa()

    def viser_secteur(self, user):
        self.visa_secteur_le = timezone.now()
        self.visa_secteur_par = user
        self.statut = self.STATUT_VISA_SERVICE
        self.save(update_fields=["visa_secteur_le", "visa_secteur_par", "statut", "updated_at"])
        AuditLog.objects.create(
            actor=user, action="feuille_service_visa_secteur",
            details=f"Feuille de service du {self.date:%d/%m/%Y} ({self.ship}) visée par le chef de secteur.",
        )
        self._notifier_prochain_visa()

    def viser_service(self, user):
        self.visa_service_le = timezone.now()
        self.visa_service_par = user
        self.statut = self.STATUT_VISA_COMAEQ
        self.save(update_fields=["visa_service_le", "visa_service_par", "statut", "updated_at"])
        AuditLog.objects.create(
            actor=user, action="feuille_service_visa_service",
            details=f"Feuille de service du {self.date:%d/%m/%Y} ({self.ship}) visée par le chef de service.",
        )
        self._notifier_prochain_visa()

    def viser_comaeq(self, user):
        """Dernier visa : vaut publication immédiate, un seul clic — aucun
        acteur distinct n'intervient entre le visa COMAEQ et la publication
        d'après le circuit décrit par Matthis (CLAUDE.md §2)."""
        self.visa_comaeq_le = timezone.now()
        self.visa_comaeq_par = user
        AuditLog.objects.create(
            actor=user, action="feuille_service_visa_comaeq",
            details=f"Feuille de service du {self.date:%d/%m/%Y} ({self.ship}) visée par le COMAEQ.",
        )
        self._publier(user)

    def _publier(self, user):
        self.statut = self.STATUT_PUBLIEE
        self.publiee_le = timezone.now()
        self.publiee_par = user
        self.save(update_fields=[
            "statut", "visa_comaeq_le", "visa_comaeq_par", "publiee_le", "publiee_par", "updated_at",
        ])
        version = self.creer_version(user)
        AuditLog.objects.create(
            actor=user, action="feuille_service_publiee",
            details=f"Feuille de service du {self.date:%d/%m/%Y} ({self.ship}) publiée, version {version.numero}.",
        )
        for marin in self.marins_de_la_fraction():
            Notification.objects.create(
                user=marin,
                verb=f"Feuille de service du {self.date:%d/%m/%Y} publiée : vous êtes de service.",
                level=NotificationLevel.INFO,
            )

    def renvoyer(self, user, motif):
        """Renvoie la feuille en BROUILLON depuis n'importe quel palier de
        visa en cours, avec un motif obligatoire, pour que le rédacteur
        corrige avant de reproposer — le circuit recommence entièrement
        (aucun visa déjà donné n'est conservé), plus simple à suivre qu'un
        redémarrage partiel (CLAUDE.md §2)."""
        self.statut = self.STATUT_BROUILLON
        self.visa_secteur_le = self.visa_secteur_par = None
        self.visa_service_le = self.visa_service_par = None
        self.visa_comaeq_le = self.visa_comaeq_par = None
        self.proposee_le = self.proposee_par = None
        self.motif_retour = motif
        self.save(update_fields=[
            "statut", "visa_secteur_le", "visa_secteur_par", "visa_service_le", "visa_service_par",
            "visa_comaeq_le", "visa_comaeq_par", "proposee_le", "proposee_par", "motif_retour", "updated_at",
        ])
        AuditLog.objects.create(
            actor=user, action="feuille_service_renvoyee",
            details=f"Feuille de service du {self.date:%d/%m/%Y} ({self.ship}) renvoyée en brouillon : {motif}",
        )
        if self.created_by_id:
            Notification.objects.create(
                user=self.created_by,
                verb=f"Feuille de service du {self.date:%d/%m/%Y} renvoyée pour correction : {motif}",
                level=NotificationLevel.WARNING,
            )

    def creer_version(self, user):
        """Fige un instantané horodaté de l'en-tête ET du personnel de
        service au moment de la publication (cahier des charges §31) — cf.
        commentaire de section sur le choix de ne pas réutiliser
        VersionListeAbstract tel quel."""
        dernier_numero = self.versions.aggregate(models.Max("numero"))["numero__max"] or 0
        contenu = {
            "entete": [{"libelle": e["rubrique"].libelle, "valeur": e["valeur"]} for e in self.rubriques_affichees],
            "personnel": [
                {
                    "fonction": e["fonction"].libelle,
                    "marin": (
                        f"{e['creneau'].marin.profile.grade} "
                        f"{e['creneau'].marin.get_full_name() or e['creneau'].marin.username}".strip()
                        if e["creneau"] and e["creneau"].marin_id else ""
                    ),
                }
                for e in self.personnel
            ],
        }
        return self.versions.create(
            numero=dernier_numero + 1, publiee_le=timezone.now(), publiee_par=user, contenu_fige=contenu,
        )

    def version_a_la_date(self, date_):
        """Dernière version publiée au plus tard le `date_` donné — même
        principe que ListeServiceAbstract.version_a_la_date."""
        limite = timezone.make_aware(datetime.combine(date_, heure_du_jour.max))
        return self.versions.filter(publiee_le__lte=limite).order_by("-numero").first()


class VersionFeuilleService(TimeStampedModel):
    """Instantané figé d'une feuille de service au moment de sa publication
    — même PRINCIPE de versionnage que VersionListeAbstract (cf. commentaire
    de section), pas la même classe : la forme du contenu figé diffère
    (en-tête + personnel, pas des créneaux)."""

    feuille = models.ForeignKey(FeuilleService, on_delete=models.CASCADE, related_name="versions")
    numero = models.PositiveIntegerField(verbose_name="Numéro de version")
    publiee_le = models.DateTimeField(verbose_name="Publiée le")
    publiee_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Publiée par",
    )
    contenu_fige = models.JSONField(default=dict, verbose_name="Contenu figé (en-tête + personnel)")

    class Meta:
        ordering = ("-numero",)
        unique_together = ("feuille", "numero")
        verbose_name = "Version de feuille de service"
        verbose_name_plural = "Versions de feuille de service"

    def __str__(self):
        return f"Version {self.numero} du {self.publiee_le:%d/%m/%Y %H:%M}"


def _est_supervision_globale_feuille(user):
    return user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_FEUILLE_SERVICE


def peut_rediger_feuille_service(user, ship):
    """Quiconque appartient au navire peut créer/modifier le brouillon de la
    feuille de service. Hypothèse de cadrage à signaler : en réalité seul le
    BSC (une astreinte organisationnelle, pas un rôle applicatif) rédige la
    feuille — l'application ne restreint pas la rédaction à cette astreinte,
    qu'elle ne modélise pas ; le circuit de visa (secteur/service/COMAEQ)
    garantit de toute façon qu'une feuille mal rédigée ne peut pas être
    publiée sans contrôle."""
    return _est_supervision_globale_feuille(user) or ship_id_for_user(user) == ship.pk


def peut_gerer_brouillon_feuille(user, feuille):
    """Modifier l'en-tête d'une feuille encore en BROUILLON, ou la
    reproposer après un renvoi : réservé à son rédacteur d'origine ou à la
    supervision globale."""
    if feuille.statut != FeuilleService.STATUT_BROUILLON:
        return False
    return _est_supervision_globale_feuille(user) or feuille.created_by_id == user.pk


def peut_viser_secteur(user, feuille):
    if _est_supervision_globale_feuille(user):
        return True
    if feuille.secteur_redacteur_id is None:
        return False
    seuil = niveau_requis_pour(user, "feuille_service_visa_secteur")
    return _perimetre_dans_scope_utilisateur(user, None, None, feuille.secteur_redacteur, None, seuil)


def peut_viser_service(user, feuille):
    if _est_supervision_globale_feuille(user):
        return True
    if feuille.service_redacteur_id is None:
        return False
    seuil = niveau_requis_pour(user, "feuille_service_visa_service")
    return _perimetre_dans_scope_utilisateur(user, None, feuille.service_redacteur, None, None, seuil)


def peut_viser_comaeq(user, feuille):
    """Approximation du visa COMAEQ (cf. commentaire de section) : n'importe
    quel membre de l'état-major du navire, en l'absence d'un niveau
    commandant adjoint dédié dans l'application."""
    if _est_supervision_globale_feuille(user):
        return True
    seuil = niveau_requis_pour(user, "feuille_service_visa_comaeq")
    return _perimetre_dans_scope_utilisateur(user, feuille.ship, None, None, None, seuil)


def peut_lire_feuille_service(user, feuille):
    """Lecture : ouverte à tout marin du navire une fois PUBLIÉE (« tous les
    marins la lisent », cf. tâche Notion) ; réservée aux acteurs du circuit
    tant qu'elle est en brouillon ou en cours de visa."""
    if feuille.statut == FeuilleService.STATUT_PUBLIEE:
        return _est_supervision_globale_feuille(user) or ship_id_for_user(user) == feuille.ship_id
    return (
        peut_gerer_brouillon_feuille(user, feuille)
        or peut_viser_secteur(user, feuille)
        or peut_viser_service(user, feuille)
        or peut_viser_comaeq(user, feuille)
    )
