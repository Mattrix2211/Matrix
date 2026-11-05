import re, time, json
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from quarts.models import FeuilleService
# 1. AUD-001 : création de feuille
for nom in ["equipier_a","equipier_a2","chef_section_a","chef_secteur_a","chef_service_a","coma_comaeq","second_a","cdt_a","admin_navire","marin_b","terre_classe"]:
    c=Client(); c.force_login(User.objects.get(username=nom))
    with transaction.atomic():
        r=c.post("/quarts/feuille-service/2/2027-03-01/", {"action":"creer"})
        cree=FeuilleService.objects.filter(ship_id=2,date="2027-03-01").exists()
        transaction.set_rollback(True)
    print("CREER", nom, r.status_code, "feuille_creee=",cree)
# 2. balayage des liens
res={}
for nom in ["equipier_a","chef_section_a","chef_secteur_a","chef_service_a","coma_comaeq","second_a","cdt_a","admin_navire","terre_classe","admin"]:
    c=Client(); c.force_login(User.objects.get(username=nom))
    r=c.get("/", HTTP_HOST="localhost"); 
    hrefs=sorted(set(h for h in re.findall(r'href="(/[^"#?]*)"', r.content.decode()) if not h.startswith(("/static","/media","/accounts/logout","/admin"))))
    stat={}; lents=[]
    for h in hrefs:
        t=time.time(); rr=c.get(h, HTTP_HOST="localhost"); d=time.time()-t
        stat[h]=rr.status_code; lents.append((round(d,2),h))
    bad={h:s for h,s in stat.items() if s>=400 or s>=300 and False}
    res[nom]=(r.status_code,len(hrefs),bad,sorted(lents,reverse=True)[:2])
    print(nom, "accueil",r.status_code,"liens",len(hrefs),"erreurs",bad,"lents",sorted(lents,reverse=True)[:2])
