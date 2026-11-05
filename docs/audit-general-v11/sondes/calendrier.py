import json, collections
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from org.models import Ship
U=["equipier_a","marin_b","chef_secteur_a","coma_comaeq","cdt_a","cdt_b","second_a","admin_navire","terre_classe","admin","marin_abe_1","cdt_abe"]
rien=set(); res={}
for u in U:
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u))
    r=c.get("/calendar/events/?start=2026-10-01&end=2027-03-31",HTTP_HOST="localhost")
    try: ev=r.json()
    except Exception: ev=[]
    if isinstance(ev,dict): ev=ev.get("events",ev.get("results",[]))
    types=collections.Counter((e.get("extendedProps",{}) or {}).get("type") or e.get("type") or "?" for e in ev)
    res[u]=(r.status_code,len(ev),dict(types))
    print("CAL",u,res[u])
# étanchéité : un utilisateur d'un autre bâtiment peut-il demander les événements de Bretagne ?
c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="marin_abe_1"))
sid=Ship.objects.get(name="Bretagne").pk
r=c.get(f"/calendar/events/?start=2026-10-01&end=2027-03-31&ship={sid}",HTTP_HOST="localhost"); ev=r.json() if r.status_code==200 else []
ev=ev.get("events",ev) if isinstance(ev,dict) else ev
print("CAL fuite inter-bâtiment : marin_abe_1 demande ship=Bretagne ->",r.status_code,len(ev),"événements")
# ical personnel
c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="equipier_a")); r=c.get("/calendar/ical/my/",HTTP_HOST="localhost"); print("CAL ical perso",r.status_code,r.headers.get("Content-Type"),r.content.decode()[:60].replace("\n"," "))
c=Client(); r=c.get("/calendar/ical/my/",HTTP_HOST="localhost"); print("CAL ical anonyme",r.status_code)
# déplacement : un équipier peut-il déplacer un événement de maintenance ? (écriture)
c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="equipier_a"))
with transaction.atomic():
    r=c.post("/calendar/events/move/",{"type":"maintenance","id":1,"start":"2027-01-01"},content_type="application/json",HTTP_HOST="localhost"); print("CAL déplacement par équipier",r.status_code)
    transaction.set_rollback(True)
