from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from maintenance.models import MaintenanceOccurrence, MaintenanceExecution
from logistics.models import CorrectiveTicket
from training.tests.test_audit_log import AuditLog
print("MNT occurrences:",MaintenanceOccurrence.objects.count(),"dont installation critique:",MaintenanceOccurrence.objects.filter(installation_maintenance__installation__critique=True).count(),"| statuts:",dict(__import__('collections').Counter(MaintenanceOccurrence.objects.values_list("status",flat=True))))
crit=MaintenanceOccurrence.objects.filter(installation_maintenance__installation__critique=True).exclude(status="DONE").first()
norm=MaintenanceOccurrence.objects.filter(installation_maintenance__installation__critique=False).exclude(status="DONE").first()
cdt=Client(raise_request_exception=False); cdt.force_login(User.objects.get(username="cdt_a"))
def essai(nom,occ,payload,user="cdt_a"):
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=user))
    with transaction.atomic():
        t0=CorrectiveTicket.objects.count(); a0=AuditLog.objects.count()
        r=c.post(f"/api/maintenance/occurrences/{occ.pk}/complete/",payload,content_type="application/json",HTTP_HOST="localhost")
        o=MaintenanceOccurrence.objects.get(pk=occ.pk); ex=MaintenanceExecution.objects.filter(occurrence=occ).first()
        print("MNT",nom,"→",r.status_code,"| statut",o.status,"| valide_par",getattr(ex,"valide_par",None),"| tickets +",CorrectiveTicket.objects.count()-t0,"| audit +",AuditLog.objects.count()-a0)
        transaction.set_rollback(True)
if crit:
    essai("critique sans confirmation",crit,{"conformity":"CONFORME"})
    essai("critique confirmation=oui",crit,{"conformity":"CONFORME","confirmation":True})
    essai("critique confirmation=\"true\" (texte)",crit,{"conformity":"CONFORME","confirmation":"true"})
    essai("critique NON_CONFORME",crit,{"conformity":"NON_CONFORME"})
if norm: essai("non critique, sans confirmation",norm,{"conformity":"CONFORME"})
if norm: essai("non critique, équipier non assigné",norm,{"conformity":"CONFORME"},user="marin_b")
