import uuid
from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from matrix.core.models import TimeStampedModel, OwnedModel
from assets.models import Asset, Installation
from org.models import Ship, Service, Sector, Section
from accounts.models import Roles, UserProfile
from notifications.models import NotificationLevel

User = get_user_model()

# Statuts CorrectiveTicket considérés "ouverts" (dossier encore actif) — référence
# unique pour les tableaux de bord (graphique service + Vue flotte), afin de ne pas
# dupliquer cette règle métier à plusieurs endroits.
STATUTS_TICKET_OUVERTS = [
    "REPORTED", "DIAGNOSED", "WAITING_PARTS", "PLANNED", "IN_REPAIR", "TESTING",
]

class CorrectiveTicket(TimeStampedModel, OwnedModel):
    STATUS = (
        ("REPORTED", "Signalé"),
        ("DIAGNOSED", "Diagnostiqué"),
        ("WAITING_PARTS", "En attente pièces"),
        ("PLANNED", "Planifié"),
        ("IN_REPAIR", "En réparation"),
        ("TESTING", "En test"),
        ("RETURNED_TO_SERVICE", "Remis en service"),
        ("CLOSED", "Fermé"),
        ("BLOCKED", "Bloqué"),
        ("CANCELLED", "Annulé"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Un ticket vise un matériel mobile (asset) OU une installation fixe
    # (installation), jamais les deux (voir clean) : les deux sont nullables au
    # niveau base pour rester rétrocompatible avec les tickets existants, tous
    # rattachés à un asset.
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.CASCADE, related_name="tickets")
    installation = models.ForeignKey(
        Installation, null=True, blank=True, on_delete=models.CASCADE, related_name="tickets",
        verbose_name="Installation concernée",
    )
    created_by_text = models.CharField(max_length=255, blank=True, default="")
    reported_at = models.DateTimeField(default=timezone.now)
    planned_for = models.DateField(null=True, blank=True)
    description = models.TextField()
    severity = models.PositiveSmallIntegerField(default=3)
    status = models.CharField(max_length=24, choices=STATUS, default="REPORTED")
    # M2M plutôt qu'un FK unique : un ticket correctif peut mobiliser plusieurs
    # marins (ex. électricien + mécanicien), même logique que
    # MaintenanceOccurrence.assignees. Permet de construire "mes tickets" sur le
    # tableau de bord personnel (principe fondamental n°3 de CLAUDE.md), à
    # l'identique de mes_maintenances/mes_formations.
    assignees = models.ManyToManyField(User, blank=True, related_name="assigned_tickets")
    # Retour d'expérience (REX) : capturé directement sur le ticket plutôt que dans
    # un modèle séparé, la donnée brute existant déjà ici (description, historique
    # de statuts, actif concerné). blank=True au niveau modèle pour rester
    # rétrocompatible avec les tickets déjà existants (migration sans valeur par
    # défaut cassante) ; le caractère obligatoire au passage en statut CLOSED est
    # appliqué côté vue (TicketTransitionView), pas ici, pour ne pas bloquer les
    # autres transitions du cycle de vie.
    diagnostic_final = models.TextField(blank=True, default="", verbose_name="Diagnostic final")
    solution = models.TextField(blank=True, default="", verbose_name="Solution appliquée")
    # Signature de validation (T-FEAT signature) : le passage au statut RETURNED_TO_SERVICE
    # exige une ré-authentification légère (mot de passe courant, cf. TicketTransitionView)
    # avant d'être appliqué. AuditLog trace déjà "qui a fait quoi", mais ces deux champs
    # distinguent explicitement une validation engageante d'une simple modification.
    valide_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tickets_valides", verbose_name="Validé par",
    )
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name="Date de validation")

    def clean(self):
        super().clean()
        if bool(self.asset_id) == bool(self.installation_id):
            raise ValidationError("Un ticket doit viser un matériel OU une installation (l'un des deux, pas les deux).")

    @property
    def equipement(self):
        """Équipement visé par le ticket : matériel mobile ou installation fixe."""
        return self.installation or self.asset

    def __str__(self):
        return f"Ticket {self.equipement}"


class TicketStatusLog(TimeStampedModel):
    ticket = models.ForeignKey(CorrectiveTicket, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=24)
    new_status = models.CharField(max_length=24)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True, default="")

