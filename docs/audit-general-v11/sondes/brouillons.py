import re
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from matrix.core.models import Brouillon
from maintenance.models import MaintenanceOccurrence
u=User.objects.get(username="equipier_a")
occ_autre=MaintenanceOccurrence.objects.exclude(assignees=u).first()
cas=[("a anomalie URL nominale","anomalie:nouvelle","/logistics/anomalies/signaler/"),
 ("b anomalie URL périmée (route disparue)","anomalie:nouvelle","/logistics/anomalie/nouvelle/"),
 ("c anomalie avec ?asset inexistant","anomalie:nouvelle","/logistics/anomalies/signaler/?asset=999999"),
 ("d anomalie avec ?installation inexistante","anomalie:nouvelle","/logistics/anomalies/signaler/?installation=999999"),
 ("e compte rendu d'une occurrence inexistante","compte-rendu:99999","/maintenance/occurrences/99999/execute/"),
 (f"f compte rendu d'une occurrence hors droits ({occ_autre.pk})",f"compte-rendu:{occ_autre.pk}",f"/maintenance/occurrences/{occ_autre.pk}/execute/"),
 ("g correctif sur ticket inexistant","correctif:00000000-0000-0000-0000-000000000000","/maintenance/correctif/00000000-0000-0000-0000-000000000000/")]
for nom,cle,url in cas:
    with transaction.atomic():
        Brouillon.objects.filter(user=u).delete()
        Brouillon.objects.create(user=u,cle=cle,contenu={"x":"1"},libelle=nom,url=url)
        c=Client(raise_request_exception=False); c.force_login(u)
        h=c.get("/",HTTP_HOST="localhost").content.decode("utf-8","ignore")
        m=re.search(r'<a[^>]*href="([^"]+)"[^>]*>\s*Reprendre',h) or re.search(r'href="([^"]+)"[^>]*>[^<]*Reprendre',h)
        lien=m.group(1) if m else None
        code=c.get(lien,HTTP_HOST="localhost").status_code if lien else None
        print("BROUILLON",nom,"| lien Reprendre:",lien,"| statut:",code)
        transaction.set_rollback(True)
