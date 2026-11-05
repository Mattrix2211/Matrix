from django.db import transaction
from django.contrib.auth.models import User
from accounts.models import UserProfile
from matrix.core.mixins import build_scope_q
from assets.models import Asset, Installation
from logistics.models import CorrectiveTicket
from logistics.perimetre import perimetre_tickets_q
from maintenance.models import MaintenanceOccurrence
from taches.models import Tache
ea=User.objects.get(username="equipier_a"); pa=ea.profile
print("SEC1 equipier_a:", "service",pa.service,"| secteur",pa.sector,"| section",pa.section,"| role",pa.role,"| scope",pa.scope)
def mesures(u):
    return {"matériels":Asset.objects.filter(build_scope_q(u,"","")).count() if False else None}
with transaction.atomic():
    def creer(nom, **kw):
        u=User.objects.create_user(nom,password="x"); UserProfile.objects.update_or_create(user=u,defaults={"role":"EQUIPIER","ship":pa.ship,"equipage":pa.equipage,**kw}); return User.objects.get(pk=u.pk)
    cas={"avec section (equipier_a)":ea,
         "secteur sans section":creer("t_secteur",service=pa.service,sector=pa.sector),
         "service seul (ni secteur ni section)":creer("t_service",service=pa.service),
         "bâtiment seul (aucun rattachement d'unité)":creer("t_ship")}
    for nom,u in cas.items():
        a=Asset.objects.filter(build_scope_q(u,"","")).count() if hasattr(Asset,"ship") else -1
        i=Installation.objects.filter(build_scope_q(u,"","")).count()
        t=CorrectiveTicket.objects.filter(perimetre_tickets_q(u)).count()
        o=MaintenanceOccurrence.objects.filter(build_scope_q(u,"asset__","installation_maintenance__installation__")).count()
        print("SEC2",nom,"| scope",u.profile.scope[0],"| matériels",a,"| installations",i,"| tickets",t,"| occurrences",o)
    transaction.set_rollback(True)
print("SEC3 totaux: matériels",Asset.objects.count(),"installations",Installation.objects.count(),"tickets",CorrectiveTicket.objects.count(),"occurrences",MaintenanceOccurrence.objects.count())
