from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from training.models import TrainingCourse, TrainingRecord, ReferentFormation
from documentation.models import Document, VersionDocument
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
U=["equipier_a","chef_section_a","chef_secteur_a","chef_service_a","coma_comaeq","second_a","cdt_a","admin_navire","terre_classe","marin_abe_1"]
print("AUT formations:",TrainingCourse.objects.count(),"référents:",list(ReferentFormation.objects.values_list("user__username","course__title")[:6]))
co=TrainingCourse.objects.first(); marin=User.objects.get(username="equipier_a")
for u in U:
    with transaction.atomic():
        n0=TrainingRecord.objects.count()
        r=cl(u).post("/formations/valider/",{"marin_id":marin.pk,"course_id":co.pk,"completed_at":"2026-11-01"},HTTP_HOST="localhost")
        print("AUT validation de formation",str(co)[:25],"par",u,"→",r.status_code,"| enregistrements +",TrainingRecord.objects.count()-n0); transaction.set_rollback(True)
# pages des modules « moins visibles »
for page in ("/documentation/","/documentation/nouveau/","/retex/","/retex/nouveau/","/retex/domaines/","/postes/","/postes/nouveau/","/absences/","/programme/","/demandes/","/taches/","/annonces/nouvelle/"):
    print("AUT",page,{u:cl(u).get(page,HTTP_HOST="localhost").status_code for u in ("equipier_a","chef_service_a","cdt_a","admin_navire","terre_classe")})
# documentation : auteur valide sa propre version ?
d=Document.objects.first()
if d: print("AUT documents:",Document.objects.count(),"versions par état:",dict(__import__('collections').Counter(VersionDocument.objects.values_list("etat",flat=True))))
