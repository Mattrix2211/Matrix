from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from quarts.models import CreneauServiceGarde as G, CreneauQuart as Q, EchangeService as E
c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="cdt_a")); cible=User.objects.get(username="equipier_a")
with transaction.atomic():
    t0=(G.objects.count(),Q.objects.count(),E.objects.count(),G.objects.filter(marin__isnull=True).count()+Q.objects.filter(marin__isnull=True).count())
    c.post("/users/",{"action":"delete_user","pk":cible.pk},HTTP_HOST="localhost")
    t1=(G.objects.count(),Q.objects.count(),E.objects.count(),G.objects.filter(marin__isnull=True).count()+Q.objects.filter(marin__isnull=True).count())
    print("SU2 créneaux de garde / de quart / échanges / créneaux sans titulaire :",t0,"→",t1); transaction.set_rollback(True)
