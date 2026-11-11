"""Suppression des unités (bâtiment, service, secteur, section) : jamais tant qu'un objet les référence.

Une unité n'est supprimable que si plus rien (marins, matériel, listes, annonces, documents, fiches, désignations, journaux…) ne la
référence, hors sous-unités elles-mêmes sans référence. Sinon : archivage (org/archivage.py), qui conserve tout. Les relations vers
les unités sont en PROTECT (Django refuse donc aussi toute suppression directe) ; ce module donne le détail, la trace et les messages.
"""
from collections import Counter

from django.db import transaction
from django.db.models import PROTECT, ProtectedError

from .archivage import libelle_type

_NOMS = {"accounts.userprofile": "profils de marins"}  # libellés que Django laisse en anglais
_ENFANTS = {"Ship": "services", "Service": "sectors", "Sector": "sections"}


class SuppressionRefusee(Exception):
    """Suppression refusée : `comptes` donne, par type d'objet, le nombre de références restantes."""

    def __init__(self, unite, comptes):
        self.unite, self.comptes = unite, comptes
        detail = ", ".join(f"{nombre} {nom}" for nom, nombre in comptes.items())
        super().__init__(f"Impossible de supprimer ce {libelle_type(unite)} : il est encore référencé par {detail}. "
                         "Archivez-le (rien n'est perdu) ou réaffectez d'abord son contenu.")


def _arbre(unite):
    yield unite
    nom_enfants = _ENFANTS.get(unite.__class__.__name__)
    for enfant in (getattr(unite, nom_enfants).all() if nom_enfants else ()):
        yield from _arbre(enfant)


def dependances(unite):
    """Références restantes vers l'unité et ses sous-unités : Counter {type d'objet: nombre}. Vide = supprimable."""
    comptes = Counter()
    for u in _arbre(unite):
        for relation in u._meta.related_objects:
            if relation.many_to_many:
                nombre = getattr(u, relation.get_accessor_name()).count()
            elif relation.on_delete is PROTECT:
                nombre = relation.related_model._base_manager.filter(**{relation.field.name: u}).count()
            else:
                continue  # sous-unités (supprimées avec leur parent, vides) et simples liens sans donnée
            if nombre:
                comptes[_NOMS.get(relation.related_model._meta.label_lower, str(relation.related_model._meta.verbose_name_plural))] += nombre
    return comptes


def _tracer(auteur, action, unite, complement=""):
    from accounts.models import AuditLog

    AuditLog.objects.create(actor=auteur, action=action, details=f"{libelle_type(unite)} pk={unite.pk}; nom={unite}{complement}")


def verifier_suppression(unite, auteur):
    """Lève SuppressionRefusee (et trace la tentative) si l'unité est encore référencée."""
    comptes = dependances(unite)
    if comptes:
        _tracer(auteur, "suppression_unite_refusee", unite, f"; références: {dict(comptes)}")
        raise SuppressionRefusee(unite, comptes)


def supprimer(unite, auteur):
    """Supprime une unité sans aucune référence (avec ses sous-unités vides) ; trace la suppression."""
    verifier_suppression(unite, auteur)
    type_unite = unite.__class__.__name__.lower()
    pk, nom = unite.pk, str(unite)
    sous_unites = sum(1 for _ in _arbre(unite)) - 1
    try:
        with transaction.atomic():
            unite.delete()
    except ProtectedError as erreur:  # quelque chose a été rattaché entre le contrôle et la suppression
        raise SuppressionRefusee(unite, Counter({"autres objets": len(erreur.protected_objects)})) from erreur
    from accounts.models import AuditLog

    AuditLog.objects.create(actor=auteur, action=f"delete_{type_unite}",
                            details=f"pk={pk}; nom={nom}; sous-unités vides supprimées: {sous_unites}")
