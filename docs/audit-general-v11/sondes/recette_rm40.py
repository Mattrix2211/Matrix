# Recette RM-40 : relève de double équipage (proposition, validation par l'autre équipage, date d'effet, fuseau, application, passation, lecture seule). Écritures annulées.
import re
from datetime import timedelta
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from org.models import Ship, ReleveEquipage
from org.models import SynthesePassation
from matrix.core.equipage import equipage_a_bord, equipage_a_terre_lecture_seule, releve_en_attente, releve_planifiee
from notifications.models import Notification
from accounts.models import AuditLog
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def L(tag,u,r,extra=""): print(f"RM40 {tag:<66} {u:<15} HTTP {r.status_code} {extra}")
def flash(r):
    import html
    t=r.content.decode(errors="ignore")
    return " | ".join(html.unescape(re.sub(r"<[^>]+>","",m)).strip()[:110] for m in re.findall(r'class="toast[^>]*>(.*?)</div>\s*</div>|class="toast[^>]*>(.*?)</button>',t,re.S) for m in m if m.strip())[:200]
nav=Ship.objects.get(pk=2)
print("RM40 départ : équipage à bord =",equipage_a_bord(nav),"| fuseau",nav.fuseau_horaire,"| relèves existantes :",list(ReleveEquipage.objects.values_list("equipage_propose","statut")))
def post(u,data):
    return cl(u).post("/parametre/",dict(data,tab="equipage"),HTTP_HOST="localhost",follow=True)
