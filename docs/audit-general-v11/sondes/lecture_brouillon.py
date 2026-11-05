from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from quarts.models import FeuilleService
date="2027-10-04"; url=f"/quarts/feuille-service/2/{date}/"
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
with transaction.atomic():
    cl("equipier_a2").post(url,{"action":"creer"},HTTP_HOST="localhost")
    for etat in ("BROUILLON","PROPOSÉE(VISA_SECTEUR)","PUBLIÉE"):
        if etat.startswith("PROPOS"): cl("equipier_a2").post(url,{"action":"proposer"},HTTP_HOST="localhost")
        if etat=="PUBLIÉE":
            FeuilleService.objects.filter(ship_id=2,date=date).update(statut="PUBLIEE")
        res={}
        for u in ("equipier_a","equipier_a2","marin_b","chef_secteur_a","chef_service_a","coma_comaeq","coma_comanav","second_a","cdt_a","cdt_b","admin_navire","terre_classe","marin_abe_1"):
            res[u]=cl(u).get(url,HTTP_HOST="localhost").status_code
        print("LECT",etat,{k:v for k,v in res.items()})
    transaction.set_rollback(True)
