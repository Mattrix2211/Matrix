"""Destination du lien « Retour » : un parent logique de la page, jamais l'historique du navigateur."""
from django.utils.http import url_has_allowed_host_and_scheme


def destination_retour(request, defaut):
    """Adresse de l'écran d'origine passée en ``?retour=`` si elle est locale, sinon le parent logique ``defaut``.

    Seuls les chemins du site sont acceptés : une adresse externe ou un schéma exotique est ignoré.
    """
    demande = request.GET.get("retour", "")
    if demande.startswith("/") and not demande.startswith("//") and url_has_allowed_host_and_scheme(
        demande, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return demande
    return defaut
