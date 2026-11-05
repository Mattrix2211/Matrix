from django.apps import apps
tot={m._meta.label:m.objects.count() for m in apps.get_models() if m._meta.app_label not in ("contenttypes","sessions","admin","auth") or m._meta.label=="auth.User"}
import json; print("CNT",json.dumps({k:v for k,v in tot.items() if v},sort_keys=True))
from django.contrib.auth.models import User; print("PWD",sum(1 for u in User.objects.all() if u.check_password('pass')),"/",User.objects.count())
