from rest_framework.permissions import BasePermission, SAFE_METHODS

from matrix.core.scopes import is_master_admin


def peut_gerer_catalogue(user, specialite):
    """Vrai si l'utilisateur peut écrire dans le catalogue de cette spécialité :
    MASTER_ADMIN, ou responsable désigné de la spécialité (accounts.ResponsableSpecialite)."""
    if not getattr(user, "is_authenticated", False):
        return False
    if is_master_admin(user):
        return True
    if specialite is None:
        return False
    specialite_id = getattr(specialite, "pk", specialite)
    return user.specialites_dont_il_est_responsable.filter(specialite_id=specialite_id).exists()


class CataloguePermission(BasePermission):
    """Lecture ouverte à tout utilisateur connecté (catalogue commun à la flotte) ;
    écriture limitée aux responsables de la spécialité de l'objet. La suppression
    est réservée à MASTER_ADMIN : un responsable archive (actif=False)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        # Spécialité cible vérifiée dans le serializer (création) et sur l'objet (modification).
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return is_master_admin(request.user)
        return peut_gerer_catalogue(request.user, obj.specialite)
