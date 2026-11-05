import json
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from org.models import Ship, Service, Sector, Section
sh=Ship.objects.get(name="Bretagne"); sv=Service.objects.filter(ship=sh).first(); se=Sector.objects.filter(service__ship=sh).first(); sc=Section.objects.filter(sector__service__ship=sh).first()
for u in ("admin_navire","cdt_a","chef_service_a","admin"):
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); res={}
    for nom,url,data,modele,champ in (("creer service","/api/org/services/",{"ship":sh.pk,"name":"Svc audit API"},Service,"Svc audit API"),("creer secteur","/api/org/sectors/",{"service":sv.pk,"name":"Sec audit API"},Sector,"Sec audit API"),("creer section","/api/org/sections/",{"sector":se.pk,"name":"Sct audit API"},Section,"Sct audit API")):
        with transaction.atomic():
            r=c.post(url,data,content_type="application/json",HTTP_HOST="localhost"); res[nom]=(r.status_code,modele.objects.filter(name=champ).exists()); transaction.set_rollback(True)
    with transaction.atomic():
        r=c.patch(f"/api/org/sections/{sc.pk}/",json.dumps({"name":"Renommée audit"}),content_type="application/json",HTTP_HOST="localhost"); res["renommer section"]=(r.status_code,Section.objects.filter(name="Renommée audit").exists()); transaction.set_rollback(True)
    with transaction.atomic():
        r=c.patch(f"/api/org/sections/{sc.pk}/",json.dumps({"archived":True}),content_type="application/json",HTTP_HOST="localhost"); res["archiver section"]=(r.status_code,Section.objects.get(pk=sc.pk).archived); transaction.set_rollback(True)
    with transaction.atomic():
        r=c.delete(f"/api/org/sections/{sc.pk}/",HTTP_HOST="localhost"); res["supprimer section"]=(r.status_code,not Section.objects.filter(pk=sc.pk).exists()); transaction.set_rollback(True)
    print("API",u,res)
