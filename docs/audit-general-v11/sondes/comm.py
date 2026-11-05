from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from notifications.models import Notification
from threads.models import Thread, Message
from annonces.models import Annonce
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def liste(c,url):
    r=c.get(url,HTTP_HOST="localhost"); 
    try: d=r.json()
    except Exception: return r.status_code,None
    d=d.get("results",d) if isinstance(d,dict) else d
    return r.status_code,len(d)
print("COM totaux: notifications",Notification.objects.count(),"threads",Thread.objects.count(),"messages",Message.objects.count(),"annonces",Annonce.objects.count())
for u in ("equipier_a","marin_b","cdt_a","terre_classe","marin_abe_1","admin"):
    c=cl(u); print("COM",u,"API notifications",liste(c,"/api/notifications/notifications/"),"| API threads",liste(c,"/api/threads/threads/"),"| messages",liste(c,"/api/threads/messages/"))
# notification d'autrui
n=Notification.objects.exclude(user__username="equipier_a").first(); c=cl("equipier_a")
with transaction.atomic():
    r1=c.post(f"/notifications/{n.pk}/lue/",HTTP_HOST="localhost"); n.refresh_from_db(); print("COM marquer lue la notification d'autrui (web) →",r1.status_code,"lue=",n.lue if hasattr(n,'lue') else getattr(n,'read',None)); transaction.set_rollback(True)
r=c.get(f"/api/notifications/notifications/{n.pk}/",HTTP_HOST="localhost"); print("COM lecture API de la notification d'autrui →",r.status_code)
# fil d'un autre bâtiment
t=Thread.objects.first(); 
for u in ("marin_abe_1","terre_classe","equipier_a"):
    r=cl(u).get(f"/api/threads/threads/{t.pk}/",HTTP_HOST="localhost"); print("COM lecture thread",t.pk,"par",u,"→",r.status_code)
    with transaction.atomic():
        r=cl(u).post("/api/threads/messages/",{"thread":t.pk,"content":"audit"},content_type="application/json",HTTP_HOST="localhost"); print("COM   écriture message par",u,"→",r.status_code); transaction.set_rollback(True)
# annonces
for u in ("equipier_a","chef_service_a","second_a","cdt_a","marin_abe_1","terre_classe"):
    c=cl(u); r=c.get("/annonces/",HTTP_HOST="localhost"); r2=c.get("/annonces/nouvelle/",HTTP_HOST="localhost"); print("COM annonces",u,"liste",r.status_code,"| formulaire de création",r2.status_code)
a=Annonce.objects.first(); print("COM annonce 1: ship/service/sector/section/equipage ciblés →",[getattr(a,k,None) for k in ("ship_id","service_id","sector_id","section_id","equipage")],"niveau",getattr(a,"niveau",None))
for u in ("marin_abe_1","equipier_a","terre_classe"): print("COM lecture annonce",a.pk,"par",u,cl(u).get(f"/annonces/{a.pk}/",HTTP_HOST="localhost").status_code)
