# Recette RM-41 : prêt à appareiller (ouverture, pointage, signature avec confirmation explicite, droits de saisie). Écritures annulées.
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from dashboard.models import SessionAppareillage, ItemAppareillage
from accounts.models import AuditLog
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def L(tag,u,r,extra=""): print(f"RM41 {tag:<64} {u:<19} HTTP {r.status_code} {extra}")
print("RM41 sessions en démonstration :",[(s.pk,s.ship.name,"ouverte" if s.est_ouverte else "clôturée") for s in SessionAppareillage.objects.all()])
with transaction.atomic():
    SessionAppareillage.objects.filter(ship_id=2,cloturee_le__isnull=True).delete()
    for u in ("equipier_a","chef_section_a","chef_secteur_a","chef_service_a","second_a","cdt_a","admin_navire"):
        r=cl(u).get("/dashboard/pret-appareillage/",HTTP_HOST="localhost"); L("1. consulter la page",u,r)
    for u in ("equipier_a","chef_section_a"):
        n=SessionAppareillage.objects.count(); r=cl(u).post("/dashboard/pret-appareillage/ouvrir/",HTTP_HOST="localhost"); L("2. ouvrir une session",u,r,f"sessions+{SessionAppareillage.objects.count()-n}")
    r=cl("chef_secteur_a").post("/dashboard/pret-appareillage/ouvrir/",HTTP_HOST="localhost",follow=True); s=SessionAppareillage.objects.filter(ship_id=2,cloturee_le__isnull=True).first()
    items=list(s.items.all()); L("2b. ouvrir une session","chef_secteur_a",r,f"items={len(items)} par catégorie={ {c:sum(1 for i in items if i.categorie==c) for c in sorted(set(i.categorie for i in items))} }")
    # 3. pointage par différents profils
    for u,it in (("equipier_a",items[0]),("equipier_elec_a",items[1] if len(items)>1 else items[0]),("marin_b",items[0]),("marin_abe_1",items[0]),("terre_classe",items[0])):
        r=cl(u).post(f"/dashboard/pret-appareillage/item/{it.pk}/cocher/",HTTP_HOST="localhost",HTTP_HX_REQUEST="true"); it.refresh_from_db(); L(f"3. pointer « {it.libelle[:34]} »" if hasattr(it,'libelle') else "3. pointer un point",u,r,f"vérifié_par={it.verifie_par}")
    print("RM41 3. attributs d'un point :",[f.name for f in ItemAppareillage._meta.fields])
    # 4. signature
    ni=s.items.filter(verifie_par__isnull=True).count(); print("RM41 4. points non vérifiés avant signature :",ni,"/",s.items.count())
    for u in ("equipier_a","chef_section_a"):
        r=cl(u).post(f"/dashboard/pret-appareillage/session/{s.pk}/signer/",{"confirmation":"1"},HTTP_HOST="localhost"); s.refresh_from_db(); L("4a. signer",u,r,f"clôturée={bool(s.cloturee_le)}")
    r=cl("chef_secteur_a").post(f"/dashboard/pret-appareillage/session/{s.pk}/signer/",HTTP_HOST="localhost",follow=True); s.refresh_from_db(); L("4b. signer sans case de confirmation","chef_secteur_a",r,f"clôturée={bool(s.cloturee_le)}")
    print("RM41 4b. trace du refus :",list(AuditLog.objects.filter(action="validation_critique_refusee").values_list("actor__username","details"))[-1:])
    r=cl("chef_secteur_a").post(f"/dashboard/pret-appareillage/session/{s.pk}/signer/",{"confirmation":"1"},HTTP_HOST="localhost",follow=True); s.refresh_from_db()
    L(f"4c. signer avec confirmation alors que {ni} points ne sont pas vérifiés","chef_secteur_a",r,f"clôturée={bool(s.cloturee_le)} valideur={s.valide_par}")
    print("RM41 4c. trace :",[a.details[:230] for a in AuditLog.objects.filter(action="session_appareillage_validation").order_by("-id")[:1]])
    r=cl("cdt_a").post(f"/dashboard/pret-appareillage/session/{s.pk}/signer/",{"confirmation":"1"},HTTP_HOST="localhost",follow=True); L("4d. signer une session déjà clôturée","cdt_a",r)
    it=items[2] if len(items)>2 else items[0]
    r=cl("equipier_a").post(f"/dashboard/pret-appareillage/item/{it.pk}/cocher/",HTTP_HOST="localhost",HTTP_HX_REQUEST="true"); L("5. pointer après clôture","equipier_a",r)
    # 6. historique
    for u in ("equipier_a","chef_secteur_a","cdt_a","admin"):
        r=cl(u).get("/dashboard/pret-appareillage/historique/",HTTP_HOST="localhost"); L("6. historique des sessions",u,r)
    # 7. signature par le chef de secteur qui a lui-même pointé tous les points (séparation des tâches)
    transaction.set_rollback(True)
