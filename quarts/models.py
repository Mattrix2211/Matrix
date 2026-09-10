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
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models import FonctionQuartChoice, ServiceFunctionChoice
from matrix.core.models import OwnedModel, TimeStampedModel
from matrix.core.roles import RoleLevel, user_role_level
from notifications.models import Notification
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
    """Vrai si `user` peut modifier/publier CETTE liste précise déjà
    existante (Quart ou ServiceGarde) — cf. utilisateur_autorise_pour_perimetre."""
    return utilisateur_autorise_pour_perimetre(user, liste.ship, liste.service, liste.sector, liste.section)


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
    STATUT_PUBLIEE = "PUBLIEE"
    STATUT_CHOICES = (
        (STATUT_BROUILLON, "Brouillon"),
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

    def publier(self, user):
        """Passe la liste au statut Publiée et notifie chaque marin affecté sur
        un créneau. Republier une liste déjà publiée (après une correction) ne
        renvoie pas de nouvelles notifications : seule la toute première
        publication alerte les marins, conformément au périmètre MVP de cette
        tâche (pas de workflow de republication après modification)."""
        deja_publiee = self.statut == self.STATUT_PUBLIEE
        self.statut = self.STATUT_PUBLIEE
        self.publiee_le = timezone.now()
        self.publiee_par = user
        self.save(update_fields=["statut", "publiee_le", "publiee_par", "updated_at"])
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
