# Recette RM-12 : réaffectation d'une installation (service / secteur / section). Écritures annulées par transaction.
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from assets.models import Installation
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from accounts.models import AuditLog
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
inst=Installation.objects.get(section__name="Moteurs bâbord",ship__name="Bretagne",pk__isnull=False) if Installation.objects.filter(section__name="Moteurs bâbord").count()==1 else Installation.objects.filter(section__name="Moteurs bâbord").first()
def etat(i): i.refresh_from_db(); return (i.service_id,i.sector_id,i.section_id,i.ship_id)
def tenter(u,svc,sec,sct,ship=2,label=""):
    with transaction.atomic():
        c=cl(u); avant=etat(inst); n=AuditLog.objects.count()
        r=c.post(f"/installations/{inst.pk}/",{"action":"edit_installation","pk":str(inst.pk),"designation":inst.designation,"reference":inst.reference or "","marque":inst.marque or "","gisement":inst.gisement or "","local":inst.local or "","ship_id":ship,"service_id":svc,"sector_id":sec,"section_id":sct or ""},HTTP_HOST="localhost",follow=True)
        msg=" / ".join(str(m) for m in (r.context["messages"] if r.context and "messages" in r.context else []))[:90]
        apres=etat(inst); trace=list(AuditLog.objects.order_by("-id")[:AuditLog.objects.count()-n].values_list("action","details"))
        print(f"RM12 {label:<58} {u:<16} HTTP {r.status_code} msg={msg!r} avant={avant[:3]} après={apres[:3]} {'CHANGÉ' if avant!=apres else 'inchangé'} trace={trace}")
        transaction.set_rollback(True)
print("RM12 installation de départ :",inst.designation,"|",inst.service,"|",inst.sector,"|",inst.section, "| id",inst.pk)
print("RM12 historique rattaché : tickets",CorrectiveTicket.objects.filter(installation=inst).count() if hasattr(CorrectiveTicket,'installation') else 'n/a',"occurrences",MaintenanceOccurrence.objects.filter(installation=inst).count() if hasattr(MaintenanceOccurrence,'installation') else 'n/a')
# A. Réaffectation légitime : Moteurs → Auxiliaires / Pompes (même service), puis vers Énergie / Électricité / Tableaux
for u in ("chef_section_a","chef_secteur_a","chef_service_a","second_a","cdt_a","equipier_a","chef_service_elec_a" if User.objects.filter(username="chef_service_elec_a").exists() else "chef_secteur_elec_a","admin_navire"):
    tenter(u,2,4,4,label="A. même service : secteur Moteurs → Auxiliaires/Pompes")
for u in ("chef_secteur_a","chef_service_a","second_a","admin_navire"):
    tenter(u,3,5,5,label="B. autre service : Propulsion → Énergie/Électricité/Tableaux")
# C. combinaisons incohérentes
tenter("chef_service_a",2,5,None,label="C1. service Propulsion avec secteur Électricité (d'un autre service)")
tenter("chef_service_a",3,3,3,label="C2. service Énergie avec secteur/section de Propulsion")
tenter("second_a",2,3,4,label="C3. section Pompes (autre secteur) sous secteur Moteurs")
for u in ("admin_navire","admin"):
    tenter(u,2,5,None,label="C1bis. service Propulsion + secteur Électricité (autre service)")
    tenter(u,3,3,3,label="C2bis. service Énergie + secteur/section de Propulsion")
    tenter(u,2,3,4,label="C3bis. section Pompes sous secteur Moteurs")
# D. autre navire
tenter("second_a",6,8,8,ship=3,label="D. vers un autre navire (Normandie)")
tenter("cdt_a",6,8,8,ship=3,label="D2. idem, commandant du Bretagne")
tenter("admin",6,8,8,ship=3,label="D3. idem, administrateur général")
# E. vue des effets sur le périmètre
with transaction.atomic():
    c=cl("admin_navire"); c.post(f"/installations/{inst.pk}/",{"action":"edit_installation","pk":str(inst.pk),"designation":inst.designation,"ship_id":2,"service_id":3,"sector_id":5,"section_id":5},HTTP_HOST="localhost")
    for u in ("chef_secteur_a","chef_service_a","chef_secteur_elec_a"):
        print("RM12 E. après réaffectation vers Énergie/Électricité, accès de",u,"à la fiche →",cl(u).get(f"/installations/{inst.pk}/",HTTP_HOST="localhost").status_code)
    transaction.set_rollback(True)
# F. effets annexes d'une réaffectation faite par admin_navire : notification, historique, tickets visibles
from notifications.models import Notification
from logistics.perimetre import perimetre_tickets_q
with transaction.atomic():
    n0=Notification.objects.count()
    cl("admin_navire").post(f"/installations/{inst.pk}/",{"action":"edit_installation","pk":str(inst.pk),"designation":inst.designation,"ship_id":2,"service_id":3,"sector_id":5,"section_id":5},HTTP_HOST="localhost")
    print("RM12 F. notifications créées par la réaffectation :",Notification.objects.count()-n0)
    for t in CorrectiveTicket.objects.filter(installation=inst):
        print("RM12 F. ticket",t.pk,"état",t.status,"visible chef_service_a (ancien service)?",CorrectiveTicket.objects.filter(perimetre_tickets_q(User.objects.get(username="chef_service_a")),pk=t.pk).exists(),"| chef_secteur_elec_a (nouveau)?",CorrectiveTicket.objects.filter(perimetre_tickets_q(User.objects.get(username="chef_secteur_elec_a")),pk=t.pk).exists())
    transaction.set_rollback(True)
