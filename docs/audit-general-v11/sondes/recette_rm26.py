# Recette RM-26 : travail terminé ≠ matériel disponible (contrôle, essais, retour en service). Écritures annulées.
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from assets.models import Asset, Installation
from logistics.models import CorrectiveTicket, TicketStatusLog
from accounts.models import AuditLog
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def st(t): t.refresh_from_db(); return t.status
def L(tag,u,r,extra=""): print(f"RM26 {tag:<66} {u:<17} HTTP {r.status_code} {extra}")
def go(t,u,statut,**kw):
    d={"status":statut}; d.update(kw)
    return cl(u).post(f"/logistics/tickets/{t.pk}/transition/",d,HTTP_HOST="localhost",follow=True)
from logistics.perimetre import perimetre_tickets_q
PERIM=CorrectiveTicket.objects.filter(perimetre_tickets_q(User.objects.get(username="chef_section_a")))
tk=PERIM.filter(status="REPORTED").first()
eq=tk.installation or tk.asset
print("RM26 ticket",tk.pk,tk.status,"sur",eq,"| statut de l'équipement :",getattr(eq,"status",None) if tk.asset_id else "installation (pas de champ statut)")
asset_tk=CorrectiveTicket.objects.filter(asset__isnull=False,asset__ship_id=2).exclude(status="CLOSED").first() if hasattr(Asset,'ship_id') else None
with transaction.atomic():
    # 1. qui peut changer le statut
    for u in ("equipier_a","equipier_a2","chef_section_a","chef_secteur_a","chef_service_a","second_a","cdt_a","admin_navire","chef_secteur_elec_a"):
        r=go(tk,u,"DIAGNOSED"); L("1. REPORTED → DIAGNOSED",u,r,f"état→{st(tk)}"); tk.status="REPORTED"; tk.save(update_fields=["status"])
    # 2. saut direct vers la remise en service, sans réparation ni essais
    r=go(tk,"chef_section_a","RETURNED_TO_SERVICE"); L("2a. REPORTED → RETURNED_TO_SERVICE sans case de confirmation","chef_section_a",r,f"état→{st(tk)}")
    r=go(tk,"chef_section_a","RETURNED_TO_SERVICE",confirmation="1"); L("2b. REPORTED → RETURNED_TO_SERVICE avec confirmation (aucune réparation, aucun essai)","chef_section_a",r,f"état→{st(tk)} valideur={tk.valide_par}")
    tk.status="REPORTED"; tk.valide_par=None; tk.save()
    r=go(tk,"chef_section_a","CLOSED",diagnostic_final="RAS",solution="RAS"); L("2c. REPORTED → CLOSED directement avec un REX de deux lettres","chef_section_a",r,f"état→{st(tk)}")
    tk.status="REPORTED"; tk.save()
    r=go(tk,"chef_section_a","N_IMPORTE_QUOI"); L("2d. statut inexistant","chef_section_a",r,f"état→{st(tk)}")
    # 3. parcours nominal complet
    tk.status="REPORTED"; tk.save()
    for u,s,kw in (("chef_section_a","DIAGNOSED",{}),("chef_section_a","IN_REPAIR",{}),("chef_section_a","TESTING",{}),("chef_secteur_a","RETURNED_TO_SERVICE",{"confirmation":"1"}),("chef_section_a","CLOSED",{"diagnostic_final":"Joint HS","solution":"Remplacé"})):
        r=go(tk,u,s,**kw); L(f"3. → {s}",u,r,f"état→{st(tk)} valideur={tk.valide_par} date={tk.date_validation and tk.date_validation.date()}")
    print("RM26 3. journal des statuts :",list(TicketStatusLog.objects.filter(ticket=tk).order_by("id").values_list("old_status","new_status","user__username")))
    print("RM26 3. audit :",[(a.action,a.details[:140]) for a in AuditLog.objects.filter(details__contains=str(tk.pk)).order_by("id")][-3:])
    # 4. retour arrière depuis CLOSED
    r=go(tk,"chef_section_a","REPORTED"); L("4. CLOSED → REPORTED (réouverture)","chef_section_a",r,f"état→{st(tk)}")
    # 5. séparation des fonctions : l'auteur de la réparation peut-il valider ?
    tk.status="TESTING"; tk.save()
    r=go(tk,"chef_section_a","RETURNED_TO_SERVICE",confirmation="1"); L("5. le chef de section remet en service (niveau le plus bas autorisé)","chef_section_a",r,f"état→{st(tk)}")
    # 6. effet sur l'état du matériel
    if tk.asset_id:
        a=tk.asset; print("RM26 6. matériel",a,"statut",a.status,"état plan",a.etat_plan)
    transaction.set_rollback(True)
# 7. matériel mobile : un ticket sur un matériel défectueux
with transaction.atomic():
    t2=CorrectiveTicket.objects.filter(asset__isnull=False).exclude(status__in=["CLOSED","RETURNED_TO_SERVICE"]).first()
    if t2:
        a=t2.asset; a.status="FAULTY"; a.save(update_fields=["status"])
        print("RM26 7. matériel",a,"déclaré FAULTY, ticket",t2.status,"→ état plan",a.etat_plan)
        t2.status="TESTING"; t2.save(); c=cl("admin")
        r=c.post(f"/logistics/tickets/{t2.pk}/transition/",{"status":"RETURNED_TO_SERVICE","confirmation":"1"},HTTP_HOST="localhost",follow=True); a.refresh_from_db(); t2.refresh_from_db()
        print("RM26 7. après remise en service validée : ticket",t2.status,"| matériel statut",a.status,"| état plan",a.etat_plan,"(HTTP",r.status_code,")")
    transaction.set_rollback(True)
print("RM26 8. tickets sur matériel mobile dans la démonstration :",CorrectiveTicket.objects.filter(asset__isnull=False).count(),"| sur installations :",CorrectiveTicket.objects.filter(installation__isnull=False).count())
