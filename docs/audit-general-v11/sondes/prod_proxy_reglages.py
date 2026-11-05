from django.test import Client
c=Client(enforce_csrf_checks=True)
H="matrix.bord.local"
r=c.get("/accounts/login/",HTTP_HOST=H,HTTP_X_FORWARDED_PROTO="https"); print("PX1 proxy→app, XFP=https :",r.status_code)
r=c.get("/accounts/login/",HTTP_HOST=H); print("PX2 http direct sans en-tête :",r.status_code,r.headers.get("Location"))
r=c.get("/accounts/login/",HTTP_HOST=H,HTTP_X_FORWARDED_PROTO="http"); print("PX3 proxy→app, XFP=http :",r.status_code)
g=c.get("/accounts/login/",HTTP_HOST=H,HTTP_X_FORWARDED_PROTO="https"); tok=g.cookies["csrftoken"].value
r=c.post("/accounts/login/",{"username":"x","password":"y","csrfmiddlewaretoken":tok},HTTP_HOST=H,HTTP_ORIGIN="https://matrix.bord.local",HTTP_X_FORWARDED_PROTO="https"); print("PX4 POST login via proxy, Origin cohérent :",r.status_code)
r=c.post("/accounts/login/",{"username":"x","password":"y","csrfmiddlewaretoken":tok},HTTP_HOST=H,HTTP_ORIGIN="https://autre.exemple",HTTP_X_FORWARDED_PROTO="https"); print("PX5 POST via proxy, Origin étranger :",r.status_code)
print("PX6 cookies Secure :",g.cookies["csrftoken"]["secure"], "| HSTS en-tête :",g.headers.get("Strict-Transport-Security"))
# usurpation : un client qui joint directement l'application et envoie lui-même l'en-tête
r=c.get("/accounts/login/",HTTP_HOST=H,HTTP_X_FORWARDED_PROTO="https"); print("PX7 usurpation de l'en-tête par un client direct : l'application le croit →",r.status_code,"(d'où l'exigence : application non joignable hors proxy, proxy qui écrase l'en-tête)")
