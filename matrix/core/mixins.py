import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .roles import NIVEAU_VISION_COMMANDEMENT, user_role_level
from .scopes import is_master_admin, perimetre_hierarchique_q, perimetre_navire_q, scope_filters_for_user, ship_id_for_user

logger = logging.getLogger(__name__)


def build_scope_q(user, *lookup_paths):
    """Traduit le périmètre (ship_id/service_id/sector_id/section_id) de
    l'utilisateur en objet Q, à travers une ou plusieurs chaînes de relations
    Django, combinées en OU (utile quand un modèle peut être rattaché de
    plusieurs façons différentes selon son type, ex. MaintenanceOccurrence
    via un matériel mobile OU une installation fixe).

    Chaque élément de `lookup_paths` est soit :
    - une chaîne de préfixe (ex. "asset__"), appliquée telle quelle à la clé
      de périmètre — à utiliser quand la relation cible porte elle-même les
      4 champs directs (ship/service/sector/section), comme Asset ou
      Installation ;
    - un dict {"ship_id": "chemin__ship_id", ...} pour les relations qui ne
      couvrent pas les 4 niveaux (ex. un type d'actif n'est jamais rattaché
      à une section précise).

    Sans rattachement, un MASTER_ADMIN (ou superutilisateur) obtient Q()
    (flotte entière) ; un utilisateur à terre est borné aux bâtiments qu'il
    suit (batiments_du_perimetre) ; tout autre n'obtient aucun résultat.

    Si un périmètre est défini mais qu'aucun des chemins fournis ne le
    couvre, renvoie un Q qui n'égale jamais rien : mieux vaut ne rien
    montrer que de renvoyer une donnée hors périmètre.
    """
    filters = scope_filters_for_user(user)
    suffixe = ""
    if not filters:
        # Import différé : contexte_batiment importe scopes (cycle).
        from .contexte_batiment import batiment_filtre, batiments_du_perimetre
        courant = batiment_filtre.get()
        if is_master_admin(user):
            if courant is None:
                return Q()
            filters = {"ship_id": courant}
        else:
            ids = list(batiments_du_perimetre(user).values_list("pk", flat=True))
            if not ids:
                return Q(pk__in=[])
            filters = {"ship_id": [courant] if courant in ids else ids}
            suffixe = "__in"
    (key, value), = filters.items()
    q = Q()
    matched = False
    for path in lookup_paths:
        lookup = path.get(key) if isinstance(path, dict) else f"{path}{key}"
        if not lookup:
            continue
        q |= Q(**{lookup + suffixe: value})
        matched = True
    return q if matched else Q(pk__in=[])


def utilisateurs_visibles_par(user):
    """Comptes utilisateurs que `user` peut lire ou désigner (assignation) :
    flotte entière pour un MASTER_ADMIN ; tout le navire pour un COMMANDANT, son second ou
    ADMIN_NAVIRE ; sinon son périmètre hiérarchique. Sans périmètre : personne.
    User ne porte pas le périmètre, son profil si : préfixe "profile__"."""
    User = get_user_model()
    if is_master_admin(user):
        return User.objects.all()
    # Un commandement à terre sans navire retombe sur les bâtiments qu'il suit (build_scope_q).
    if user_role_level(user) >= NIVEAU_VISION_COMMANDEMENT and ship_id_for_user(user):
        return User.objects.filter(perimetre_navire_q(user, "profile__"))
    # Un chef de service voit aussi les marins de ses secteurs ; le niveau « navire » reste réservé au commandement.
    niveau = user.profile.scope[0] if getattr(user, "profile", None) else None
    perimetre = perimetre_hierarchique_q(user, "profile__") if niveau in ("service", "sector", "section") else None
    return User.objects.filter(perimetre if perimetre is not None else build_scope_q(user, "profile__"))


class SuppressionInterditeMixin:
    """Retire la méthode DELETE d'un ViewSet DRF (retourne 405 avant même la
    vérification des permissions) : à réutiliser sur toute ressource dont
    l'historique ne doit jamais pouvoir disparaître, parce que son cycle de
    statuts et/ou sa signature de validation font foi (ex. CorrectiveTicket,
    MaintenanceOccurrence/MaintenanceExecution). Sans ce garde-fou, un
    ModelViewSet standard expose une suppression complète de l'objet à tout
    rôle satisfaisant le seuil d'écriture générique, ce qui contourne
    silencieusement tout le cycle de vie métier (cf. tâche Notion « Matrice
    de tests de permissions », refus du Tech Lead sur CorrectiveTicketViewSet
    initialement enregistré sans cette restriction).
    """

    http_method_names = ["get", "post", "put", "patch", "head", "options", "trace"]


