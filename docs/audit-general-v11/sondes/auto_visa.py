from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from quarts.models import FeuilleService
date="2027-07-06"; url=f"/quarts/feuille-service/2/{date}/"
def cli(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def st(): return FeuilleService.objects.get(ship_id=2,equipage="A",date=date).statut
for visa in ("admin_navire","cdt_a"):
  with transaction.atomic():
    cli("equipier_a2").post(url,{"action":"creer"},HTTP_HOST="localhost"); cli("equipier_a2").post(url,{"action":"proposer"},HTTP_HOST="localhost")
    c=cli(visa); c.post(url,{"action":"viser_secteur"},HTTP_HOST="localhost"); a=st()
    c.post(url,{"action":"viser_service"},HTTP_HOST="localhost"); b=st()
    f=FeuilleService.objects.get(ship_id=2,equipage="A",date=date)
    print("AUTOVISA",visa,"après secteur:",a,"après service:",b,"visa_secteur_par=",f.visa_secteur_par,"visa_service_par=",f.visa_service_par)
    transaction.set_rollback(True)
