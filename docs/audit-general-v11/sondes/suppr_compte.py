from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from taches.models import Tache
from demandes.models import Demande
from accounts.models import AuditLog
from quarts.models import CreneauServiceGarde, CreneauQuart, FeuilleService
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
cible=User.objects.get(username="equipier_a")
for acteur in ("cdt_a","chef_service_a","admin_navire"):
    with transaction.atomic():
        t0=Tache.objects.count(); d0=Demande.objects.count(); a0=AuditLog.objects.filter(actor=cible).count(); cr0=CreneauQuart.objects.filter(marin=cible).count()+CreneauServiceGarde.objects.filter(marin=cible).count()
        r=cl(acteur).post("/users/",{"action":"delete_user","user_id":cible.pk,"pk":cible.pk},HTTP_HOST="localhost")
        print("SUP",acteur,"→",r.status_code,"| compte encore là:",User.objects.filter(pk=cible.pk).exists(),"| tâches",t0,"→",Tache.objects.count(),"| difficultés",d0,"→",Demande.objects.count(),"| lignes d'audit de ce compte",a0,"→",AuditLog.objects.filter(actor=cible).count(),"| actor NULL:",AuditLog.objects.filter(actor__isnull=True).count(),"| créneaux de quart/garde conservés:",CreneauQuart.objects.filter(marin_id=cible.pk).count()+CreneauServiceGarde.objects.filter(marin_id=cible.pk).count(),"/",cr0)
        transaction.set_rollback(True)