dem=(timezone.localtime(timezone.now(),timezone.zoneinfo.ZoneInfo("Europe/Paris"))+timedelta(days=2)).strftime("%Y-%m-%dT%H:%M") if hasattr(timezone,'zoneinfo') else None
import zoneinfo
dem=(timezone.now().astimezone(zoneinfo.ZoneInfo("Europe/Paris"))+timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
hier=(timezone.now().astimezone(zoneinfo.ZoneInfo("Europe/Paris"))-timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
with transaction.atomic():
    a_bord=equipage_a_bord(nav); autre="B" if a_bord=="A" else "A"
    cdt_bord,cdt_autre=("cdt_a","cdt_b") if a_bord=="A" else ("cdt_b","cdt_a")
    ex=releve_en_attente(nav)
    print("RM40 0. relève déjà en attente dans la démonstration : équipage",ex.equipage_propose,"proposée par",ex.propose_par,"pour le",ex.date_effet)
    sp=transaction.savepoint()
    r=post("cdt_b",{"action":"decider_releve","decision":"valider"}); ex.refresh_from_db()
    print("RM40 0b. la relève de démonstration (sans date d'effet) validée par cdt_b → HTTP",r.status_code,"| statut",ex.statut,"| à bord =",equipage_a_bord(nav),"|",flash(r)[:140])
    transaction.savepoint_rollback(sp)
    r=post(ex.propose_par.username,{"action":"annuler_releve"}); print("RM40 0. annulée par son auteur →",r.status_code,"| en attente =",bool(releve_en_attente(nav)))
    # 1. qui peut proposer
    for u in ("equipier_a","chef_service_a","admin_navire"):
        r=post(u,{"action":"proposer_releve","equipage":autre,"date_effet":dem}); L("1. proposer une relève",u,r,f"relève en attente={bool(releve_en_attente(nav))} | {flash(r)}")
    r=post(cdt_bord,{"action":"proposer_releve","equipage":autre,"date_effet":hier}); L("1b. date d'effet dans le passé",cdt_bord,r,f"en attente={bool(releve_en_attente(nav))} | {flash(r)}")
    r=post(cdt_bord,{"action":"proposer_releve","equipage":a_bord,"date_effet":dem}); L("1c. relever l'équipage déjà à bord",cdt_bord,r,f"en attente={bool(releve_en_attente(nav))} | {flash(r)}")
    n=Notification.objects.count()
    r=post(cdt_bord,{"action":"proposer_releve","equipage":autre,"date_effet":dem}); rel=releve_en_attente(nav)
    L(f"2. proposition valide : équipage {autre} le {dem} (heure locale Paris)",cdt_bord,r,f"en attente={bool(rel)} date_effet(UTC)={rel and rel.date_effet} notifiés={sorted(set(Notification.objects.order_by('-id')[:Notification.objects.count()-n].values_list('user__username',flat=True)))}")
    # 3. validation
    for u,tag in ((cdt_bord,"3a. le proposant valide lui-même"),("second_a" if a_bord=="A" else cdt_bord,"3b. le second de l'équipage proposant valide"),("equipier_a","3c. un équipier valide"),("admin_navire","3d. l'admin du bâtiment valide"),("admin","3e. l'admin général valide (hors secours)")):
        r=post(u,{"action":"decider_releve","decision":"valider"}); rel2=releve_en_attente(nav); L(tag,u,r,f"encore en attente={bool(rel2)} | {flash(r)}")
    r=post(cdt_autre,{"action":"decider_releve","decision":"valider"}); pl=releve_planifiee(nav)
    L("3f. validation par le commandant de l'autre équipage",cdt_autre,r,f"planifiée={bool(pl)} | à bord toujours={equipage_a_bord(nav)} | {flash(r)}")
    print("RM40 3f. audit :",list(AuditLog.objects.filter(action__startswith="releve").order_by("id").values_list("action","details"))[-2:])
    for u in (cdt_bord,"admin_navire"):
        r=post(u,{"action":"modifier_fuseau","fuseau_horaire":"Pacific/Noumea"}); nav.refresh_from_db(); L("3g. changer le fuseau du bâtiment (équipage à bord)",u,r,f"fuseau={nav.fuseau_horaire} | {flash(r)[:90]}")
        nav.fuseau_horaire="Europe/Paris"; nav.save()
    # 4. avant la date d'effet : pas de bascule ; lecture/écriture des équipages
    print("RM40 4. avant la date d'effet : à bord =",equipage_a_bord(nav),"| équipier A lecture seule =",equipage_a_terre_lecture_seule(User.objects.get(username="equipier_a")))
    # 5. date d'effet atteinte (simulation : on avance la date de la relève planifiée)
    pl.date_effet=timezone.now()-timedelta(minutes=1); pl.save(update_fields=["date_effet"])
    print("RM40 5. date d'effet atteinte (sans action humaine) : à bord =",equipage_a_bord(nav),"| statut de la relève =",ReleveEquipage.objects.get(pk=pl.pk).statut)
    for u in ("equipier_a","chef_service_a","second_a","cdt_a","equipier_a2","marin_b","cdt_b"):
        us=User.objects.get(username=u); r=cl(u).get("/maintenance/occurrences/",HTTP_HOST="localhost"); 
        print(f"RM40 5. {u:<14} équipage {us.profile.equipage or '-'} lecture seule = {equipage_a_terre_lecture_seule(us)}")
    from annonces.models import Annonce; na=Annonce.objects.count(); r=cl("equipier_a").post("/annonces/nouvelle/",{"titre":"test","corps":"x","contenu":"x"},HTTP_HOST="localhost"); L("5b. équipier de l'équipage à terre tente d'écrire (annonce)","equipier_a",r,f"annonces+{Annonce.objects.count()-na}")
    r=cl("chef_section_a").post("/postes/nouveau/",{"intitule":"x","cible":"ship:2"},HTTP_HOST="localhost"); L("5c. chef de l'équipage à terre tente d'écrire (poste)","chef_section_a",r)
    # 6. passation
    for u in (cdt_autre,cdt_bord,"equipier_a","admin_navire"):
        r=post(u,{"action":"generer_passation"}); L("6. générer la synthèse de passation",u,r,f"synthèses={SynthesePassation.objects.count()} {flash(r)[:80]}")
    # 7. changement de fuseau
    for u,tz in ((cdt_bord,"Pacific/Noumea"),("admin_navire","Pacific/Noumea"),("admin","Pacific/Noumea")):
        r=post(u,{"action":"modifier_fuseau","fuseau_horaire":tz,"ship_id":2}); nav.refresh_from_db(); L(f"7. changer le fuseau en {tz}",u,r,f"fuseau={nav.fuseau_horaire}"); 
    # 8. relève planifiée annulée
    transaction.set_rollback(True)
