"""Contexte « bâtiment » de la barre supérieure (docs/UX.md §8).

Un utilisateur de bord a un bâtiment fixe (son rattachement). Un utilisateur à
terre qui suit plusieurs bâtiments peut choisir celui qu'il consulte ; le choix
est mémorisé dans la SESSION (et non dans le profil : il s'efface à la
déconnexion, ce qui convient aux postes partagés, et ne modifie jamais le
rattachement du marin).

Périmètre des bâtiments, avec les règles déjà utilisées par les tableaux de
bord (``dashboard.web_views``), sans système parallèle :
- administrateur général (``is_master_admin``) et responsable de spécialité
  (``accounts.ResponsableSpecialite``, toute la flotte) : tous les bâtiments ;
- responsable de classe (``org.ResponsableClasseNavire``) : les bâtiments de
  ses classes ;
- dans tous les cas, le bâtiment de rattachement du profil.
Tout autre utilisateur n'a que son bâtiment de rattachement (même périmètre
« navire » que ``scope_filters_for_user``).

À ce jour, ce choix n'est lu que par la barre supérieure : aucune vue métier ne
filtre encore sur ``batiment_courant`` (voir la tâche de suite dans Notion).
"""
from org.models import Ship
from matrix.core.scopes import is_master_admin
from training.models import navire_de

CLE_SESSION = "batiment_courant_id"


def batiments_du_perimetre(user):
    """Bâtiments (unités non archivées) que l'utilisateur a le droit de consulter."""
    if not getattr(user, "is_authenticated", False):
        return Ship.objects.none()
    actives = Ship.objects.filter(archived=False)
    if is_master_admin(user) or user.specialites_dont_il_est_responsable.exists():
        return actives.order_by("name")
    rattachement = navire_de(user)
    filtre = Ship.objects.filter(pk=rattachement.pk) if rattachement else Ship.objects.none()
    classes = list(user.classes_navire_dont_il_est_responsable.values_list("classe_navire", flat=True))
    if classes:
        filtre = actives.filter(classe_navire__in=classes) | filtre
    return filtre.filter(archived=False).distinct().order_by("name")


def selecteur_batiment(user):
    """Liste des bâtiments proposés si l'utilisateur en suit plusieurs, sinon []."""
    batiments = list(batiments_du_perimetre(user))
    return batiments if len(batiments) > 1 else []


def batiment_courant(request, batiments=None):
    """Bâtiment courant : choix mémorisé en session s'il est toujours dans le
    périmètre, sinon bâtiment de rattachement, sinon None. Le périmètre est
    revalidé à chaque appel : jamais de confiance à la session seule."""
    user = request.user
    if batiments is None:
        batiments = selecteur_batiment(user)
    if batiments:
        choisi = request.session.get(CLE_SESSION)
        for batiment in batiments:
            if batiment.pk == choisi:
                return batiment
    return navire_de(user)
