"""Organisation en miroir des deux équipages d'un bâtiment à double équipage
(page Notion « Organigramme et rôles » §9 et §11) : les deux équipages ont la
même organisation (COMAEQ / COMOPS / COMANAV / COMAVIA, services, secteurs,
sections), chacun avec ses propres personnes.

`copier_organisation` est la brique unique de copie : elle sert à la duplication
d'un équipage vers l'autre (un clic sur la page « Équipages ») et à la
duplication d'un navire (matrix/settings_views.py). Les titulaires et les marins
ne sont jamais copiés. La copie est idempotente : un élément déjà présent chez la
destination (même sigle, même nom) est conservé, jamais écrasé."""
from django.contrib import messages

from accounts.models import AuditLog

from .models import CommandantAdjoint, Section, Sector, Service


def copier_organisation(navire_source, equipage_source, navire_cible, equipage_cible):
    """Copie l'organisation de (navire_source, equipage_source) vers
    (navire_cible, equipage_cible) ; un équipage None désigne l'organisation
    d'un navire à équipage unique. Renvoie le nombre d'éléments créés."""
    crees = {"postes": 0, "services": 0, "secteurs": 0, "sections": 0}
    correspondance_postes = {}
    for poste in CommandantAdjoint.objects.filter(ship=navire_source, equipage=equipage_source):
        copie, cree = CommandantAdjoint.objects.get_or_create(
            ship=navire_cible, equipage=equipage_cible, sigle=poste.sigle
        )
        correspondance_postes[poste.pk] = copie
        crees["postes"] += cree
    for service in Service.objects.filter(ship=navire_source, equipage=equipage_source).order_by("id"):
        nouveau_service, cree = Service.objects.get_or_create(
            ship=navire_cible, equipage=equipage_cible, name=service.name,
            defaults={"commandant_adjoint": correspondance_postes.get(service.commandant_adjoint_id)},
        )
        crees["services"] += cree
        for secteur in service.sectors.order_by("id"):
            nouveau_secteur, cree = Sector.objects.get_or_create(
                service=nouveau_service, name=secteur.name,
                defaults={"color": secteur.color, "equipage": equipage_cible},
            )
            crees["secteurs"] += cree
            for section in secteur.sections.order_by("id"):
                _, cree = Section.objects.get_or_create(
                    sector=nouveau_secteur, name=section.name, defaults={"equipage": equipage_cible}
                )
                crees["sections"] += cree
    return crees


def rattacher_organisation_existante(navire, equipage):
    """À l'activation du double équipage, l'organisation déjà en place (sans
    équipage) devient celle de l'équipage à bord : aucune donnée perdue."""
    for modele, filtre in (
        (CommandantAdjoint, {"ship": navire}),
        (Service, {"ship": navire}),
        (Sector, {"service__ship": navire}),
        (Section, {"sector__service__ship": navire}),
    ):
        modele.objects.filter(equipage__isnull=True, **filtre).update(equipage=equipage)


def dupliquer_vers_l_autre_equipage(request, navire):
    """Action « Dupliquer en miroir » : copie l'organisation de l'équipage source
    vers l'équipage destination du même bâtiment, et trace l'opération."""
    source = navire.equipages.filter(pk=request.POST.get("source_id") or 0).first()
    destination = navire.equipages.filter(pk=request.POST.get("destination_id") or 0).first()
    if source is None or destination is None or source == destination:
        messages.error(request, "Choisissez deux équipages différents de cette unité.")
        return
    crees = copier_organisation(navire, source, navire, destination)
    detail = (
        f"{source.nom} -> {destination.nom}; postes={crees['postes']}; services={crees['services']}; "
        f"secteurs={crees['secteurs']}; sections={crees['sections']}"
    )
    AuditLog.objects.create(
        actor=request.user, action="dupliquer_organisation_equipage", details=f"navire={navire.name}; {detail}"
    )
    total = sum(crees.values())
    if total:
        messages.success(
            request,
            f"Organisation de l'équipage {source.nom} dupliquée vers l'équipage {destination.nom} : "
            f"{crees['services']} service(s), {crees['secteurs']} secteur(s), {crees['sections']} section(s), "
            f"{crees['postes']} poste(s) COMA. Les titulaires sont à désigner.",
        )
    else:
        messages.info(request, f"L'équipage {destination.nom} a déjà toute l'organisation de l'équipage {source.nom}.")
