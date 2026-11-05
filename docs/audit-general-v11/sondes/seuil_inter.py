from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from org.models import RoleThresholdConfig
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
for cible in (1,3,5):
  with transaction.atomic():
    av=list(RoleThresholdConfig.objects.filter(ship_id=cible).values_list("thresholds",flat=True))
    r=cl("admin_navire").post("/parametre/?tab=seuils_role",{"action":"update_role_threshold","ship_id":cible,"selected_ship":cible,"cle_action":"liste_service_publication","nouveau_role":"EQUIPIER","next_tab":"seuils_role"},HTTP_HOST="localhost")
    ap=list(RoleThresholdConfig.objects.filter(ship_id=cible).values_list("thresholds",flat=True))
    print("SIN admin_navire (bâtiment 2) → seuil du bâtiment",cible,":",r.status_code,"| avant",av,"| après",ap)
    transaction.set_rollback(True)
