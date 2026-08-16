import logging

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q

from .scopes import scope_filters_for_user

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

    Si l'utilisateur n'a pas de périmètre défini (ex. administrateur
    général sans navire attribué), renvoie Q() : aucun filtre, comportement
    volontaire identique à scope_filters_for_user().

    Si un périmètre est défini mais qu'aucun des chemins fournis ne le
    couvre, renvoie un Q qui n'égale jamais rien : mieux vaut ne rien
    montrer que de renvoyer une donnée hors périmètre.
    """
    filters = scope_filters_for_user(user)
    if not filters:
        return Q()
    (key, value), = filters.items()
    q = Q()
    matched = False
    for path in lookup_paths:
        lookup = path.get(key) if isinstance(path, dict) else f"{path}{key}"
        if not lookup:
            continue
        q |= Q(**{lookup: value})
        matched = True
    return q if matched else Q(pk__in=[])


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
            # Utilisateur sans périmètre défini (ex. administrateur général) :
            # aucun filtre à appliquer, comportement volontaire de
            # scope_filters_for_user().
            return qs

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
