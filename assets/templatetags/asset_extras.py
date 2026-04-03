import os
from django import template

register = template.Library()

@register.filter
def basename(value: str) -> str:
    try:
        return os.path.basename(value or "")
    except Exception:
        return value or ""
