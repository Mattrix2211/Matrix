import time
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from org.models import Ship, Service, Sector, Section
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
etapes=[]
def pas(nom,r,ok): etapes.append((nom,r.status_code,ok))
t0=time.time()
with transaction.atomic():
    m=cl("admin")
    r=m.post("/parametre/?tab=notifications",{"action":"add_ship","name":"Patrouilleur Test","code":"PT1","fuseau_horaire":"Europe/Paris","next_tab":"utilisateurs"},HTTP_HOST="localhost"); sh=Ship.objects.filter(code="PT1").first(); pas("créer le bâtiment",r,bool(sh))
    for n in ("Pont","Machine"):
        r=m.post("/parametre/",{"action":"add_service","name":n,"ship_id":sh.pk},HTTP_HOST="localhost"); pas("créer le service "+n,r,Service.objects.filter(ship=sh,name=n).exists())
    pont=Service.objects.get(ship=sh,name="Pont"); mach=Service.objects.get(ship=sh,name="Machine")
    for n,s in (("Manœuvre",pont),("Moteurs",mach)):
        r=m.post("/parametre/",{"action":"add_sector","name":n,"service_id":s.pk},HTTP_HOST="localhost"); pas("créer le secteur "+n,r,Sector.objects.filter(service=s,name=n).exists())
    man=Sector.objects.get(service=pont,name="Manœuvre"); mot=Sector.objects.get(service=mach,name="Moteurs")
    comptes={}
    def creer(cle,role,**aff):
        r=m.post("/users/",{"action":"create_user","first_name":cle.replace("_","").title(),"last_name":"Essai","email":cle+"@x.invalid","role":role,"ship_id":sh.pk,**aff},HTTP_HOST="localhost")
        u=User.objects.filter(first_name=cle.replace("_","").title(),last_name="Essai").first(); comptes[cle]=u.username if u else None
        pas("créer le compte "+cle+" ("+r.headers.get("Content-Type","")[:9]+")",r,bool(u))
    creer("cdt_pt","COMMANDANT"); creer("chef_man_pt","CHEF_SECTEUR",service_id=pont.pk,sector_id=man.pk)
    for i in (1,2,3): creer(f"eq_man_pt{i}","EQUIPIER",service_id=pont.pk,sector_id=man.pk)
    creer("eq_sans_rattachement_pt","EQUIPIER")
    ok=sum(1 for e in etapes if e[2]); print("NBA étapes réussies",ok,"/",len(etapes),"| échecs:",[e[0] for e in etapes if not e[2]])
    # le secteur sans section fonctionne-t-il ?
    for cle in ("cdt_pt","chef_man_pt","eq_man_pt1","eq_sans_rattachement_pt"):
        u=comptes[cle]; c=cl(u); print("NBA accueil de",cle,"→",c.get("/",HTTP_HOST="localhost").status_code,"| /taches/",c.get("/taches/",HTTP_HOST="localhost").status_code,"| /quarts/",c.get("/quarts/",HTTP_HOST="localhost").status_code,"| /calendar/",c.get("/calendar/",HTTP_HOST="localhost").status_code,"| périmètre:",User.objects.get(username=u).profile.scope[0])
    # attribution d'une tâche à un équipier d'un secteur sans section
    c=cl(comptes["chef_man_pt"]); eq=User.objects.get(username=comptes["eq_man_pt1"])
    from taches.models import Tache
    r=c.post("/taches/attribuer/",{"titre":"Tâche nouveau bâtiment","assigne":eq.pk},HTTP_HOST="localhost"); print("NBA attribution d'une tâche (URL supposée) →",r.status_code,"| créée:",Tache.objects.filter(titre="Tâche nouveau bâtiment").exists())
    # un chef peut-il ajouter une section (autonomie) ?
    r=cl(comptes["chef_man_pt"]).post("/parametre/",{"action":"add_section","name":"Section X","sector_id":man.pk},HTTP_HOST="localhost"); print("NBA le chef de secteur ajoute une section par l'écran →",r.status_code,Section.objects.filter(name="Section X").exists())
    r=cl(comptes["cdt_pt"]).post("/api/org/sections/",{"sector":man.pk,"name":"Section Y"},content_type="application/json",HTTP_HOST="localhost"); print("NBA le commandant ajoute une section par l'API →",r.status_code)
    # visibilité du marin sans rattachement
    from maintenance.models import MaintenanceOccurrence
    print("NBA marin sans rattachement : voit les autres bâtiments ?",cl(comptes["eq_sans_rattachement_pt"]).get("/calendar/events/?start=2026-10-01&end=2027-03-31",HTTP_HOST="localhost").json().__len__() if True else "", "événements dans son calendrier")
    print("NBA durée de la simulation (HTTP direct) :",round(time.time()-t0,1),"s")
    transaction.set_rollback(True)
