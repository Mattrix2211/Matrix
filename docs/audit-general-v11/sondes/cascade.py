from django.db.models.deletion import Collector, ProtectedError
from django.db import router
from org.models import Service, Sector, Section, Ship
def simul(obj):
    col=Collector(using=router.db_for_write(obj.__class__))
    try:
        col.collect([obj])
    except ProtectedError as e:
        return "PROTÉGÉ"
    n={m._meta.label:len(v) for m,v in col.data.items()}
    n.update({"(rattachements remis à NULL) "+m._meta.label:sum(len(o) for o in v.values()) for m,v in {}.items()})
    nul={}
    for (field,value),objs in col.field_updates.items():
        nul[f"{field.model._meta.label}.{field.name}"]=len(list(objs))
    return n,nul
for o in list(Service.objects.all())+list(Sector.objects.all())+list(Section.objects.all())+[Ship.objects.get(name="Normandie")]:
    r=simul(o); 
    print("CAS",o.__class__.__name__,str(o)[:48],"→",r if r=="PROTÉGÉ" else {k:v for k,v in r[0].items() if k.split('.')[-1] not in ('Section','Sector')}, "| mis à NULL:", r[1] if r!="PROTÉGÉ" else "")
