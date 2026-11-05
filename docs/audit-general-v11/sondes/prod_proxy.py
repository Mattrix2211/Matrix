from django.test import Client
from django.conf import settings
print("PROD DEBUG=",settings.DEBUG,"SSL_REDIRECT=",settings.SECURE_SSL_REDIRECT,"PROXY_HDR=",getattr(settings,"SECURE_PROXY_SSL_HEADER",None),"CSRF_TRUSTED=",settings.CSRF_TRUSTED_ORIGINS)
c=Client(enforce_csrf_checks=True)
# 1. HTTP direct (réseau de bord sans TLS)
r=c.get("/accounts/login/",HTTP_HOST="matrix.bord.local"); print("PROD 1 GET http direct ->",r.status_code,r.headers.get("Location"))
# 2. derrière un reverse proxy qui termine TLS et envoie X-Forwarded-Proto
r=c.get("/accounts/login/",HTTP_HOST="matrix.bord.local",HTTP_X_FORWARDED_PROTO="https"); print("PROD 2 GET via proxy (X-Forwarded-Proto: https) ->",r.status_code,r.headers.get("Location"))
# 3. HTTPS natif (le serveur d'application termine lui-même le TLS)
r=c.get("/accounts/login/",HTTP_HOST="matrix.bord.local",secure=True); print("PROD 3 GET https natif ->",r.status_code)
# 4. POST de connexion en https natif avec CSRF
g=c.get("/accounts/login/",HTTP_HOST="matrix.bord.local",secure=True); tok=g.cookies.get("csrftoken").value if g.cookies.get("csrftoken") else ""
r=c.post("/accounts/login/",{"username":"x","password":"y","csrfmiddlewaretoken":tok},HTTP_HOST="matrix.bord.local",HTTP_ORIGIN="https://matrix.bord.local",secure=True); print("PROD 4 POST https natif, Origin cohérent ->",r.status_code)
# 5. POST via proxy : Django voit http, Origin = https
r=c.post("/accounts/login/",{"username":"x","password":"y","csrfmiddlewaretoken":tok},HTTP_HOST="matrix.bord.local",HTTP_ORIGIN="https://matrix.bord.local",HTTP_X_FORWARDED_PROTO="https"); print("PROD 5 POST via proxy ->",r.status_code,r.headers.get("Location"))
