"""Modèles de la session d'appareillage : préparation d'un appareillage datée
et tracée, réutilisant l'agrégation déjà écrite pour l'ancien tableau « Prêt à
appareillage » en lecture seule (occurrences en retard, relevés manquants ou
anciens, dérives non résolues, stock sous seuil sur installations critiques),
mais désormais persistée (cf. tâche Notion « [FEAT] Tableau de bord Prêt à
appareillage » — arbitrage utilisateur : une session datée, pas un état
permanent recalculé à chaque affichage).
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from matrix.core.models import OwnedModel, TimeStampedModel
from org.models import Ship


class SessionAppareillage(TimeStampedModel, OwnedModel):
    """Session de préparation à un appareillage, ouverte pour un navire donné.

    Une seule session ouverte (cloturee_le NULL) à la fois par navire : contrôle
    applicatif dans SessionAppareillageOuvrirView, pas de contrainte base de
    données (un index partiel "un seul NULL par navire" n'est pas portable de
    façon simple entre SQLite dev et PostgreSQL prod) — même choix que le reste
    de l'app pour les règles métier non triviales à exprimer en base.

    La signature réutilise exactement le pattern déjà en place sur
    MaintenanceExecution (maintenance/models.py) : valide_par (FK) + date_validation
    (DateTimeField), vérifiés par mot de passe (request.user.check_password),
    pas de nouveau mécanisme."""

    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="sessions_appareillage")
    ouverte_le = models.DateTimeField(auto_now_add=True, verbose_name="Ouverte le")
    cloturee_le = models.DateTimeField(null=True, blank=True, verbose_name="Clôturée le")
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="sessions_appareillage_signees", verbose_name="Signée par",
    )
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name="Date de signature")

    class Meta:
        ordering = ["-ouverte_le"]
        verbose_name = "Session d'appareillage"
        verbose_name_plural = "Sessions d'appareillage"

    def __str__(self):
        return f"Appareillage {self.ship} du {self.ouverte_le:%d/%m/%Y}"

    @property
    def est_ouverte(self):
        """Vrai tant que la session n'a pas été signée/clôturée — au-delà,
        aucune modification n'est plus possible (items figés)."""
        return self.cloturee_le is None

    @property
    def nombre_items(self):
        return self.items.count()

    @property
    def nombre_items_verifies(self):
        return self.items.exclude(verifie_par__isnull=True).count()

    @property
    def progression_pct(self):
        """Pourcentage d'items déjà vérifiés — alimente la barre de
        progression visuelle de la session (principe n°5 CLAUDE.md)."""
        total = self.nombre_items
        if not total:
            return 100
        return round(self.nombre_items_verifies / total * 100)

    @property
    def tout_verifie(self):
        return self.nombre_items == self.nombre_items_verifies


class ItemAppareillage(TimeStampedModel):
    """Item à vérifier dans une session d'appareillage : généré une seule fois
    à l'ouverture de la session (cf. dashboard.web_views._points_de_vigilance_navire),
    jamais recalculé ensuite — l'état constaté à l'ouverture reste la référence
    même si la situation évolue en base pendant la préparation.

    Le champ content_type/object_id référence l'objet source (occurrence en
    retard, installation avec relevé manquant/ancien ou dérive détectée, pièce
    de stock sous seuil), même pattern que notifications.models.Notification."""

    CATEGORIE_OCCURRENCE = "OCCURRENCE"
    CATEGORIE_RELEVE = "RELEVE"
    CATEGORIE_DERIVE = "DERIVE"
    CATEGORIE_STOCK = "STOCK"
    CATEGORIES = (
        (CATEGORIE_OCCURRENCE, "Essai ou relevé en attente"),
        (CATEGORIE_RELEVE, "Relevé technique manquant ou ancien"),
        (CATEGORIE_DERIVE, "Dérive détectée non résolue"),
        (CATEGORIE_STOCK, "Pièce de stock sous seuil"),
    )

    session = models.ForeignKey(SessionAppareillage, on_delete=models.CASCADE, related_name="items")
    categorie = models.CharField(max_length=16, choices=CATEGORIES)
    libelle = models.CharField(max_length=255, verbose_name="Libellé")
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=64, null=True, blank=True)
    objet_source = GenericForeignKey("content_type", "object_id")
    verifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="items_appareillage_verifies", verbose_name="Vérifié par",
    )
    verifie_le = models.DateTimeField(null=True, blank=True, verbose_name="Vérifié le")

    class Meta:
        ordering = ["categorie", "libelle"]
        verbose_name = "Item de session d'appareillage"
        verbose_name_plural = "Items de session d'appareillage"

    def __str__(self):
        return self.libelle

    @property
    def est_verifie(self):
        return self.verifie_par_id is not None
