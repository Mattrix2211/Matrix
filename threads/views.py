from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Thread, Message, Attachment
from .serializers import ThreadSerializer, MessageSerializer, AttachmentSerializer
from matrix.core.mixins import EcritureDansLePerimetreMixin, ScopedQuerySetMixin
from matrix.core.permissions import IsAuthorOrReadOnly, RolePermission
from matrix.core.scopes import is_master_admin, scope_filters_for_user
from accounts.models import AuditLog
from logistics.perimetre import perimetre_tickets_q
from maintenance.perimetre import perimetre_occurrences_q

class DefaultPermission(permissions.IsAuthenticated):
    pass


def _filtre_perimetre_threads(user, prefix=""):
    """Filtre Q des fils visibles. Thread est générique (GenericForeignKey) : on résout le
    périmètre sur les types réellement discutés (tickets, occurrences) ; tout autre type
    reste masqué. `prefix` : « thread__ » pour Message, « message__thread__ » pour Attachment.

    Sans rattachement : None (aucun filtre) pour un MASTER_ADMIN ; un utilisateur à terre
    garde les fils des bâtiments qu'il suit (build_scope_q), les autres rien."""
    if not scope_filters_for_user(user) and is_master_admin(user):
        return None
    # Import différé : évite tout risque de cycle d'import au chargement du
    # module (logistics/maintenance n'importent jamais threads.views).
    from logistics.models import CorrectiveTicket
    from maintenance.models import MaintenanceOccurrence

    ids_tickets = CorrectiveTicket.objects.filter(perimetre_tickets_q(user)).values_list("pk", flat=True)
    ids_occurrences = MaintenanceOccurrence.objects.filter(perimetre_occurrences_q(user)).values_list("pk", flat=True)
    ct_ticket = ContentType.objects.get_for_model(CorrectiveTicket)
    ct_occurrence = ContentType.objects.get_for_model(MaintenanceOccurrence)
    return (
        Q(**{f"{prefix}content_type": ct_ticket, f"{prefix}object_id__in": [str(pk) for pk in ids_tickets]})
        | Q(**{f"{prefix}content_type": ct_occurrence, f"{prefix}object_id__in": [str(pk) for pk in ids_occurrences]})
    )


def _fil_dans_perimetre(user, thread):
    filtre = _filtre_perimetre_threads(user)
    return filtre is None or Thread.objects.filter(filtre, pk=thread.pk).exists()


class ThreadViewSet(EcritureDansLePerimetreMixin, ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Thread.objects.all()
    serializer_class = ThreadSerializer
    permission_classes = [RolePermission]
    # Seuil configurable par navire (matrix/core/role_thresholds.py) : limite
    # l'écriture aux chefs de section et plus, par défaut.
    role_threshold_action_write = "thread_ecriture"

    def get_scoped_filters(self):
        return _filtre_perimetre_threads(self.request.user)

    def perform_destroy(self, instance):
        # Suppression d'un fil de discussion entier (cascade sur tous ses
        # messages) : action sensible, tracée dans le journal transverse
        # AVANT suppression effective, pour conserver l'identifiant de
        # l'objet concerné — cf. tâche Notion « Unifier les modèles
        # d'historique/audit ».
        AuditLog.objects.create(
            actor=self.request.user, action="delete_thread",
            details=f"thread={instance.pk}; objet={instance.content_type}#{instance.object_id}",
        )
        super().perform_destroy(instance)

class MessageViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Message.objects.select_related("thread", "author").all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def get_scoped_filters(self):
        return _filtre_perimetre_threads(self.request.user, prefix="thread__")

    def perform_create(self, serializer):
        if not _fil_dans_perimetre(self.request.user, serializer.validated_data["thread"]):
            raise ValidationError({"thread": "Fil hors de votre périmètre."})
        serializer.save(author=self.request.user, created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        # Un message système est une trace automatique : jamais supprimable.
        if instance.is_system:
            raise PermissionDenied("Un message système ne peut pas être supprimé.")
        # Suppression d'un message d'une discussion : action sensible (un
        # message peut porter une décision ou une consigne), tracée dans le
        # journal transverse — cf. tâche Notion « Unifier les modèles
        # d'historique/audit ».
        AuditLog.objects.create(
            actor=self.request.user, action="delete_message",
            details=f"message={instance.pk}; thread={instance.thread_id}",
        )
        super().perform_destroy(instance)

class AttachmentViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Attachment.objects.select_related("message").all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def get_scoped_filters(self):
        return _filtre_perimetre_threads(self.request.user, prefix="message__thread__")

    def perform_create(self, serializer):
        message = serializer.validated_data["message"]
        if message.author_id != self.request.user.pk or not _fil_dans_perimetre(self.request.user, message.thread):
            raise ValidationError({"message": "Vous ne pouvez joindre un fichier qu'à votre propre message."})
        serializer.save(created_by=self.request.user)
