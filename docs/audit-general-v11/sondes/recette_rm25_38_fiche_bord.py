# Recette RM-25 / RM-38 : fiche d'installation du bord, circuit section→secteur→service→commandant adjoint (écritures annulées).
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from assets.models import Installation, InstallationMaintenance, ChecklistTemplate
from accounts.models import AuditLog
from notifications.models import Notification
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
inst=Installation.objects.get(designation="Pompe de graissage",section__name="Moteurs bâbord",ship__name="Bretagne")
def msgs(r):
    try: return "; ".join(str(m) for m in r.context["messages"])[:100]
    except Exception: return ""
def v_etat(v): v.refresh_from_db(); return v.etat
form={"name":"Contrôle trimestriel pompe de graissage (recette)","description":"Vérifier pression et fuites","mode_declenchement":"calendrier","intervalle":"3","unite_intervalle":"M","duree_estimee_min":"30","nb_personnes":"2","etape_texte":["Consigner la machine","Relever la pression"],"etape_attention":["",""],"ligne_label":["Pression huile"],"ligne_type":["number"],"ligne_unite":["bar"],"ligne_cle":[""],"ligne_min":["2"],"ligne_max":["6"]}
def ligne(tag,u,r,extra=""): print(f"RM38 {tag:<62} {u:<18} HTTP {r.status_code} {msgs(r)!r} {extra}")
with transaction.atomic():
    # 1. qui peut rédiger ?
    for u in ("equipier_a","chef_section_a","chef_secteur_a","chef_service_a","second_a","coma_comanav","admin_navire","chef_secteur_elec_a"):
        r=cl(u).get(f"/installations/{inst.pk}/fiches/nouvelle/",HTTP_HOST="localhost"); ligne("1. ouvrir l'assistant de rédaction",u,r)
    # 2. proposition par le chef de section
    n_notif=Notification.objects.count(); n_audit=AuditLog.objects.count()
    c=cl("chef_section_a"); r=c.post(f"/installations/{inst.pk}/fiches/nouvelle/",form,HTTP_HOST="localhost",follow=True)
    v=ChecklistTemplate.objects.filter(fiche__installation=inst).order_by("-id").first()
    ligne("2. proposition (chef de section)","chef_section_a",r,f"version={v.pk} état={v.etat} notifications+{Notification.objects.count()-n_notif} audit+{AuditLog.objects.count()-n_audit}")
    print("RM38    destinataires notifiés :",sorted(set(Notification.objects.order_by('-id')[:Notification.objects.count()-n_notif].values_list("user__username",flat=True))))
    def viser(u,etape=None,tag=""):
        etape=etape or v.etat
        r=cl(u).post(f"/fiches/versions/{v.pk}/viser/",{"etape":etape},HTTP_HOST="localhost",follow=True); ligne(tag or f"visa {etape}",u,r,f"état→{v_etat(v)}")
    # 3. visas hors rang, avant le bon visiteur
    viser("chef_section_a",tag="3a. auto-visa par le rédacteur (étape secteur)")
    viser("chef_secteur_elec_a",tag="3b. visa par un chef de secteur d'un autre secteur")
    viser("chef_service_a","visa_service","3c. saut d'étape : le chef de service vise avant le chef de secteur")
    viser("admin_navire","visa_secteur","3d. admin_navire vise à la place du chef de secteur")
    viser("admin","visa_secteur","3e. administrateur général vise à la place")
    viser("equipier_a","visa_secteur","3f. équipier tente un visa")
    # 4. refus puis correction
    r=cl("chef_secteur_a").post(f"/fiches/versions/{v.pk}/refuser/",{"etape":"visa_secteur","motif":""},HTTP_HOST="localhost",follow=True); ligne("4a. refus sans motif","chef_secteur_a",r,f"état→{v_etat(v)}")
    r=cl("chef_secteur_a").post(f"/fiches/versions/{v.pk}/refuser/",{"etape":"visa_secteur","motif":"Préciser la valeur de pression nominale"},HTTP_HOST="localhost",follow=True); ligne("4b. refus motivé","chef_secteur_a",r,f"état→{v_etat(v)}")
    fiche=v.fiche
    r=cl("chef_section_a").post(f"/fiches/{fiche.pk}/modifier/",dict(form,resume_modifications="Pression nominale ajoutée"),HTTP_HOST="localhost",follow=True); ligne("4c. correction et nouvelle proposition","chef_section_a",r,f"état→{v_etat(v)}")
    # 5. circuit nominal
    viser("chef_secteur_a",tag="5a. visa du chef de secteur")
    viser("chef_service_a",tag="5b. visa du chef de service")
    viser("second_a",tag="5c. visa : commandant en second (grade supérieur, non titulaire)")
    viser("coma_comaeq",tag="5d. visa : COMAEQ (autre fonction que COMANAV)")
    viser("cdt_a",tag="5e. visa : commandant")
    viser("coma_comanav",tag="5f. visa du commandant adjoint référent (COMANAV)")
    v.refresh_from_db(); fiche.refresh_from_db()
    print("RM38 6. résultat : version",v.etat,"| version validée de la fiche =",fiche.version_validee.pk if fiche.version_validee else None,"| publiée =",fiche.version_validee_id==v.pk if hasattr(fiche,'version_validee_id') else '?')
    print("RM38 6. historique de la version :",[(e.action,getattr(e.user,'username',None)) for e in v.evenements.order_by('id')])
    # 7. lecture de la fiche publiée par un équipier
    r=cl("equipier_a").get(f"/fiches/{fiche.pk}/",HTTP_HOST="localhost"); ligne("7. lecture de la fiche publiée","equipier_a",r)
    # 8. variante : un chef de secteur rédige (il ne vise pas sa propre étape)
    autre=Installation.objects.filter(sector_id=inst.sector_id).exclude(pk=inst.pk).first() or inst
    n=Installation.objects.filter(sector_id=inst.sector_id).count()
    r=cl("chef_secteur_a").post(f"/installations/{autre.pk}/fiches/nouvelle/",dict(form,name="Fiche rédigée par un chef de secteur",intervalle="2",unite_intervalle="S"),HTTP_HOST="localhost",follow=True)
    v2=ChecklistTemplate.objects.filter(fiche__isnull=False).order_by("-id").first(); print('RM38    erreur éventuelle :',[x for x in __import__('re').findall(r'alert[^>]*>([^<]{5,160})',r.content.decode())][:2]); ligne("8. un chef de secteur rédige : première étape","chef_secteur_a",r,f"installation={autre.designation!r} état={v2.etat} (secteur compte {n} installations)")
    # 9. commandant adjoint vacant : qui peut débloquer ?
    pf=User.objects.get(username="coma_comanav").profile; pf.fonction_coma=""; pf.save()
    r=cl("chef_section_a").post(f"/installations/{inst.pk}/fiches/nouvelle/",dict(form,name="Fiche avec COMA vacant",intervalle="1",unite_intervalle="A"),HTTP_HOST="localhost",follow=True)
    v3=ChecklistTemplate.objects.filter(fiche__isnull=False).order_by("-id").first()
    ligne("9. COMA du service non désigné : proposition","chef_section_a",r,f"état={v3.etat}")
    for u,e in (("chef_secteur_a","visa_secteur"),("chef_service_a","visa_service")):
        cl(u).post(f"/fiches/versions/{v3.pk}/viser/",{"etape":e},HTTP_HOST="localhost")
    v3.refresh_from_db(); print("RM38 9. après visas secteur et service, état =",v3.etat)
    for u in ("coma_comanav","second_a","cdt_a","admin_navire","admin"):
        r=cl(u).post(f"/fiches/versions/{v3.pk}/viser/",{"etape":"visa_coma"},HTTP_HOST="localhost",follow=True); v3.refresh_from_db(); ligne("9. visa avec COMA vacant",u,r,f"état→{v3.etat}")
    r=cl("chef_service_a").get(f"/fiches/{v3.fiche_id}/?v={v3.numero}",HTTP_HOST="localhost"); import re; t=r.content.decode(); print("RM38 9. texte d'absence affiché :",[x.strip()[:160] for x in re.findall(r"[^<>]*(?:désign|absent|vacant)[^<>]*",t)][:3])
    transaction.set_rollback(True)
