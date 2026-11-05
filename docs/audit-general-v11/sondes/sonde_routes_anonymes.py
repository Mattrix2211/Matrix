import re
from django.test import Client
from django.contrib.auth.models import User
from django.urls import get_resolver
# toutes les routes sans paramètre, anonymes
from django.urls.resolvers import URLPattern, URLResolver
def parcours(pats, pref=""):
    for p in pats:
        if isinstance(p, URLResolver): yield from parcours(p.url_patterns, pref+str(p.pattern))
        else: yield pref+str(p.pattern)
routes=[r for r in parcours(get_resolver().url_patterns) if "<" not in r and "(" not in r and "^" not in r]
routes=sorted({"/"+r.lstrip("/") for r in routes})
anon=Client(); ouvert=[]
for r in routes:
    if r.startswith(("/static","/media")): continue
    resp=anon.get(r, HTTP_HOST="localhost")
    if resp.status_code==200: ouvert.append(r)
    elif resp.status_code not in (301,302,401,403,404,405): ouvert.append((r,resp.status_code))
print("routes sans paramètre:",len(routes)); print("anonymes répondant 200/autre:", ouvert)
