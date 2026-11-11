"""Archivage des unités (bâtiment, service, secteur, section) : règle unique.

Une unité est ACTIVE si elle et tous ses ancêtres ne sont pas archivés. Archiver ne supprime rien : l'historique (listes,
annonces, documents, tâches) reste lisible et le rattachement des marins n'est jamais modifié. Une unité archivée n'est plus
proposée ni acceptée pour de NOUVEAUX rattachements ; archiver une unité qui porte encore des marins actifs ou du matériel est refusé.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q


def parent(unite):
    """Unité parente, ou None pour un bâtiment."""
    nom = unite.__class__.__name__
    return {"Service": getattr(unite, "ship", None), "Sector": getattr(unite, "service", None),
            "Section": getattr(unite, "sector", None)}.get(nom)


def navire_de(unite):
    """Bâtiment auquel appartient l'unité."""
    return list(ancetres_et_soi(unite))[-1]


def ancetres_et_soi(unite):
    while unite is not None:
        yield unite
        unite = parent(unite)


def est_active(unite):
    return not any(u.archived for u in ancetres_et_soi(unite))


def libelle_type(unite):
    return {"Ship": "bâtiment", "Service": "service", "Sector": "secteur", "Section": "section"}[unite.__class__.__name__]


_CHEMINS = {  # chemins du profil d'un marin vers chaque niveau, par type d'unité
    "Ship": ("profile__ship", "profile__service__ship", "profile__sector__service__ship", "profile__section__sector__service__ship"),
    "Service": ("profile__service", "profile__sector__service", "profile__section__sector__service"),
    "Sector": ("profile__sector", "profile__section__sector"),
    "Section": ("profile__section",),
}
_CHAMP_MATERIEL = {"Ship": "ship", "Service": "service", "Sector": "sector", "Section": "section"}


def marins_actifs(unite, actifs=True):
    """Comptes (actifs par défaut) rattachés à l'unité ou à l'une de ses sous-unités."""
    filtre = Q()
    for chemin in _CHEMINS[unite.__class__.__name__]:
        filtre |= Q(**{chemin: unite})
    comptes = get_user_model().objects.filter(filtre).distinct()
    return comptes.filter(is_active=True) if actifs else comptes


def obstacles(unite):
    """Éléments qui empêchent l'archivage (libellés avec effectifs)."""
    from assets.models import Asset, Installation

    champ = _CHAMP_MATERIEL[unite.__class__.__name__]
    trouves = []
    for libelle, nombre in (("marin(s) actif(s)", marins_actifs(unite).count()),
                            ("installation(s)", Installation.objects.filter(**{champ: unite}).count()),
                            ("matériel(s)", Asset.objects.filter(**{champ: unite}).count())):
        if nombre:
            trouves.append(f"{nombre} {libelle}")
    return trouves


def exclure_archives(queryset, garder_occupees=False):
    """Restreint à des unités actives. `garder_occupees` : garde aussi une unité archivée à laquelle un compte (même désactivé) est
    encore rattaché (données antérieures à la règle), pour que sa fiche reste modifiable sans perdre son rattachement."""
    nom = queryset.model.__name__
    ancetres = {"Ship": (), "Service": ("ship",), "Sector": ("service", "service__ship"),
                "Section": ("sector", "sector__service", "sector__service__ship")}[nom]
    actives = Q(archived=False)
    for chemin in ancetres:
        actives &= Q(**{f"{chemin}__archived": False})
    if not garder_occupees:
        return queryset.filter(actives)
    occupees = [u.pk for u in queryset.exclude(actives) if marins_actifs(u, actifs=False).exists()]
    return queryset.filter(actives | Q(pk__in=occupees))


def erreur_changement(unite, archived_voulu, avant=None):
    """Message d'erreur (chaîne vide si le changement est permis) pour une unité qui devient/reste `archived_voulu`.

    `avant` : état enregistré (None pour une création). Seuls les CHANGEMENTS sont contrôlés : modifier une unité déjà archivée
    reste possible."""
    archivee_avant = bool(avant and avant.archived)
    mere = parent(unite)
    if avant is None and mere is not None and not est_active(mere):
        return f"Impossible de créer ce {libelle_type(unite)} dans une unité archivée."
    if avant is not None and mere is not None and parent(avant).pk != mere.pk and not est_active(mere):
        return f"Impossible de déplacer ce {libelle_type(unite)} vers une unité archivée."
    if archived_voulu and not archivee_avant and unite.pk:
        trouves = obstacles(unite)
        if trouves:
            return (f"Impossible d'archiver ce {libelle_type(unite)} : il porte encore {', '.join(trouves)}. "
                    "Affectez-les d'abord ailleurs.")
    if not archived_voulu and archivee_avant and parent(unite) is not None and not est_active(parent(unite)):
        return f"Impossible de réactiver ce {libelle_type(unite)} : son unité parente est archivée. Réactivez-la d'abord."
    return ""


def verifier_modele(unite):
    """Contrôle appelé par `clean()` des modèles (administration) et par les API : lève ValidationError."""
    avant = type(unite).objects.filter(pk=unite.pk).first() if unite.pk else None
    message = erreur_changement(unite, unite.archived, avant)
    if message:
        raise ValidationError({"archived": message} if (avant is not None or unite.archived) else message)


def _changer(unite, auteur, archived):
    from accounts.models import AuditLog

    avant = type(unite).objects.get(pk=unite.pk)
    if avant.archived == archived:
        return False  # idempotent : aucun changement, aucune trace
    message = erreur_changement(unite, archived, avant)
    if message:
        raise ValidationError(message)
    unite.archived = archived
    unite.save(update_fields=["archived", "updated_at"])
    AuditLog.objects.create(actor=auteur, action=f"{'archive' if archived else 'reactive'}_{unite.__class__.__name__.lower()}",
                            details=f"pk={unite.pk}; nom={unite}; archived: {avant.archived} -> {archived}")
    return True


def archiver(unite, auteur):
    """Archive l'unité (refusé si elle porte des marins actifs ou du matériel). Retourne False si elle l'était déjà."""
    return _changer(unite, auteur, True)


def reactiver(unite, auteur):
    """Réactive l'unité (refusé si son parent est archivé). Retourne False si elle était déjà active."""
    return _changer(unite, auteur, False)


def verifier_rattachement(objet, champs=("ship", "service", "sector", "section")):
    """Un objet (matériel, installation) ne peut pas être NOUVELLEMENT rattaché à une unité archivée.

    Une valeur inchangée reste acceptée, pour que l'objet reste modifiable."""
    avant = type(objet).objects.filter(pk=objet.pk).first() if objet.pk else None
    erreurs = {}
    for champ in champs:
        unite = getattr(objet, champ, None)
        if unite is None or est_active(unite):
            continue
        if avant is not None and getattr(avant, f"{champ}_id") == unite.pk:
            continue
        erreurs[champ] = f"Ce {libelle_type(unite)} est archivé : il ne peut plus recevoir de nouveau rattachement."
    if erreurs:
        raise ValidationError(erreurs)
