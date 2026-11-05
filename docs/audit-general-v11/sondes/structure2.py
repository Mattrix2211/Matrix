import traceback
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from org.models import Sector, Service, Section, Ship
c=Client(raise_request_exception=True); c.force_login(User.objects.get(username="admin"))
for modele,act in ((Sector,"delete_sector"),(Service,"delete_service")):
    for obj in modele.objects.all()[:6]:
        try:
            with transaction.atomic():
                r=c.post("/parametre/",{"action":act,"pk":obj.pk,"next_tab":"utilisateurs"},HTTP_HOST="localhost"); print("STR2",act,obj,r.status_code); transaction.set_rollback(True)
        except Exception as e:
            print("STR2 EXC",act,obj,type(e).__name__,str(e)[:230]); 
