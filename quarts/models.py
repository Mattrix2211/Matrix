"""Quarts et services de garde/quai (Phase 2 — Vie quotidienne, cf. VISION_MATRIX_2_0.md
§7.1/§7.2 et tâche Notion « Quarts/services »).

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
from matrix.core.scopes import scope_filters_for_user
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
    garde de nuit, permanence — cf. VISION_MATRIX_2_0.md §7.2). `type_service`
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
