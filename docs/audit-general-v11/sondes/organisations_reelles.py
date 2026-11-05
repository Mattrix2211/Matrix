"""Inventaire des organisations de la démonstration et variantes d'organisation (transactions annulées)."""
import collections
from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User
from org.models import Ship, Service, Sector, Section
from accounts.models import UserProfile
from quarts.mouvements import mode_du_batiment
from quarts.models import FeuilleService, peut_viser_comaeq, ChefDeListe, ServiceGarde, Quart
from matrix.core.commandants_adjoints import titulaires_commandant_adjoint
for sh in Ship.objects.order_by("pk"):
    svc=Service.objects.filter(ship=sh); sec=Sector.objects.filter(service__ship=sh); sct=Section.objects.filter(sector__service__ship=sh)
    coma={f:titulaires_commandant_adjoint(sh,f,None).count() for f in ("COMAEQ","COMOPS","COMANAV","COMAVIA")} if True else {}
    rattach=dict(collections.Counter(svc.values_list("commandant_adjoint",flat=True)))
    roles=dict(collections.Counter(UserProfile.objects.filter(ship=sh).values_list("role",flat=True)))
    print("ORG",sh.name,"| type",sh.type_unite,"| classe",sh.classe_navire or "-","| double équipage",sh.double_equipage,"| mode",mode_du_batiment(sh),"| services",svc.count(),"secteurs",sec.count(),"sections",sct.count(),"| COMA titulaires",coma,"| rattachement des services aux COMA",rattach,"| effectif",UserProfile.objects.filter(ship=sh).count(),"| listes",Quart.objects.filter(ship=sh).count()+ServiceGarde.objects.filter(ship=sh).count())
print("ORG équipages présents:",dict(collections.Counter(UserProfile.objects.exclude(equipage="").values_list("equipage",flat=True))))
print("ORG fonctions COMA possibles:",[c[0] for c in UserProfile._meta.get_field("fonction_coma").choices])
# variante 1 : bâtiment sans titulaire COMAEQ (feuille : qui peut viser ?)
def u(n): return User.objects.get(username=n)
with transaction.atomic():
    f=FeuilleService.objects.filter(ship_id=2,equipage="A").first()
    avant={n:peut_viser_comaeq(u(n),f) for n in ("coma_comaeq","cdt_a","second_a","admin_navire","coma_comanav")}
    UserProfile.objects.filter(user__username="coma_comaeq").update(fonction_coma="")
    apres={n:peut_viser_comaeq(User.objects.get(username=n),f) for n in ("coma_comaeq","cdt_a","second_a","admin_navire","coma_comanav")}
    print("ORG variante COMAEQ vacant : peut viser avant",avant,"→ poste vacant",apres)
    transaction.set_rollback(True)
# variante 2 : un service rattaché à un COMAVIA désigné
with transaction.atomic():
    UserProfile.objects.filter(user__username="coma_comops").update(fonction_coma="COMAVIA")
    Service.objects.filter(ship_id=2,name__icontains="Opérations").update(commandant_adjoint="COMAVIA")
    print("ORG variante COMAVIA : titulaires COMAVIA du bâtiment 2 =",titulaires_commandant_adjoint(Ship.objects.get(pk=2),"COMAVIA","A").count(),"| COMOPS =",titulaires_commandant_adjoint(Ship.objects.get(pk=2),"COMOPS","A").count())
    transaction.set_rollback(True)
# variante 3 : installations sans secteur ou sans service
from assets.models import Installation
print("ORG installation : service obligatoire =",not Installation._meta.get_field("service").null,"| secteur obligatoire =",not Installation._meta.get_field("sector").null,"| section facultative =",Installation._meta.get_field("section").null)
from assets.models import InstallationBigrameChoice
print("ORG regroupement d'installations : catégories prédéfinies dans le code ?",[f.name for f in InstallationBigrameChoice._meta.fields],"| lignes en base:",InstallationBigrameChoice.objects.count())
