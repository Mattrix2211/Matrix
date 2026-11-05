from django.test import Client
from django.contrib.auth.models import User
from assets.models import Installation
i=Installation.objects.first(); c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="equipier_a"))
r=c.get(f"/scan/{i.pk}/",HTTP_HOST="localhost"); print("QR scan",r.status_code,r.headers.get("Location"))
from django.apps import apps
print("ARCH champs 'archiv' :",[f"{m._meta.label}.{f.name}" for m in apps.get_models() for f in m._meta.fields if "archiv" in f.name or f.name in ("actif","active","desactive")][:30])
