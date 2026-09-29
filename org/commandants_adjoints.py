"""Niveau « commandant adjoint » (COMAEQ / COMOPS / COMANAV / COMAVIA) de
l'organisation d'un navire : helper de résolution et actions de l'onglet
« Commandants adjoints » des Réglages (page Notion « Organigramme et rôles »
§2 et §11). Toute modification est tracée dans l'AuditLog unifié."""
from django.contrib import messages
from django.contrib.auth import get_user_model

from accounts.models import AuditLog
from matrix.core.scopes import ship_id_for_user

from .models import CommandantAdjoint, Service, Ship

User = get_user_model()

ACTIONS = (
    "toggle_capacite_aviation",
    "add_commandant_adjoint",
    "delete_commandant_adjoint",
    "set_titulaire_commandant_adjoint",
    "set_service_commandant_adjoint",
)


def commandant_adjoint_du_service(service):
    """Commandant adjoint dont dépend ce service, ou None si le service n'est
    rattaché à aucun (tolérance des services existants). Point d'entrée prévu
    pour le circuit de validation des fiches (chef de service PUIS commandant
    adjoint du service)."""
    return service.commandant_adjoint


def titulaires_possibles(ship):
    """Utilisateurs de rôle ETAT_MAJOR rattachés à ce navire."""
    return User.objects.filter(profile__role="ETAT_MAJOR", profile__ship=ship).order_by(
        "last_name", "first_name", "username"
    )


def contexte_onglet(ship):
    """Données affichées par l'onglet, pour le navire donné (ou None)."""
    if ship is None:
        return {"coma_ship": None}
    postes = list(ship.commandants_adjoints.select_related("titulaire", "equipage"))
    # Double équipage : un sigle reste ajoutable tant qu'un des équipages ne l'a pas.
    equipages = list(ship.equipages.all()) if ship.double_equipage else [None]
    sigles_pris = {
        p.sigle for p in postes
        if all(any(q.sigle == p.sigle and q.equipage == e for q in postes) for e in equipages)
    }
    return {
        "coma_ship": ship,
        "coma_postes": postes,
        "coma_equipages": equipages if ship.double_equipage else [],
        "coma_sigles_ajoutables": [
            (valeur, libelle, CommandantAdjoint.SIGNIFICATIONS[valeur])
            for valeur, libelle in CommandantAdjoint.Sigle.choices
            if valeur not in sigles_pris and (valeur != "COMAVIA" or ship.capacite_aviation)
        ],
        "coma_services": ship.services.select_related("commandant_adjoint", "equipage").order_by("name"),
        "coma_titulaires_possibles": titulaires_possibles(ship),
    }


def _navire_cible(request):
    if request.user.is_superuser:
        return Ship.objects.filter(pk=request.POST.get("ship_id")).first()
    return Ship.objects.filter(pk=ship_id_for_user(request.user)).first()


def _tracer(request, action, ship, detail):
    AuditLog.objects.create(actor=request.user, action=action, details=f"navire={ship.name}; {detail}")


def _poste_du_navire(ship, pk):
    return ship.commandants_adjoints.filter(pk=pk).first() if pk and pk.isdigit() else None


def traiter_action(request, action):
    """Exécute une action de l'onglet (déjà autorisée par la vue), limitée au
    navire de l'appelant (ou au navire choisi pour un superuser)."""
    ship = _navire_cible(request)
    if ship is None:
        messages.error(request, "Aucune unité sélectionnée.")
        return
    poste = None
    if action in ("delete_commandant_adjoint", "set_titulaire_commandant_adjoint"):
        poste = _poste_du_navire(ship, request.POST.get("pk"))
        if poste is None:
            messages.error(request, "Poste introuvable.")
            return

    if action == "toggle_capacite_aviation":
        if ship.capacite_aviation and ship.commandants_adjoints.filter(sigle="COMAVIA").exists():
            messages.error(request, "Supprimez d'abord le COMAVIA avant de retirer la capacité aviation.")
            return
        ship.capacite_aviation = not ship.capacite_aviation
        ship.save(update_fields=["capacite_aviation", "updated_at"])
        _tracer(request, action, ship, f"capacite_aviation={ship.capacite_aviation}")
        messages.success(
            request, f"Capacité aviation {'activée' if ship.capacite_aviation else 'désactivée'} pour {ship.name}."
        )
    elif action == "add_commandant_adjoint":
        sigle = request.POST.get("sigle")
        if sigle not in CommandantAdjoint.Sigle.values:
            messages.error(request, "Sigle inconnu.")
        elif sigle == "COMAVIA" and not ship.capacite_aviation:
            messages.error(request, "Le COMAVIA n'est possible que sur un bâtiment à capacité aviation.")
        else:
            equipage = ship.equipages.filter(pk=request.POST.get("equipage_id") or 0).first()
            if ship.double_equipage and equipage is None:
                messages.error(request, "Choisissez l'équipage du poste.")
                return
            _, cree = CommandantAdjoint.objects.get_or_create(ship=ship, sigle=sigle, equipage=equipage)
            if cree:
                _tracer(request, action, ship, f"sigle={sigle}" + (f"; equipage={equipage.nom}" if equipage else ""))
                messages.success(request, f"{sigle} ajouté.")
            else:
                messages.warning(request, f"Le {sigle} existe déjà sur cette unité.")
    elif action == "delete_commandant_adjoint":
        nb_services = poste.services.count()
        poste.delete()
        _tracer(request, action, ship, f"sigle={poste.sigle}; services_detaches={nb_services}")
        messages.success(request, f"{poste.sigle} supprimé ({nb_services} service(s) détaché(s)).")
    elif action == "set_titulaire_commandant_adjoint":
        user_id = request.POST.get("user_id")
        titulaire = None
        if user_id:
            titulaire = titulaires_possibles(ship).filter(pk=user_id if user_id.isdigit() else 0).first()
            if titulaire is None:
                messages.error(request, "Le titulaire doit être un membre de l'état-major de cette unité.")
                return
        if titulaire is not None and poste.equipage_id and titulaire.profile.equipage_id not in (None, poste.equipage_id):
            messages.error(request, f"Ce marin appartient à l'autre équipage : le {poste.sigle} doit être de l'équipage {poste.equipage.nom}.")
            return
        ancien = poste.titulaire.username if poste.titulaire else "aucun"
        poste.titulaire = titulaire
        poste.save(update_fields=["titulaire", "updated_at"])
        _tracer(request, action, ship, f"sigle={poste.sigle}; {ancien} -> {titulaire.username if titulaire else 'aucun'}")
        messages.success(request, f"Titulaire du {poste.sigle} mis à jour.")
    elif action == "set_service_commandant_adjoint":
        service = Service.objects.filter(pk=request.POST.get("service_id"), ship=ship).first()
        coma_id = request.POST.get("coma_id")
        coma = _poste_du_navire(ship, coma_id) if coma_id else None
        if service is None or (coma_id and coma is None):
            messages.error(request, "Service ou poste introuvable sur cette unité.")
            return
        if coma is not None and coma.equipage_id != service.equipage_id:
            messages.error(request, "Le service et le poste doivent appartenir au même équipage.")
            return
        ancien = service.commandant_adjoint.sigle if service.commandant_adjoint else "aucun"
        service.commandant_adjoint = coma
        service.save(update_fields=["commandant_adjoint", "updated_at"])
        _tracer(request, action, ship, f"service={service.name}; {ancien} -> {coma.sigle if coma else 'aucun'}")
        messages.success(request, f"Service « {service.name} » : rattachement mis à jour.")
