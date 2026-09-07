from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework import viewsets, permissions
from .models import Thread, Message, Attachment
from .serializers import ThreadSerializer, MessageSerializer, AttachmentSerializer
from matrix.core.mixins import ScopedQuerySetMixin, build_scope_q
from matrix.core.permissions import IsAuthorOrReadOnly, RolePermission
from matrix.core.roles import RoleLevel
from matrix.core.scopes import scope_filters_for_user

class DefaultPermission(permissions.IsAuthenticated):
    pass


def _filtre_perimetre_threads(user, prefix=""):
    """Thread est générique (GenericForeignKey vers n'importe quel modèle,
    cf. threads/utils.py, threads/models.py) : il ne porte lui-même aucun
    champ de périmètre, ni de relation classique exploitable par
    build_scope_q. Avant cette correction, ThreadViewSet/MessageViewSet/
    AttachmentViewSet ne filtraient DU TOUT par périmètre : n'importe quel
    utilisateur authentifié pouvait lire, via l'API brute, les fils de
    discussion (et pièces jointes) de tickets correctifs ou d'occurrences de
    maintenance d'un AUTRE navire — alors que les pages web équivalentes
    (logistics/web_views.py, maintenance/web_views.py) ne les affichent
    qu'après avoir déjà vérifié le périmètre sur l'objet parent
    (threads/utils.py, docstring de module) — faille corrigée ici (audit
    sécurité scoping API, tâche Notion « Audit complet du scoping par
    périmètre »).

    On résout donc le périmètre en amont, pour chaque type d'objet
    EFFECTIVEMENT rattaché à un fil de discussion dans l'appli (ticket
    correctif, occurrence de maintenance) : un utilisateur scopé ne voit que
    les fils portant sur un objet de son périmètre. Un fil rattaché à un
    autre type de contenu (cas générique prévu par l'app mais non encore
    utilisé en pratique en dehors des tests, cf. threads/tests/
    test_permissions.py) reste invisible à un utilisateur scopé plutôt que
    montré sans contrôle : mieux vaut masquer que fuiter.

    `prefix` permet d'appliquer ce filtre à Message ("thread__") et
    Attachment ("message__thread__"), qui ne portent pas eux-mêmes le
    content_type/object_id mais y accèdent via leur fil.

    Si l'utilisateur n'a pas de périmètre défini (ex. administrateur
    général), renvoie None : aucun filtre à appliquer, même convention que
    scope_filters_for_user()."""
    if not scope_filters_for_user(user):
        return None
    # Import différé : évite tout risque de cycle d'import au chargement du
    # module (logistics/maintenance n'importent jamais threads.views).
    from logistics.models import CorrectiveTicket
    from maintenance.models import MaintenanceOccurrence

    ids_tickets = CorrectiveTicket.objects.filter(build_scope_q(user, "asset__")).values_list("pk", flat=True)
    ids_occurrences = MaintenanceOccurrence.objects.filter(
        build_scope_q(user, "asset__", "installation_maintenance__installation__")
    ).values_list("pk", flat=True)
    ct_ticket = ContentType.objects.get_for_model(CorrectiveTicket)
    ct_occurrence = ContentType.objects.get_for_model(MaintenanceOccurrence)
    return (
        Q(**{f"{prefix}content_type": ct_ticket, f"{prefix}object_id__in": [str(pk) for pk in ids_tickets]})
        | Q(**{f"{prefix}content_type": ct_occurrence, f"{prefix}object_id__in": [str(pk) for pk in ids_occurrences]})
    )


class ThreadViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Thread.objects.all()
    serializer_class = ThreadSerializer
    permission_classes = [RolePermission]
    # limiter l'écriture aux chefs de section et plus
    min_role_level_write = RoleLevel.CHEF_SECTION

    def get_scoped_filters(self):
        return _filtre_perimetre_threads(self.request.user)

class MessageViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Message.objects.select_related("thread", "author").all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def get_scoped_filters(self):
        return _filtre_perimetre_threads(self.request.user, prefix="thread__")

class AttachmentViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Attachment.objects.select_related("message").all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def get_scoped_filters(self):
        return _filtre_perimetre_threads(self.request.user, prefix="message__thread__")
