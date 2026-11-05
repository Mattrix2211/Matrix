import datetime, json
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from quarts.models import FeuilleService, RedacteurFeuilleService, Quart, CreneauQuart
from org.models import Ship
U=["equipier_a","equipier_a2","marin_b","chef_section_a","chef_secteur_a","chef_secteur_b","chef_service_a","coma_comaeq","coma_comanav","coma_comops","second_a","cdt_a","cdt_b","admin_navire","terre_classe","admin"]
cl={u:Client(raise_request_exception=False) for u in U}
for u,c in cl.items(): c.force_login(User.objects.get(username=u))
res={}
# A. feuille : étapes du circuit, effet réel sur le statut
etapes=[("enregistrer_entete","BROUILLON"),("proposer","BROUILLON"),("viser_secteur","VISA_SECTEUR"),("viser_service","VISA_SERVICE"),("viser_comaeq","VISA_COMAEQ"),("modifier_comaeq","VISA_COMAEQ"),("renvoyer","VISA_SERVICE"),("ouvrir_rectificatif","PUBLIEE"),("resynchroniser","BROUILLON")]
date="2027-05-03"; url=f"/quarts/feuille-service/2/{date}/"
cree_par=User.objects.get(username="equipier_a2")
for action,statut in etapes:
    for u in U:
        with transaction.atomic():
            f=FeuilleService.objects.create(ship_id=2,equipage="A",date=date,created_by=cree_par,updated_by=cree_par)
            FeuilleService.objects.filter(pk=f.pk).update(statut=statut)
            avant=FeuilleService.objects.get(pk=f.pk)
            r=cl[u].post(url,{"action":action,"motif":"audit","commentaire":"audit"},HTTP_HOST="localhost")
            apres=FeuilleService.objects.get(pk=f.pk)
            effet = apres.statut!=statut or apres.updated_by_id!=avant.updated_by_id or apres.valeurs_entete!=avant.valeurs_entete
            res[f"FEUILLE|{action}@{statut}|{u}"]=(r.status_code,effet)
            transaction.set_rollback(True)
# B. désignation de rédacteurs
cible=User.objects.get(username="equipier_a"); cible_b=User.objects.get(username="m_dupont") if User.objects.filter(username="m_dupont").exists() else None
for tag,cb in (("equipier_a(A)",cible),("marin_b2(B)",User.objects.filter(profile__ship_id=2,profile__equipage="B").exclude(username="marin_b").first())):
    if cb is None: continue
    for u in U:
        with transaction.atomic():
            r=cl[u].post(f"/quarts/feuille-service/redacteurs/?ship=2",{"action":"designer","user":cb.pk,"ship":2},HTTP_HOST="localhost")
            eff=RedacteurFeuilleService.objects.filter(ship_id=2,user=cb).exists()
            res[f"DESIGNER|{tag}|{u}"]=(r.status_code,eff); transaction.set_rollback(True)
# C. création inter-équipage via ?equipage=
for u in ("equipier_a2","marin_b"):
    for eq in ("A","B"):
        with transaction.atomic():
            r=cl[u].post(f"/quarts/feuille-service/2/2027-06-01/?equipage={eq}",{"action":"creer"},HTTP_HOST="localhost")
            res[f"CREER_INTER|{u}|?equipage={eq}"]=(r.status_code,list(FeuilleService.objects.filter(ship_id=2,date="2027-06-01").values_list("equipage",flat=True)))
            transaction.set_rollback(True)
# D. liste publiée : suppression d'un créneau (voie directe)
q=Quart.objects.get(pk=2); cr=CreneauQuart.objects.filter(quart=q).first()
print("quart2 créneaux:", CreneauQuart.objects.filter(quart=q).count(), "statut", q.statut)
for u in U:
    with transaction.atomic():
        n0=CreneauQuart.objects.filter(quart=q).count()
        r=cl[u].post("/quarts/quart/2/",{"action":"supprimer_creneau","creneau_id":cr.pk,"motif":"audit"},HTTP_HOST="localhost")
        res[f"DIRECT|supprimer_creneau@publiée|{u}"]=(r.status_code, CreneauQuart.objects.filter(quart=q).count()!=n0)
        transaction.set_rollback(True)
json.dump(res,open("droits2.json","w"),ensure_ascii=False)
print("OK",len(res))
