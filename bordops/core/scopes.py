from typing import Dict, Any
from django.contrib.auth import get_user_model


def scope_filters_for_user(user) -> Dict[str, Any]:
    if not user.is_authenticated:
        return {}
    profile = getattr(user, "profile", None)
    if not profile:
        return {}
    level, obj_id = profile.scope
    if level == "ship":
        return {"ship_id": obj_id}
    if level == "service":
        return {"service_id": obj_id}
    if level == "sector":
        return {"sector_id": obj_id}
    if level == "section":
        return {"section_id": obj_id}
    return {}
