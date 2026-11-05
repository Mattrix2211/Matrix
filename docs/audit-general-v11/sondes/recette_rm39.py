# Recette RM-39 : RETEX proposé → validé par les habilités (COMA référent d'abord) → document publié → actions → clôture. Écritures annulées.
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from retex.models import Retex, DomaineRetex
from retex import services
from notifications.models import Notification
from documentation.models import Document
from taches.models import Tache
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def L(tag,u,r,extra=""): print(f"RM39 {tag:<64} {u:<17} HTTP {r.status_code} {extra}")
print("RM39 RETEX en démonstration :",[(r.titre[:30],r.etat) for r in Retex.objects.all()])
with transaction.atomic():
    dom=services.domaines_du_navire(2)
    print("RM39 domaines du bâtiment et COMA référent :",[(d.nom,d.coma) for d in dom])
    d=[x for x in dom if x.coma][0]
    n=Notification.objects.count()
    r=cl("equipier_a").post("/retex/nouveau/",{"titre":"Fuite récurrente joint pompe","constat":"Fuite constatée 3 fois en 2 mois","enseignement":"Changer le joint à 500 h","domaine":d.pk,"diffusion":"BATIMENT"},HTTP_HOST="localhost",follow=True)
    rt=Retex.objects.order_by("-id").first(); L("1. proposition par un équipier","equipier_a",r,f"état={rt.etat} domaine={rt.domaine.nom} (COMA référent « {rt.domaine.coma} »)")
    dest=list(Notification.objects.order_by("-id")[:Notification.objects.count()-n].values_list("user__username","user__profile__fonction_service"))
    print("RM39 1. habilités prévenus, dans l'ordre :",dest, "| ordre de valideurs():",[u.username for u in services.valideurs(rt)])
    pf=User.objects.get(username="coma_comops").profile; pf.fonction_service="Commandant adjoint COMOPS"; pf.save()
    d2=DomaineRetex.objects.get(ship_id=2,coma="COMOPS"); rt.domaine=d2; 
    print("RM39 1bis. domaine COMOPS, texte libre de fonction renseigné → ordre :",[u.username for u in services.valideurs(rt)][:3],"| fonction_coma des COMA :",{u.username:u.profile.fonction_coma for u in services.valideurs(rt) if u.username.startswith("coma")})
    rt.domaine=d; pf.fonction_service=""; pf.save()
    for u in ("marin_b","equipier_a2","chef_section_a","chef_secteur_a"):
        r=cl(u).get(f"/retex/{rt.pk}/",HTTP_HOST="localhost"); L("2. lecture d'un RETEX proposé (non validé)",u,r)
    for u in ("chef_section_a","chef_secteur_a","equipier_a"):
        r=cl(u).post(f"/retex/{rt.pk}/action/",{"action":"valider"},HTTP_HOST="localhost",follow=True); rt.refresh_from_db(); L("3. tentative de validation sans être habilité",u,r,f"état={rt.etat}")
    # le COMA référent d'un autre domaine, puis un chef de service d'un service sans rapport, peuvent-ils valider ?
    print("RM39 3. seuil de validation :",__import__('matrix.core.role_thresholds',fromlist=['x']).seuil_role("retex_validation",2))
    r=cl("chef_service_a").post(f"/retex/{rt.pk}/action/",{"action":"refuser","motif":""},HTTP_HOST="localhost",follow=True); rt.refresh_from_db(); L("4a. refus sans motif","chef_service_a",r,f"état={rt.etat}")
    r=cl("coma_comaeq" if "sécur" in d.nom.lower() or "Sécur" in d.nom else "coma_comanav").post(f"/retex/{rt.pk}/action/",{"action":"valider","motif":"Pertinent"},HTTP_HOST="localhost",follow=True); rt.refresh_from_db()
    L("4b. validation par le COMA référent ("+d.coma+")","coma",r,f"état={rt.etat} décidé_par={rt.decide_par} document={rt.document_id}")
    if rt.etat!="VALIDE":
        r=cl("chef_service_a").post(f"/retex/{rt.pk}/action/",{"action":"valider","motif":"ok"},HTTP_HOST="localhost",follow=True); rt.refresh_from_db(); L("4c. validation par un chef de service","chef_service_a",r,f"état={rt.etat}")
    doc=rt.document
    print("RM39 5. document publié :",doc and (doc.titre,doc.domaine,[ (v.numero,v.etat) for v in doc.versions.all()]) )
    for u in ("equipier_a2","marin_b","marin_abe_1"):
        r=cl(u).get(f"/documentation/{doc.pk}/",HTTP_HOST="localhost") if doc else None; L("5. lecture du document RETEX publié",u,r) if r else None
    print("RM39 5. notification à l'auteur :",Notification.objects.filter(user__username="equipier_a").order_by("-id").values_list("verb",flat=True).first())
    # 6. actions → tâches
    r=cl("chef_service_a").post(f"/retex/{rt.pk}/action/",{"action":"creer_action","assigne":User.objects.get(username="equipier_a2").pk,"titre":"Changer le joint","echeance":"2026-12-15"},HTTP_HOST="localhost",follow=True)
    L("6a. création d'une action (tâche assignée)","chef_service_a",r,f"tâches liées={rt.taches.count()} statut={[t.statut for t in rt.taches.all()]}")
    r=cl("chef_service_a").post(f"/retex/{rt.pk}/action/",{"action":"clore"},HTTP_HOST="localhost",follow=True); rt.refresh_from_db(); L("6b. clôture avec action ouverte","chef_service_a",r,f"état={rt.etat}")
    print("RM39 6. statuts de tâche :",list(dict(Tache._meta.get_field("statut").choices)))
    for t in rt.taches.all(): t.statut=[k for k in dict(Tache._meta.get_field("statut").choices) if k not in Tache.STATUTS_OUVERTS][0]; t.save()
    r=cl("chef_service_a").post(f"/retex/{rt.pk}/action/",{"action":"clore"},HTTP_HOST="localhost",follow=True); rt.refresh_from_db(); L("6c. clôture une fois les actions terminées","chef_service_a",r,f"état={rt.etat}")
    transaction.set_rollback(True)