class PartRequest(TimeStampedModel, OwnedModel):
    STATUS = (
        ("OPEN", "Ouverte"),
        ("CLOSED", "Fermée"),
    )
    ticket = models.ForeignKey(CorrectiveTicket, on_delete=models.CASCADE, related_name="part_requests")
    requested_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    needed_by_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="OPEN")

class PartLineItem(TimeStampedModel):
    STATUS = (
        ("TO_ORDER", "À commander"),
        ("ORDERED", "Commandée"),
        ("SHIPPED", "Expédiée"),
        ("RECEIVED", "Reçue"),
        ("CONSUMED", "Consommée"),
        ("RETURNED", "Retournée"),
    )
    part_request = models.ForeignKey(PartRequest, on_delete=models.CASCADE, related_name="lines")
    reference = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    qty = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS, default="TO_ORDER")
    vendor = models.CharField(max_length=255, blank=True, default="")
    order_number = models.CharField(max_length=255, blank=True, default="")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ordered_at = models.DateField(null=True, blank=True)
    received_at = models.DateField(null=True, blank=True)

class StockPiece(TimeStampedModel, OwnedModel):
    """Stock proactif de pièces de rechange, indépendant de tout ticket correctif.

    Permet de suivre un inventaire bord avec seuil d'alerte (quantite_minimale),
    contrairement à PartLineItem qui n'existe que rattaché à un CorrectiveTicket
    (logistique purement réactive).
    """
    reference = models.CharField(max_length=255, verbose_name="Référence")
    designation = models.CharField(max_length=255, verbose_name="Désignation")
    # NNO : Numéro de Nomenclature OTAN, référence militaire standard permettant
    # d'identifier une pièce de façon univoque entre bâtiments et armées. Texte
    # libre (pas de format imposé) et optionnel : rétrocompatible avec les
    # pièces déjà existantes, saisies avant l'ajout de ce champ.
    nno = models.CharField(max_length=50, blank=True, default="", verbose_name="NNO (Numéro de Nomenclature OTAN)")
    quantite = models.PositiveIntegerField(default=0, verbose_name="Quantité")
    quantite_minimale = models.PositiveIntegerField(default=0, verbose_name="Quantité minimale")
    # Seuil critique (optionnel) : franchi, il déclenche une alerte de niveau
    # supérieur (DANGER) à celle du seuil bas (WARNING), cf. notifications/tasks.py
    # ::notify_low_stock. Nullable plutôt qu'une valeur par défaut arbitraire, même
    # convention que Installation.isolation_seuil_ohms : sans valeur renseignée, le
    # comportement historique est conservé (pièce à quantité 0 = critique), pour
    # rester rétrocompatible avec les pièces déjà existantes sans backfill.
    quantite_critique = models.PositiveIntegerField(null=True, blank=True, verbose_name="Seuil critique")
    emplacement = models.CharField(max_length=255, blank=True, default="", verbose_name="Emplacement")
    # Note libre affichée dans la fiche détaillée de la pièce (pop-up), pour toute
    # information complémentaire ne méritant pas un champ dédié.
    note = models.TextField(blank=True, default="", verbose_name="Note")
    # Photo de la pièce, même mécanisme que les autres photos du projet
    # (Asset.photo, Installation.photo, InstallationPart.photo) : pas de nouveau
    # système de pièce jointe.
    photo = models.FileField(upload_to="stock_photos/", null=True, blank=True, verbose_name="Photo")
    ship = models.ForeignKey(Ship, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Unité")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Service")
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Secteur")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_pieces", verbose_name="Section")
    # Lien optionnel vers l'équipement affilié (une installation fixe OU un
    # matériel mobile, jamais les deux) : la pièce apparaît alors dans l'onglet
    # « Pièces » de la fiche de cet équipement. SET_NULL plutôt que CASCADE : la
    # suppression d'un équipement ne doit pas faire disparaître la pièce en stock,
    # seulement son rattachement.
    installation = models.ForeignKey(
        Installation, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pieces_stock", verbose_name="Installation liée",
    )
    asset = models.ForeignKey(
        Asset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pieces_stock", verbose_name="Matériel lié",
    )

    class Meta:
        verbose_name = "Pièce en stock"
        verbose_name_plural = "Pièces en stock"
        ordering = ["reference"]

    def clean(self):
        super().clean()
        if self.installation_id and self.asset_id:
            raise ValidationError(
                "Une pièce ne peut être liée qu'à un seul équipement : une installation OU un matériel, pas les deux."
            )
        # Le lien doit rester dans le même périmètre que la pièce (même secteur),
        # même principe que le contrôle déjà appliqué côté vue sur le secteur posté.
        if self.installation_id and self.installation.sector_id != self.sector_id:
            raise ValidationError({"installation": "L'installation liée doit appartenir au même secteur que la pièce."})
        if self.asset_id and self.asset.sector_id != self.sector_id:
            raise ValidationError({"asset": "Le matériel lié doit appartenir au même secteur que la pièce."})

    @property
    def seuil_critique_effectif(self):
        """Seuil critique réellement appliqué : la valeur renseignée, ou 0 par
        défaut (comportement historique : seule une rupture totale était
        considérée comme critique avant l'ajout de ce champ)."""
        return self.quantite_critique if self.quantite_critique is not None else 0

    @property
    def est_critique(self):
        return self.quantite <= self.seuil_critique_effectif

    @property
    def est_bas(self):
        return not self.est_critique and self.quantite < self.quantite_minimale

    @property
    def equipement_lie(self):
        return self.installation or self.asset

    def __str__(self):
        return f"{self.reference} - {self.designation}"


