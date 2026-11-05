# Recette RM-30 : composition d'une fraction de service à quai (exemple BRF : 9 postes) avec le module Postes et le lien avec la liste de service de garde. Écritures annulées.
import re
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from postes.models import Poste, AffectationPoste
from postes.services import tableau_effectifs
from quarts.models import ServiceGarde, CreneauServiceGarde
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def L(tag,u,r,extra=""): print(f"RM30 {tag:<64} {u:<17} HTTP {r.status_code} {extra}")
print("RM30 postes en démonstration :",[(p.intitule,p.ship.name,p.effectif,p.affectations.count()) for p in Poste.objects.all()])
BRF=["Officier de garde (OG)","Officier de permanence (OPSC)","Officier de permanence nav. (OPN)","Gradé de coupée 1","Gradé de coupée 2","Gradé de coupée 3","Permanent mécanique","Permanent électricité","Permanent sécurité"]
with transaction.atomic():
    for u in ("equipier_a","chef_section_a","chef_secteur_a","chef_service_a","second_a","cdt_a","admin_navire"):
        r=cl(u).get("/postes/nouveau/",HTTP_HOST="localhost"); L("1. ouvrir la création d'un poste",u,r)
    # 2. création des 9 postes de la fraction par le commandant en second puis le commandant
    for u in ("second_a","cdt_a","chef_service_a"):
        n=Poste.objects.count()
        r=cl(u).post("/postes/nouveau/",{"intitule":BRF[0]+" "+u,"cible":"ship:2","effectif":"1","equipage":""},HTTP_HOST="localhost",follow=True)
        L("2. créer un poste au niveau du bâtiment (ship:2)",u,r,f"postes+{Poste.objects.count()-n}")
    n=Poste.objects.count()
    for i in BRF[1:]:
        cl("cdt_a").post("/postes/nouveau/",{"intitule":i,"cible":"ship:2","effectif":"1" if "coupée" not in i else "1","equipage":""},HTTP_HOST="localhost")
    print("RM30 2. postes de la fraction BRF créés par le commandant :",Poste.objects.count()-n,"/ 8 demandés (+1 déjà créé)")
    # 3. affectation de marins et lecture du tableau d'effectifs
    brf=list(Poste.objects.filter(intitule__in=BRF+[BRF[0]+" cdt_a"]))
    marins=list(User.objects.filter(profile__ship_id=2,is_active=True).exclude(username__in=("admin","cdt_a","second_a"))[:6])
    for p,m in zip(brf,marins):
        r=cl("cdt_a").post(f"/postes/{p.pk}/",{"action":"affecter","marin":m.pk},HTTP_HOST="localhost")
    lignes=[l for l in tableau_effectifs(User.objects.get(username="cdt_a")) if l["poste"].pk in {p.pk for p in brf}]
    print("RM30 3. tableau d'effectifs du commandant (poste : pourvu/requis) :",[(l["poste"].intitule[:22],f"{l['affectes']}/{l['poste'].effectif}") for l in lignes])
    print("RM30 3. postes non pourvus signalés :",sum(1 for l in lignes if l["non_pourvu"]),"| composition complète ?",all(l["non_pourvu"]==0 for l in lignes))
    r=cl("cdt_a").get("/postes/",HTTP_HOST="localhost"); t=r.content.decode()
    print("RM30 3. page /postes/ :",r.status_code,"| mentions « fraction » / « composition » / « quai » :",[len(re.findall(m,t,re.I)) for m in ("fraction","composition","quai")])
    # 4. lien avec la liste de service de garde
    champs=[f.name for f in ServiceGarde._meta.fields]
    print("RM30 4. champs d'un service de garde :",[c for c in champs if c not in ("created_at","updated_at","created_by","updated_by")])
    print("RM30 4. liaison Poste ↔ créneau de garde (clé étrangère) :",[f.name for f in CreneauServiceGarde._meta.fields if f.is_relation and f.related_model is Poste] or "aucune — le poste du créneau est un texte libre")
    transaction.set_rollback(True)
