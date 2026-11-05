from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from org.models import Ship, Service, Sector, Section
from accounts.models import UserProfile
from quarts.models import ChefDeListe
from assets.models import Installation
from maintenance.models import MaintenanceOccurrence
print("STR admin superuser:", User.objects.get(username="admin").is_superuser, "| profil", User.objects.get(username="admin").profile.role)
sh=Ship.objects.get(name="Bretagne")
for u in ("admin_navire","cdt_a","second_a","chef_service_a","admin"):
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); res={}
    for act,data in (("add_service",{"ship_id":sh.pk,"name":"Service audit"}),("add_sector",{"service_id":Service.objects.filter(ship=sh).first().pk,"name":"Secteur audit"}),("add_section",{"sector_id":Sector.objects.filter(service__ship=sh).first().pk,"name":"Section audit"})):
        with transaction.atomic():
            r=c.post("/parametre/?tab=notifications",{"action":act,"next_tab":"utilisateurs",**data},HTTP_HOST="localhost"); 
            cree={"add_service":Service.objects.filter(name="Service audit").exists(),"add_sector":Sector.objects.filter(name="Secteur audit").exists(),"add_section":Section.objects.filter(name="Section audit").exists()}[act]
            res[act]=(r.status_code,cree); transaction.set_rollback(True)
    print("STR",u,res)
# conséquence d'une suppression de section / de secteur, par le compte technique
sec=Section.objects.get(name__icontains="bâbord") if Section.objects.filter(name__icontains="bâbord").exists() else Section.objects.first()
with transaction.atomic():
    avant={"profils_dans_section":UserProfile.objects.filter(section=sec).count(),"profils_scope_section":[ (p.user.username,p.scope[0]) for p in UserProfile.objects.filter(section=sec)]}
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="admin"))
    r=c.post("/parametre/",{"action":"delete_section","pk":sec.pk,"next_tab":"utilisateurs"},HTTP_HOST="localhost")
    apres=[(p.user.username,p.scope[0]) for p in UserProfile.objects.filter(user__username__in=[x[0] for x in avant["profils_scope_section"]])]
    print("STR delete_section",sec,r.status_code,"avant",avant["profils_scope_section"],"après",apres,"section encore là:",Section.objects.filter(pk=sec.pk).exists())
    transaction.set_rollback(True)
secteur=Sector.objects.get(pk=sec.sector_id)
with transaction.atomic():
    n={"profils":UserProfile.objects.filter(sector=secteur).count(),"installations":Installation.objects.filter(sector=secteur).count(),"chefs_de_liste":ChefDeListe.objects.filter(sector=secteur).count()}
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="admin"))
    r=c.post("/parametre/",{"action":"delete_sector","pk":secteur.pk,"next_tab":"utilisateurs"},HTTP_HOST="localhost")
    m={"profils_secteur_restants":UserProfile.objects.filter(sector=secteur).count(),"installations_secteur_restantes":Installation.objects.filter(sector=secteur).count(),"chefs_de_liste_restants":ChefDeListe.objects.filter(sector=secteur).count(),"installations_total":Installation.objects.count(),"installations_sans_secteur":Installation.objects.filter(sector=None).count(),"profils_scope_ship":UserProfile.objects.filter(user__in=[p.user for p in UserProfile.objects.filter(sector=None,service=None)]).count()}
    print("STR delete_sector",secteur,r.status_code,"avant",n,"après",m)
    transaction.set_rollback(True)
