from django.apps import apps
from org.models import Service, Sector, Section, Ship
import collections
for cible in (Section, Sector, Service, Ship):
    c=collections.defaultdict(list)
    for m in apps.get_models():
        for f in m._meta.get_fields():
            if f.many_to_one and f.related_model is cible and hasattr(f,"remote_field") and f.remote_field.on_delete:
                c[f.remote_field.on_delete.__name__].append(f"{m._meta.app_label}.{m.__name__}.{f.name}")
    print("FK",cible.__name__,{k:len(v) for k,v in c.items()})
    for k in ("CASCADE","SET_NULL"):
        if c.get(k): print("FK   ",k,", ".join(c[k][:14]))
