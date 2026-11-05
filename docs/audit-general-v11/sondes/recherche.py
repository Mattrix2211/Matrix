import re
from django.test import Client
from django.contrib.auth.models import User
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
for u in ("equipier_a","chef_service_a","marin_abe_1","terre_classe"):
    for q in ("pompe","Equipier","incendie"):
        r=cl(u).get("/search/",{"q":q},HTTP_HOST="localhost"); h=r.content.decode("utf-8","ignore")
        cats=re.findall(r'<h2[^>]*>\s*([^<]+?)\s*(?:<|\()',h); n=len(re.findall(r'href="/(?:installations|logistics|taches|users|formations|documentation|retex|assets|quarts|annonces)[^"]*"',h))
        r2=cl(u).get("/search/rapide/",{"q":q},HTTP_HOST="localhost")
        print("REC",u,q,"→",r.status_code,"liens de résultats:",n,"| recherche rapide",r2.status_code,len(r2.content),"octets")
