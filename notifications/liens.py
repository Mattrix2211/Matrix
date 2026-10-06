"""Lien direct d'une notification vers l'objet concerné, seulement si le
marin y a accès (périmètre). Aucun lien n'est produit vers un objet interdit."""
import uuid

from django.urls import reverse


def liens_accessibles(request, notifications):
    """Renvoie {id de notification: URL} pour les notifications qui ont une
    cible connue et accessible. Les accès sont vérifiés en une requête par type."""
    liens = {}
    installations = {}
    for notification in notifications:
        modele = notification.content_type.model if notification.content_type_id else None
        if modele == "installation" and notification.object_id:
            installations[notification.pk] = notification.object_id
        elif notification.verb.startswith("Ma journée"):
            # Digest quotidien : pas d'objet unique, on renvoie vers le calendrier
            liens[notification.pk] = reverse("calendar-index")
    if installations:
        # Même périmètre que la fiche installation
        from assets.web_views import InstallationDetailView

        vue = InstallationDetailView()
        vue.request = request
        identifiants = {str(i) for i in vue.get_queryset().filter(
            pk__in=_uuids(installations.values())).values_list("pk", flat=True)}
        for pk_notification, objet in installations.items():
            if objet in identifiants:
                liens[pk_notification] = reverse("installation-detail", args=[objet])
    return liens


def _uuids(valeurs):
    """Ne garde que les identifiants bien formés (object_id est un texte libre)."""
    retenus = []
    for valeur in valeurs:
        try:
            retenus.append(uuid.UUID(valeur))
        except ValueError:
            pass
    return retenus
