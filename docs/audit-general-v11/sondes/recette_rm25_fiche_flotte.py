# Recette RM-25 : fiche matériel flotte, circuit à 7 étapes (rédaction, secteur, service, commandant adjoint, vérification à terre, chef de spécialité, publication) puis adaptation au bord (écritures annulées).
import re
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from assets.models import Installation, InstallationMaintenance, ChecklistTemplate
from notifications.models import Notification
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def erreur(r): return [x.strip()[:140] for x in re.findall(r'alert[^>]*>([^<]{8,200})',r.content.decode()) if x.strip()][:2]
def etat(v): v.refresh_from_db(); return v.etat
def L(tag,u,r,extra=""): print(f"RM25 {tag:<66} {u:<17} HTTP {r.status_code} {extra}")
bord=InstallationMaintenance.objects.filter(niveau="BORD",installation__ship_id=2,installation__service_id=2).exclude(versions__isnull=True).first()
print("RM25 fiche de départ (bord, Bretagne) :",bord.pk,bord.title,"|",bord.installation.designation)
form={"name":bord.title,"description":"Proposée à la flotte (recette)","mode_declenchement":"calendrier","intervalle":"6","unite_intervalle":"M","duree_estimee_min":"45","nb_personnes":"2","etape_texte":["Consigner","Contrôler"],"etape_attention":["",""],"specialite":"2","equipement":bord.installation.designation,"reference_equipement":bord.installation.reference or "","classe_navire":""}
with transaction.atomic():
    for u in ("equipier_a","chef_service_a","terre_securite","terre_classe","chef_section_a"):
        r=cl(u).get(f"/fiches/{bord.pk}/proposer-flotte/",HTTP_HOST="localhost"); L("1. ouvrir « proposer à la flotte »",u,r)
    n=Notification.objects.count()
    r=cl("chef_section_a").post(f"/fiches/{bord.pk}/proposer-flotte/",form,HTTP_HOST="localhost",follow=True)
    v=ChecklistTemplate.objects.filter(fiche__niveau="FLOTTE").order_by("-id").first()
    L("2. proposition par le bord","chef_section_a",r,f"version={v and v.pk} état={v and v.etat} notifs+{Notification.objects.count()-n}")
    def viser(u,tag,etape=None):
        r=cl(u).post(f"/fiches/versions/{v.pk}/viser/",{"etape":etape or v.etat},HTTP_HOST="localhost",follow=True); L(tag,u,r,f"état→{etat(v)}")
    viser("chef_secteur_a","3a. visa du chef de secteur (bord)")
    viser("chef_service_a","3b. visa du chef de service (bord)")
    viser("terre_securite","3c. responsable de spécialité vise à l'étape COMA","visa_coma")
    viser("coma_comanav","3d. visa du commandant adjoint (bord)")
    # vérification à terre
    for u in ("terre_classe","chef_service_a","admin_navire","admin","terre_chef_securite"):
        r=cl(u).get(f"/fiches/versions/{v.pk}/verifier/",HTTP_HOST="localhost"); L("4a. ouvrir la vérification",u,r)
    r=cl("terre_securite").post(f"/fiches/versions/{v.pk}/verifier/",dict(form,description="Vérifiée : intervalle conforme à la doctrine"),HTTP_HOST="localhost",follow=True); L("4b. vérification et transmission","terre_securite",r,f"état→{etat(v)}")
    viser("terre_securite","5a. le vérificateur vise aussi (auto-validation ?)")
    viser("coma_comanav","5b. le COMA du bord vise à l'étape du chef de spécialité")
    viser("admin","5c. administrateur général vise")
    viser("terre_chef_securite","5d. visa du chef de la spécialité (terre)")
    fiche=v.fiche; fiche.refresh_from_db()
    print("RM25 6. résultat : état",v.etat,"| version applicable de la fiche flotte =",(fiche.version_validee.pk==v.pk) if fiche.version_validee else None,"| historique :",[(e.action,getattr(e.user,'username',None)) for e in v.evenements.order_by('id')])
    # adaptation au bord : installation équivalente d'un autre navire (Normandie) et du même navire
    from assets.fiche_adaptation import fiches_flotte_proposees
    for inst in Installation.objects.filter(designation=bord.installation.designation):
        print("RM25 7. installation",inst.pk,inst.ship,"| fiches flotte proposées :",[f.title for f in fiches_flotte_proposees(inst)])
    ib=bord.installation
    r=cl("chef_section_a").get(f"/installations/{ib.pk}/fiches/nouvelle/?depuis={fiche.pk}",HTTP_HOST="localhost"); L("7b. ouvrir l'adaptation de la fiche flotte pour l'installation d'origine","chef_section_a",r)
    r=cl("chef_section_a").post(f"/installations/{ib.pk}/fiches/nouvelle/?depuis={fiche.pk}",dict(form,intervalle="4",depuis=str(fiche.pk)),HTTP_HOST="localhost",follow=True)
    va=ChecklistTemplate.objects.filter(fiche__niveau="BORD").order_by("-id").first(); L("7c. adaptation proposée au circuit du bord","chef_section_a",r,f"état={va.etat} origine={va.fiche.origine_id}")
    print("RM25 7d. toutes les installations du parc et fiches flotte proposées :",{str(i.designation)[:25]+'/'+i.ship.name:len(fiches_flotte_proposees(i)) for i in Installation.objects.all() if fiches_flotte_proposees(i)})
    # 8. proposition d'une catégorie de matériel sans responsable de spécialité
    cat=[c for c in __import__('assets.models',fromlist=['CategorieCatalogue']).CategorieCatalogue.objects.all()]
    for c in cat[:2]:
        r=cl("chef_section_a").post(f"/catalogue/categories/{c.pk}/fiches/nouvelle/",dict(form,name="Fiche catégorie "+c.nom),HTTP_HOST="localhost",follow=True); v2=ChecklistTemplate.objects.filter(fiche__niveau="FLOTTE").order_by("-id").first(); L(f"8. fiche de catégorie « {c.nom} » par le bord","chef_section_a",r,f"état={v2.etat}")
    transaction.set_rollback(True)