def destinataires_ticket(asset):
    """Chefs concernés par un ticket correctif portant sur cet actif — même
    construction que notifications/tasks.py::_destinataires_installation
    (chef de service/secteur dont le périmètre correspond, et chef de section
    si l'actif en a une). Point unique, appelable aussi bien depuis la
    création manuelle d'un ticket (logistics/web_views.py::TicketCreateView)
    que depuis la création automatique via le signal d'inspection QR
    (maintenance/models.py::create_corrective_on_non_conform), pour ne pas
    dupliquer cette logique de destinataires entre les deux chemins."""
    scope_filter = Q(role=Roles.CHEF_SERVICE, service=asset.service) | Q(
        role=Roles.CHEF_SECTEUR, sector=asset.sector
    )
    if asset.section_id:
        scope_filter |= Q(role=Roles.CHEF_SECTION, section=asset.section)
    return UserProfile.objects.filter(scope_filter).select_related("user")


def niveau_alerte_ticket(severity):
    """Mappe la gravité d'un ticket correctif (1-5) vers un niveau de
    notification — même code couleur que la jauge de sévérité affichée dans
    ticket_list.html (rouge >= 4, ambre == 3, vert < 3) : une anomalie grave
    déclenche un Web Push (DANGER), une anomalie mineure reste in-app (INFO).
    Point unique, partagé par la création manuelle et la création automatique
    d'un ticket correctif."""
    if severity >= 4:
        return NotificationLevel.DANGER
    if severity == 3:
        return NotificationLevel.WARNING
    return NotificationLevel.INFO


def perimetre_du_profil(profil):
    """(navire, service, secteur, section) d'un profil, remontés depuis le
    niveau le plus fin renseigné ; (None,)*4 sans profil."""
    if profil is None:
        return None, None, None, None
    section = profil.section
    sector = profil.sector or (section.sector if section else None)
    service = profil.service or (sector.service if sector else None)
    ship = profil.ship or (service.ship if service else None)
    return ship, service, sector, section


STATUTS_ANOMALIE_OUVERTS = ["SIGNALEE", "PRISE_EN_COMPTE"]


