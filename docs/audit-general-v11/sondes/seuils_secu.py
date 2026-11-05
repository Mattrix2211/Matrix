from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from org.models import Ship, VersionConfiguration
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
# (b) effet réel d'un changement de seuil par l'administrateur d'unité
with transaction.atomic():
    def publier(): return cl("chef_service_a").post("/quarts/quart/1/",{"action":"publier"},HTTP_HOST="localhost").status_code
    avant=publier(); v0=list(VersionConfiguration.objects.values_list("cle","valeur"))
    r=cl("admin_navire").post("/parametre/?tab=seuils_role",{"action":"update_role_threshold","ship_id":2,"cle_action":"liste_service_publication","nouveau_role":"COMMANDANT","next_tab":"seuils_role"},HTTP_HOST="localhost")
    apres=publier(); v1=list(VersionConfiguration.objects.values_list("cle","valeur"))
    print("SEU chef_service_a publie une liste : avant le réglage",avant,"→ après avoir relevé le seuil à COMMANDANT",apres,"| réglage HTTP",r.status_code,"| versions de configuration",v0,"→",v1)
    r=cl("admin_navire").post("/parametre/?tab=seuils_role",{"action":"reset_role_threshold","ship_id":2,"cle_action":"liste_service_publication","next_tab":"seuils_role"},HTTP_HOST="localhost"); print("SEU retour au défaut →",publier())
    r=cl("chef_service_a").post("/parametre/?tab=seuils_role",{"action":"update_role_threshold","ship_id":2,"cle_action":"liste_service_publication","nouveau_role":"EQUIPIER"},HTTP_HOST="localhost"); print("SEU un chef de service tente d'abaisser un seuil →",r.status_code)
    r=cl("admin_navire").post("/parametre/?tab=seuils_role",{"action":"update_role_threshold","ship_id":1,"cle_action":"liste_service_publication","nouveau_role":"EQUIPIER"},HTTP_HOST="localhost"); print("SEU admin d'unité modifie le seuil d'un AUTRE bâtiment (ship 1) →",r.status_code)
    transaction.set_rollback(True)
# (f) connexions répétées, politique de mot de passe
with transaction.atomic():
    c=Client(raise_request_exception=False); codes=[c.post("/accounts/login/",{"username":"equipier_a","password":"mauvais%d"%i},HTTP_HOST="localhost").status_code for i in range(25)]
    ok=c.post("/accounts/login/",{"username":"equipier_a","password":"pass"},HTTP_HOST="localhost").status_code
    print("SEC 25 mots de passe erronés de suite :",set(codes),"| puis le bon mot de passe →",ok,"(302 = connexion acceptée : aucun verrouillage)")
    transaction.set_rollback(True)
from django.conf import settings
print("SEC validateurs de mot de passe:",[v["NAME"].split(".")[-1] for v in settings.AUTH_PASSWORD_VALIDATORS],"| durée de session (s):",getattr(settings,"SESSION_COOKIE_AGE",None),"| expiration à la fermeture:",getattr(settings,"SESSION_EXPIRE_AT_BROWSER_CLOSE",None))
with transaction.atomic():
    r=cl("admin_navire").post("/users/",{"action":"create_user","username":"test_faible","password":"a","role":"EQUIPIER","ship_id":2},HTTP_HOST="localhost"); print("SEC création d'un compte avec le mot de passe « a » →",r.status_code,"| compte créé:",User.objects.filter(username="test_faible").exists())
    u=User.objects.filter(username="test_faible").first(); print("SEC   mot de passe accepté tel quel:",bool(u and u.check_password("a")))
    transaction.set_rollback(True)
