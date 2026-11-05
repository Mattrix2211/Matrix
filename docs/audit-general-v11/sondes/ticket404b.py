from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from logistics.models import CorrectiveTicket
t=CorrectiveTicket.objects.get(pk="1a696760-af5a-4363-a09c-858bb5780170")
for acteur,cible in (("coma_comaeq","equipier_a"),("coma_comaeq","chef_secteur_a"),("admin_navire","equipier_a"),("chef_secteur_incendie_a","equipier_a"),("chef_secteur_incendie_a","chef_secteur_a")):
    with transaction.atomic():
        c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=acteur))
        t.assignees.clear()
        r=c.post(f"/logistics/tickets/{t.pk}/assign/",{"assignees":[User.objects.get(username=cible).pk]},HTTP_HOST="localhost")
        print("ASSIGN",acteur,"->",cible,r.status_code,[u.username for u in t.assignees.all()])
        transaction.set_rollback(True)
