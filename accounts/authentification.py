"""Connexion surveillée : verrouillage après des essais répétés et expiration du mot de passe provisoire (AC-12).

Le compteur est en base (`EchecConnexion`) : il vaut pour tous les processus du serveur et survit à un redémarrage, sans service
externe. Un identifiant verrouillé est refusé même avec le bon mot de passe jusqu'à la fin du délai ; un succès remet le
compteur à zéro. Risque accepté : quiconque connaît un identifiant peut le verrouiller pour la durée du délai.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.db import transaction
from django.utils import timezone

from .models import EchecConnexion


def _cle(identifiant):
    return (identifiant or "").lower()[:150]


def _fenetre():
    return timedelta(minutes=settings.VERROUILLAGE_CONNEXION_MINUTES)


def est_verrouille(identifiant):
    echec = EchecConnexion.objects.filter(identifiant=_cle(identifiant)).first()
    return bool(echec and echec.essais >= settings.TENTATIVES_CONNEXION_MAX and timezone.now() - echec.debut <= _fenetre())


def enregistrer_echec(identifiant):
    maintenant = timezone.now()
    with transaction.atomic():
        echec, _ = EchecConnexion.objects.select_for_update().get_or_create(
            identifiant=_cle(identifiant), defaults={"essais": 0, "debut": maintenant})
        if maintenant - echec.debut > _fenetre():
            echec.essais, echec.debut = 0, maintenant
        echec.essais += 1
        echec.save(update_fields=["essais", "debut"])


def effacer_echecs(identifiant):
    EchecConnexion.objects.filter(identifiant=_cle(identifiant)).delete()


class ConnexionSurveilleeBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("username")
        if est_verrouille(username):
            return None
        utilisateur = super().authenticate(request, username=username, password=password, **kwargs)
        if utilisateur is None:
            if username:
                enregistrer_echec(username)
            return None
        profil = getattr(utilisateur, "profile", None)
        if profil and profil.mot_de_passe_provisoire and profil.mot_de_passe_provisoire_expire_le \
                and profil.mot_de_passe_provisoire_expire_le < timezone.now():
            return None
        effacer_echecs(username)
        return utilisateur