class Anomalie(TimeStampedModel, OwnedModel):
    """Signalement libre d'une anomalie constatée à bord (ex. fuite en coursive,
    obstacle sur une issue de secours), avec ou sans équipement enregistré.

    Distinct de CorrectiveTicket, qui exige un matériel mobile : une anomalie
    peut être rattachée à une Installation OU à un Asset, ou à aucun des deux
    (localisation en texte libre). Quand un matériel est identifié, un chef peut
    la convertir en ticket correctif ; le lien est conservé dans les deux sens
    (Anomalie.ticket / CorrectiveTicket.anomalie_source).
    """
    STATUTS = (
        ("SIGNALEE", "Signalée"),
        ("PRISE_EN_COMPTE", "Prise en compte"),
        ("TRAITEE", "Traitée"),
        ("CLOTUREE", "Clôturée"),
    )
    titre = models.CharField(max_length=150, verbose_name="Titre")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    # Même échelle 1-5 que CorrectiveTicket.severity, pour réutiliser
    # niveau_alerte_ticket et la même jauge colorée.
    gravite = models.PositiveSmallIntegerField(default=3, verbose_name="Gravité")
    statut = models.CharField(max_length=20, choices=STATUTS, default="SIGNALEE", verbose_name="Statut")
    localisation = models.CharField(max_length=255, blank=True, default="", verbose_name="Localisation")
    photo = models.FileField(upload_to="anomalie_photos/", null=True, blank=True, verbose_name="Photo")
    # Périmètre organisationnel, déduit de l'équipement lié sinon du profil du
    # déclarant (voir rattacher_a) : sert uniquement au scoping et aux
    # notifications, jamais saisi à la main.
    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.SET_NULL, related_name="anomalies")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.SET_NULL, related_name="anomalies")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.SET_NULL, related_name="anomalies")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="anomalies")
    installation = models.ForeignKey(
        Installation, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="anomalies", verbose_name="Installation concernée",
    )
    asset = models.ForeignKey(
        Asset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="anomalies", verbose_name="Matériel concerné",
    )
    ticket = models.OneToOneField(
        CorrectiveTicket, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="anomalie_source", verbose_name="Ticket correctif issu de l'anomalie",
    )

    class Meta:
        verbose_name = "Anomalie"
        verbose_name_plural = "Anomalies"
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.installation_id and self.asset_id:
            raise ValidationError(
                "Une anomalie ne peut être liée qu'à un seul équipement : une installation OU un matériel, pas les deux."
            )

    def rattacher_a(self, profil=None, secteur=None):
        """Renseigne navire/service/secteur/section : ceux de l'équipement lié
        s'il y en a un, sinon ceux du secteur explicitement choisi par le
        déclarant (le service et le navire en découlent, pas de section), sinon
        ceux du profil du déclarant. Sans rien de tout cela, l'anomalie reste
        sans périmètre (visible seulement de son auteur et des administrateurs)."""
        equipement = self.installation or self.asset
        if equipement:
            self.ship_id, self.service_id = equipement.ship_id, equipement.service_id
            self.sector_id, self.section_id = equipement.sector_id, equipement.section_id
            return
        ship, service, sector, section = perimetre_du_profil(profil)
        if secteur is not None and secteur != sector:
            ship, service, sector, section = secteur.service.ship, secteur.service, secteur, None
        self.ship, self.service, self.sector, self.section = ship, service, sector, section

    @property
    def equipement_lie(self):
        return self.installation or self.asset

    @property
    def est_ouverte(self):
        return self.statut in STATUTS_ANOMALIE_OUVERTS

    def __str__(self):
        return self.titre


class AnomalieStatutLog(TimeStampedModel):
    """Historique des changements de statut d'une anomalie (qui, quand, ancienne
    et nouvelle valeur) — même principe que TicketStatusLog."""
    anomalie = models.ForeignKey(Anomalie, on_delete=models.CASCADE, related_name="status_logs")
    ancien_statut = models.CharField(max_length=20)
    nouveau_statut = models.CharField(max_length=20)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at"]

    @property
    def ancien_libelle(self):
        return dict(Anomalie.STATUTS).get(self.ancien_statut, self.ancien_statut)

    @property
    def nouveau_libelle(self):
        return dict(Anomalie.STATUTS).get(self.nouveau_statut, self.nouveau_statut)


def destinataires_anomalie(anomalie):
    """Chefs concernés par une anomalie : chef de service/secteur/section dont
    le périmètre correspond, uniquement sur les niveaux renseignés (une
    anomalie sans périmètre ne notifie personne plutôt qu'un chef au hasard).
    Même construction que destinataires_ticket."""
    filtre = Q(pk__in=[])
    if anomalie.service_id:
        filtre |= Q(role=Roles.CHEF_SERVICE, service_id=anomalie.service_id)
    if anomalie.sector_id:
        filtre |= Q(role=Roles.CHEF_SECTEUR, sector_id=anomalie.sector_id)
    if anomalie.section_id:
        filtre |= Q(role=Roles.CHEF_SECTION, section_id=anomalie.section_id)
    return UserProfile.objects.filter(filtre).select_related("user")