class ScopedQuerySetMixin:
    """Filtre le queryset d'un ViewSet DRF selon le périmètre (navire/
    service/secteur/section) de l'utilisateur connecté.

    Comportement par défaut : le périmètre renvoyé par
    scope_filters_for_user() est appliqué directement sur les champs
    ship_id/service_id/sector_id/section_id du modèle exposé.

    Si le modèle n'a pas ces champs directement (parce qu'il concerne un
    objet rattaché à un équipement, lui-même rattaché à un navire), le
    ViewSet DOIT surcharger get_scoped_filters() pour renvoyer un objet Q
    traduisant le périmètre via la bonne chaîne de relations — voir
    build_scope_q() ci-dessus et les exemples dans maintenance/views.py et
    logistics/views.py.

    Si aucun filtre ne peut être appliqué (modèle sans champ direct ET
    ViewSet non surchargé), on refuse de renvoyer un queryset non filtré :
    mieux vaut une erreur bruyante en développement qu'une fuite de données
    entre navires en production.
    """

    scope_fields_order = ["ship_id", "service_id", "sector_id", "section_id"]

    def get_scoped_filters(self):
        return scope_filters_for_user(self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        filters = self.get_scoped_filters()

        # Un ViewSet peut surcharger get_scoped_filters() pour renvoyer
        # directement un objet Q traduisant le périmètre via une relation.
        if isinstance(filters, Q):
            return qs.filter(filters)

        if not filters:
            # Sans rattachement : flotte entière pour un MASTER_ADMIN, bâtiments suivis pour un
            # utilisateur à terre (comme build_scope_q), rien pour les autres.
            if is_master_admin(self.request.user):
                return qs
            if hasattr(qs.model, "ship"):
                return qs.filter(build_scope_q(self.request.user, ""))
            return qs.none()

        # Ne garder que les filtres correspondant à un champ direct du modèle
        applicable = {k: v for k, v in filters.items() if hasattr(qs.model, k.replace("_id", ""))}
        if applicable:
            return qs.filter(**applicable)

        # Le modèle n'a pas de champ de périmètre direct et le ViewSet n'a pas
        # surchargé get_scoped_filters() pour traduire le filtre via une
        # relation : on refuse de renvoyer un queryset non filtré plutôt que
        # de risquer d'exposer la flotte entière à tout utilisateur.
        logger.error(
            "ScopedQuerySetMixin : aucun filtre de périmètre applicable sur %s pour "
            "l'utilisateur %s — le modèle n'a pas de champ ship/service/sector/section "
            "direct. Surchargez get_scoped_filters() dans ce ViewSet (cf. build_scope_q).",
            qs.model.__name__,
            getattr(self.request.user, "pk", None),
        )
        raise ImproperlyConfigured(
            f"ScopedQuerySetMixin : le modèle {qs.model.__name__} n'a pas de champ de "
            "périmètre direct et son ViewSet ne surcharge pas get_scoped_filters(). "
            "Voir matrix/core/mixins.py::build_scope_q."
        )


class EcritureDansLePerimetreMixin:
    """À combiner avec ScopedQuerySetMixin : une création ou une modification
    qui rattacherait l'objet hors du périmètre de l'appelant (clé étrangère
    choisie dans le payload) est refusée en 400 et annulée.

    Les champs posés par le serveur (demandeur, auteur...) se déclarent dans
    champs_serveur_creation() / champs_serveur_modification().

    `champs_utilisateurs_perimetre` liste les champs (clé étrangère ou
    plusieurs-à-plusieurs vers User) dont les comptes désignés doivent
    appartenir au périmètre de l'appelant (assignation)."""

    champs_utilisateurs_perimetre = ()

    def champs_serveur_creation(self):
        return {}

    def champs_serveur_modification(self):
        return {}

    def _verifier_utilisateurs(self, serializer):
        for champ in self.champs_utilisateurs_perimetre:
            valeur = serializer.validated_data.get(champ)
            if not valeur:
                continue
            ids = {u.pk for u in (valeur if isinstance(valeur, (list, tuple)) else [valeur])}
            autorises = set(utilisateurs_visibles_par(self.request.user).filter(pk__in=ids).values_list("pk", flat=True))
            if ids - autorises:
                raise ValidationError({champ: "Utilisateur hors de votre périmètre."})

    def _enregistrer_dans_le_perimetre(self, serializer, **champs):
        self._verifier_utilisateurs(serializer)
        with transaction.atomic():
            objet = serializer.save(**champs)
            if not self.get_queryset().filter(pk=objet.pk).exists():
                raise ValidationError("Objet de rattachement hors de votre périmètre.")

    def perform_create(self, serializer):
        self._enregistrer_dans_le_perimetre(serializer, **self.champs_serveur_creation())

    def perform_update(self, serializer):
        self._enregistrer_dans_le_perimetre(serializer, **self.champs_serveur_modification())


class EcritureTraceeMixin:
    """À placer en tête des bases d'un ViewSet : chaque création, modification et
    suppression est inscrite à l'AuditLog (`<domaine_audit>.creation|modification|suppression`),
    avec les champs changés (avant -> après) ou, pour une suppression, les marins rattachés."""

    domaine_audit = ""

    def _tracer(self, verbe, objet, complement=""):
        from accounts.models import AuditLog
        AuditLog.objects.create(
            actor=self.request.user, action=f"{self.domaine_audit}.{verbe}",
            details=f"{objet._meta.verbose_name} « {objet} » ({objet.pk}){complement}"[:2000],
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            super().perform_create(serializer)
            self._tracer("creation", serializer.instance)

    def perform_update(self, serializer):
        instance = serializer.instance
        champs = {f.name for f in instance._meta.concrete_fields}
        changes = [
            f"{champ}: {getattr(instance, champ)} -> {valeur}"
            for champ, valeur in serializer.validated_data.items()
            if champ in champs and getattr(instance, champ) != valeur
        ]
        with transaction.atomic():
            super().perform_update(serializer)
            self._tracer("modification", serializer.instance, f" ; {' ; '.join(changes)}" if changes else "")

    def perform_destroy(self, instance):
        profils = getattr(instance, "profiles", None)
        complement = f" ; marins rattachés: {profils.count()}" if profils is not None else ""
        with transaction.atomic():
            self._tracer("suppression", instance, complement)
            super().perform_destroy(instance)
