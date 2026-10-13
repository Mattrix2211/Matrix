from django import template

from documentation.services import documents_associes, documents_liables, peut_gerer_liens

register = template.Library()


@register.inclusion_tag("documentation/_associes.html", takes_context=True)
def documents_associes_a(context, objet):
    """Documents applicables liés à l'objet de la page, lisibles par le marin connecté."""
    request = context.get("request")
    if request is None or not getattr(request.user, "is_authenticated", False) or objet is None:
        return {"documents": []}
    associes = documents_associes(request.user, objet)
    gere = peut_gerer_liens(request.user)
    return {
        "documents": list(associes.prefetch_related("versions")), "request": request, "csrf_token": context.get("csrf_token"),
        "peut_lier": gere, "reference": f"{objet._meta.model_name}:{objet.pk}",
        "candidats": documents_liables(request.user, objet) if gere else [],
    }
