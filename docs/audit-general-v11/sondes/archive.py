import json
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from org.models import Section, Sector
from accounts.models import UserProfile
sc=Section.objects.get(name="Moteurs bâbord"); membres=list(UserProfile.objects.filter(section=sc))
a=Client(raise_request_exception=False); a.force_login(User.objects.get(username="admin_navire"))
with transaction.atomic():
    r=a.patch(f"/api/org/sections/{sc.pk}/",json.dumps({"archived":True}),content_type="application/json",HTTP_HOST="localhost")
    print("ARC archivage via API →",r.status_code,"| section.archived =",Section.objects.get(pk=sc.pk).archived)
    print("ARC périmètre des",len(membres),"membres après archivage:",{p.user.username:p.scope[0] for p in UserProfile.objects.filter(pk__in=[m.pk for m in membres])})
    h=a.get("/users/",HTTP_HOST="localhost").content.decode("utf-8","ignore"); print("ARC la section archivée est encore proposée dans l'annuaire/formulaires:", sc.name in h)
    h2=a.get("/users/nouveau/",HTTP_HOST="localhost").content.decode("utf-8","ignore"); print("ARC … dans le formulaire de création:", sc.name in h2)
    u=User.objects.get(username="equipier_a2"); 
    for ob in (Sector,):
        pass
    # réaffecter un marin vers la section archivée
    r=a.post(f"/users/{User.objects.get(username='marin_b').pk}/modifier/",{"section_id":sc.pk,"sector_id":sc.sector_id,"service_id":sc.sector.service_id,"ship_id":sc.sector.service.ship_id,"role":"EQUIPIER"},HTTP_HOST="localhost"); print("ARC réaffectation vers section archivée →",r.status_code)
    transaction.set_rollback(True)
# renommage : conséquence sur l'historique (noms stockés en texte ?)
from quarts.models import FeuilleService
print("ARC FeuilleService : champs texte reprenant le nom du secteur:",[f.name for f in FeuilleService._meta.fields if 'secteur' in f.name or 'sector' in f.name])
