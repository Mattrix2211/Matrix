import re, json
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from quarts.models import FeuilleService
U=["equipier_a","equipier_a2","marin_b","chef_section_a","chef_secteur_a","chef_secteur_b","chef_service_a","coma_comaeq","coma_comanav","coma_comops","second_a","cdt_a","cdt_b","admin_navire","terre_classe","admin"]
cl={u:Client(raise_request_exception=False) for u in U}
for u,c in cl.items(): c.force_login(User.objects.get(username=u))
date="2027-07-05"; url=f"/quarts/feuille-service/2/{date}/"
def statut(): 
    f=FeuilleService.objects.filter(ship_id=2,equipage="A",date=date).first(); return f.statut if f else None
def jeton(u):
    h=cl[u].get(url,HTTP_HOST="localhost").content.decode()
    m=re.search(r'name="jeton_visa"[^>]*value="([^"]+)"',h) or re.search(r'value="([^"]+)"[^>]*name="jeton_visa"',h)
    return m.group(1) if m else ""
def essai(action, depart, acteurs_attendus, extra=lambda u:{}):
    ok=[]
    for u in U:
        sp=transaction.savepoint()
        r=cl[u].post(url,{"action":action,"motif":"audit",**extra(u)},HTTP_HOST="localhost")
        if statut()!=depart or action in("modifier_comaeq",) : ok.append((u,r.status_code,statut()))
        elif r.status_code not in (403,404): ok.append((u,r.status_code,"sans effet"))
        transaction.savepoint_rollback(sp)
    print(f"{action}@{depart}: {ok}")
with transaction.atomic():
    r=cl["equipier_a2"].post(url,{"action":"creer"},HTTP_HOST="localhost"); print("creer",r.status_code,statut())
    r=cl["equipier_a2"].post(url,{"action":"proposer"},HTTP_HOST="localhost"); print("proposer",r.status_code,statut())
    f=FeuilleService.objects.get(ship_id=2,equipage="A",date=date); print("secteur_redacteur",f.secteur_redacteur_id,"service_redacteur",f.service_redacteur_id)
    essai("viser_secteur","VISA_SECTEUR",None)
    essai("renvoyer","VISA_SECTEUR",None)
    cl["chef_secteur_a"].post(url,{"action":"viser_secteur"},HTTP_HOST="localhost"); print("→",statut())
    essai("viser_service","VISA_SERVICE",None)
    cl["chef_service_a"].post(url,{"action":"viser_service"},HTTP_HOST="localhost"); print("→",statut())
    essai("viser_comaeq","VISA_COMAEQ",None,extra=lambda u:{"jeton_visa":jeton(u)})
    essai("modifier_comaeq","VISA_COMAEQ",None)
    essai("renvoyer","VISA_COMAEQ",None)
    r=cl["coma_comaeq"].post(url,{"action":"viser_comaeq","jeton_visa":jeton("coma_comaeq")},HTTP_HOST="localhost"); print("viser_comaeq par comaeq",r.status_code,"→",statut())
    essai("ouvrir_rectificatif","PUBLIEE",None)
    transaction.set_rollback(True)
