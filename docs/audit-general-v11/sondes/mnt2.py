from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket
from notifications.models import Notification
inst=MaintenanceOccurrence.objects.filter(installation_maintenance__isnull=False).exclude(status="DONE").exclude(installation_maintenance__installation__critique=True).first()
mat=MaintenanceOccurrence.objects.filter(asset__isnull=False).exclude(status="DONE").first()
print("MN2 occurrences installation:",MaintenanceOccurrence.objects.filter(installation_maintenance__isnull=False).count(),"| occurrences matériel mobile:",MaintenanceOccurrence.objects.filter(asset__isnull=False).count())
for nom,occ in (("installation",inst),("matériel mobile",mat)):
    if not occ: print("MN2",nom,"aucune occurrence disponible"); continue
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="cdt_a"))
    with transaction.atomic():
        t0=CorrectiveTicket.objects.count(); n0=Notification.objects.count()
        r=c.post(f"/api/maintenance/occurrences/{occ.pk}/complete/",{"conformity":"NON_CONFORME","notes":"audit"},content_type="application/json",HTTP_HOST="localhost")
        print("MN2",nom,"NON_CONFORME →",r.status_code,"| tickets +",CorrectiveTicket.objects.count()-t0,"| notifications +",Notification.objects.count()-n0)
        transaction.set_rollback(True)
