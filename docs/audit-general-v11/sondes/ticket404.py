from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from logistics.models import CorrectiveTicket
from logistics.perimetre import perimetre_tickets_q
t=CorrectiveTicket.objects.get(pk="1a696760-af5a-4363-a09c-858bb5780170")
a=t.asset
print("asset:",a, "ship",a.ship_id,"service",a.service,"secteur",a.sector,"| reported_at",t.reported_at.date())
print("chef_secteur_a: secteur", User.objects.get(username="chef_secteur_a").profile.sector, "service", User.objects.get(username="chef_secteur_a").profile.service)
voient=[u.username for u in User.objects.filter(is_active=True).select_related("profile") if CorrectiveTicket.objects.filter(perimetre_tickets_q(u),pk=t.pk).exists()]
print("VOIENT le ticket:",voient)
# la route est valide pour qui voit le ticket
for n in voient[:3]:
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=n))
    print("GET par",n,c.get(f"/logistics/tickets/{t.pk}/",HTTP_HOST="localhost").status_code)
# l'assignation hors périmètre est-elle possible ?
for acteur in voient[:6]:
    with transaction.atomic():
        c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=acteur))
        cible=User.objects.get(username="chef_secteur_a")
        for nom_url in ("/logistics/tickets/%s/assigner/"%t.pk, "/logistics/tickets/%s/assignes/"%t.pk):
            r=c.post(nom_url,{"assignees":[cible.pk]},HTTP_HOST="localhost"); print("ASSIGN",acteur,nom_url.split('/')[-2],r.status_code, [u.username for u in t.assignees.all()])
        transaction.set_rollback(True)
