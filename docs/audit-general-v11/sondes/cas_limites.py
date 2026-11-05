import json
from datetime import timedelta
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction, router
from django.db.models.deletion import Collector, ProtectedError
from django.utils import timezone
from quarts.models import ServiceGarde, CreneauServiceGarde, Quart, CreneauQuart, ChefDeListe, RemplacementChefDeListe, EchangeService
from quarts.remplacement import designer_remplacant
from quarts.activation import ActivationImpossible
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
U=lambda n:User.objects.get(username=n)
# ---------- E1 : listes publiées
g=ServiceGarde.objects.filter(statut="PUBLIEE",equipage="A",ship_id=2).exclude(creneaux__isnull=True).first()
cr=g.creneaux.filter(marin__isnull=False).first(); print("EDG liste",g.pk,"créneaux",g.creneaux.count(),"| créneau",cr.pk,cr.poste,"marin",cr.marin)
u=f"/quarts/garde/{g.pk}/"
def essai(nom,acteur,data,verif):
    with transaction.atomic():
        r=cl(acteur).post(u,data,HTTP_HOST="localhost"); print("EDG",nom,"→",r.status_code,"|",verif()); transaction.set_rollback(True)
essai("retrait sans motif (cdt_a)","cdt_a",{"action":"supprimer_creneau","creneau_id":cr.pk},lambda:"créneau encore là: "+str(CreneauServiceGarde.objects.filter(pk=cr.pk).exists()))
essai("retrait avec motif (cdt_a)","cdt_a",{"action":"supprimer_creneau","creneau_id":cr.pk,"motif":"audit"},lambda:"créneau encore là: "+str(CreneauServiceGarde.objects.filter(pk=cr.pk).exists()))
ech=EchangeService.objects.filter(creneau_demandeur=cr).first() if hasattr(EchangeService,"creneau_demandeur") else None
print("EDG champs EchangeService:",[f.name for f in EchangeService._meta.fields][:12])
debut=timezone.now()+timedelta(days=30)
base={"action":"ajouter_creneau","poste":"Poste audit","debut":debut.strftime("%Y-%m-%dT%H:%M"),"fin":(debut+timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M")}
essai("ajout (cdt_a) marin du périmètre","cdt_a",{**base,"marin":cr.marin_id},lambda:"créneaux +"+str(CreneauServiceGarde.objects.filter(service_garde=g,poste="Poste audit").count()))
essai("ajout (cdt_a) marin d'un autre bâtiment","cdt_a",{**base,"marin":U("marin_abe_1").pk},lambda:"créneaux +"+str(CreneauServiceGarde.objects.filter(service_garde=g,poste="Poste audit").count()))
essai("ajout (cdt_a) fin avant début","cdt_a",{**base,"fin":(debut-timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),"marin":cr.marin_id},lambda:"créneaux +"+str(CreneauServiceGarde.objects.filter(service_garde=g,poste="Poste audit").count()))
essai("ajout en double clic (2 requêtes identiques)","cdt_a",{**base,"marin":cr.marin_id},lambda:"")
with transaction.atomic():
    c=cl("cdt_a"); c.post(u,{**base,"marin":cr.marin_id},HTTP_HOST="localhost"); c.post(u,{**base,"marin":cr.marin_id},HTTP_HOST="localhost")
    print("EDG double soumission : créneaux identiques créés =",CreneauServiceGarde.objects.filter(service_garde=g,poste="Poste audit").count()); transaction.set_rollback(True)
with transaction.atomic():
    cl("cdt_a").post(u,{"action":"publier"},HTTP_HOST="localhost"); r=cl("cdt_a").post(u,{"action":"publier"},HTTP_HOST="localhost"); g.refresh_from_db(); print("EDG publier une liste déjà publiée → statut",g.statut,"| version",getattr(g,"version_publiee",None)); transaction.set_rollback(True)
# traçabilité des modifications
from accounts.models import AuditLog
with transaction.atomic():
    n0=AuditLog.objects.count(); cl("cdt_a").post(u,{"action":"supprimer_creneau","creneau_id":cr.pk,"motif":"audit tracé"},HTTP_HOST="localhost"); print("EDG lignes d'audit ajoutées par un retrait motivé:",AuditLog.objects.count()-n0,[a.action for a in AuditLog.objects.order_by('-pk')[:2]]); transaction.set_rollback(True)
# ---------- E2 : délégations (remplacement de chef de liste)
des=ChefDeListe.objects.filter(type_liste="QUAI").first(); print("EDG désignation QUAI:",des.pk,des.user.username)
now=timezone.now()+timedelta(days=10); marin=U("equipier_a2"); autre_ship=U("marin_abe_1")
def tente(nom,**kw):
    args=dict(auteur=U("chef_service_a"),designation=des,remplacant=marin,debut=now+timedelta(minutes=10),fin=now+timedelta(hours=8),motif="audit"); args.update(kw)
    with transaction.atomic():
        try: designer_remplacant(**args); print("EDG remplacement",nom,"→ ACCEPTÉ"); 
        except ActivationImpossible as e: print("EDG remplacement",nom,"→ refusé :",str(e)[:80])
        transaction.set_rollback(True)
tente("normal"); tente("se remplacer soi-même",remplacant=des.user); tente("remplaçant d'un autre bâtiment",remplacant=autre_ship); tente("sans motif",motif=" ")
tente("dans le passé",debut=timezone.now()-timedelta(hours=2),fin=timezone.now()+timedelta(hours=1)); tente("fin avant début",fin=now); tente("durée 200 h",fin=now+timedelta(hours=200))
u2=marin; u2.is_active=False
with transaction.atomic():
    marin.is_active=False; marin.save()
    try: designer_remplacant(auteur=U("chef_service_a"),designation=des,remplacant=marin,debut=now+timedelta(minutes=10),fin=now+timedelta(hours=8),motif="audit"); print("EDG remplacement d'un compte désactivé → ACCEPTÉ")
    except ActivationImpossible as e: print("EDG remplacement d'un compte désactivé → refusé :",str(e)[:60])
    transaction.set_rollback(True)
marin=U("equipier_a2")
with transaction.atomic():
    r1=designer_remplacant(auteur=U("chef_service_a"),designation=des,remplacant=marin,debut=now+timedelta(minutes=10),fin=now+timedelta(hours=8),motif="audit")
    try: designer_remplacant(auteur=U("chef_service_a"),designation=des,remplacant=U("equipier_a"),debut=now+timedelta(hours=1),fin=now+timedelta(hours=6),motif="audit"); print("EDG chevauchement du même titulaire avec un autre remplaçant → ACCEPTÉ")
    except ActivationImpossible as e: print("EDG chevauchement du même titulaire → refusé :",str(e)[:70])
    # droits effectifs du remplaçant (pendant la période)
    RemplacementChefDeListe.objects.filter(pk=r1.pk).update(debut=timezone.now()-timedelta(minutes=1),fin=timezone.now()+timedelta(hours=5))
    gq=ServiceGarde.objects.filter(statut="PUBLIEE",ship_id=2).first()
    for act in ("publier","ajouter_creneau","regler_echanges"):
        rr=cl("equipier_a2").post(f"/quarts/garde/{gq.pk}/",{"action":act},HTTP_HOST="localhost"); print("EDG remplaçant (en cours) action",act,"→",rr.status_code)
    rr=cl("equipier_a2").post("/quarts/reglages/",{"action":"remplacer","ship":2},HTTP_HOST="localhost"); print("EDG remplaçant désigne un remplaçant (transitivité) →",rr.status_code)
    RemplacementChefDeListe.objects.filter(pk=r1.pk).update(fin=timezone.now()-timedelta(seconds=30),debut=timezone.now()-timedelta(hours=1))
    rr=cl("equipier_a2").post(f"/quarts/garde/{gq.pk}/",{"action":"activer"},HTTP_HOST="localhost"); print("EDG remplaçant APRÈS expiration, action activer →",rr.status_code)
    transaction.set_rollback(True)
# ---------- E3 : suppression et archivage, cas limites
def simul(obj):
    col=Collector(using=router.db_for_write(obj.__class__))
    try: col.collect([obj])
    except ProtectedError: return "protégé"
    n={m._meta.label:len(v) for m,v in col.data.items()}
    return {k:v for k,v in n.items() if k.split(".")[-1] not in ("Section","Sector","Service")}
from org.models import Service, Sector, Section, Ship
for s in Service.objects.filter(ship__name__in=["Jacques Chevallier","Auguste Bénébig"]): print("EDG cascade service",s,simul(s))
for sh in Ship.objects.filter(name__in=["Auguste Bénébig","Jacques Chevallier"]): print("EDG cascade bâtiment",sh,simul(sh))
us=U("equipier_a"); print("EDG cascade suppression d'un compte (equipier_a):",simul(us))
from accounts.models import AuditLog as AL
print("EDG AuditLog.actor on_delete :",AL._meta.get_field("actor").remote_field.on_delete.__name__)
# archivage : double archivage, archivage d'une unité occupée par API
import json as j
a=cl("admin_navire"); sc=Section.objects.get(name="Moteurs bâbord")
with transaction.atomic():
    r1=a.patch(f"/api/org/sections/{sc.pk}/",j.dumps({"archived":True}),content_type="application/json",HTTP_HOST="localhost"); r2=a.patch(f"/api/org/sections/{sc.pk}/",j.dumps({"archived":True}),content_type="application/json",HTTP_HOST="localhost")
    print("EDG archivage deux fois →",r1.status_code,r2.status_code)
    sec=sc.sector; r3=a.patch(f"/api/org/sectors/{sec.pk}/",j.dumps({"archived":True}),content_type="application/json",HTTP_HOST="localhost"); print("EDG archivage d'un secteur dont les sections sont actives →",r3.status_code,"| sections encore actives:",sec.sections.filter(archived=False).count())
    r4=a.patch(f"/api/org/sections/{sc.pk}/",j.dumps({"sector":Sector.objects.exclude(pk=sec.pk).first().pk}),content_type="application/json",HTTP_HOST="localhost"); print("EDG déplacement d'une section vers un autre secteur (API) →",r4.status_code, "| profils de la section ont-ils encore section_id cohérent:",all(p.section_id==sc.pk for p in sc.profiles.all()))
    transaction.set_rollback(True)
