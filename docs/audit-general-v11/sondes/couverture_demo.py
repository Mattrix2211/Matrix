"""Couverture des données de démonstration : par profil (données propres) et par machine à états (états absents)."""
import collections
from django.apps import apps
from django.db.models import Q
from django.contrib.auth.models import User
def M(label): return apps.get_model(label)
def essai(f):
    try: return f()
    except Exception as e: return "?"
profils=["equipier_a","equipier_a2","marin_b","chef_section_a","chef_secteur_a","chef_service_a","coma_comaeq","coma_comanav","coma_comops","second_a","cdt_a","admin_navire","terre_classe","marin_abe_1","cdt_abe","m_chevalier"]
def champ(model,*noms):
    for n in noms:
        try: model._meta.get_field(n); return n
        except Exception: pass
    return None
cols={
 "taches":lambda u:M("taches.Tache").objects.filter(assigne=u).count(),
 "maint.":lambda u:M("maintenance.MaintenanceOccurrence").objects.filter(assignees=u).count(),
 "tickets":lambda u:M("logistics.CorrectiveTicket").objects.filter(assignees=u).count(),
 "quarts":lambda u:M("quarts.CreneauQuart").objects.filter(marin=u).count(),
 "gardes":lambda u:M("quarts.CreneauServiceGarde").objects.filter(marin=u).count(),
 "échanges":lambda u:M("quarts.EchangeService").objects.filter(Q(demandeur=u)|Q(cible=u)).count(),
 "absences":lambda u:M("absences.Absence").objects.filter(**{champ(M("absences.Absence"),"marin","user","utilisateur"):u}).count(),
 "qualif.":lambda u:M("training.TrainingRecord").objects.filter(**{champ(M("training.TrainingRecord"),"marin","user","utilisateur"):u}).count(),
 "notif.":lambda u:M("notifications.Notification").objects.filter(user=u).count(),
 "annonces lues":lambda u:M("annonces.LectureAnnonce").objects.filter(user=u).count() if "LectureAnnonce" in [m.__name__ for m in apps.get_app_config("annonces").get_models()] else "?",
 "postes":lambda u:M("postes.AffectationPoste").objects.filter(user=u).count(),
 "brouillons":lambda u:M("core.Brouillon").objects.filter(user=u).count() if essai(lambda:M("core.Brouillon")) != "?" else "?",
 "désign.":lambda u:M("quarts.ChefDeListe").objects.filter(user=u).count()+M("quarts.RedacteurFeuilleService").objects.filter(user=u).count()+M("training.ReferentFormation").objects.filter(user=u).count(),
}
tete=list(cols)
print("COV profil |"+" | ".join(tete))
for p in profils:
    u=User.objects.filter(username=p).first()
    if not u: print("COV",p,"absent"); continue
    print("COV",p,"|"," | ".join(str(essai(lambda:cols[c](u))) for c in tete))
# machines à états
machines=[("logistics.CorrectiveTicket","status"),("maintenance.MaintenanceOccurrence","status"),("taches.Tache","statut"),("quarts.EchangeService","statut"),("quarts.Quart","statut"),("quarts.ServiceGarde","statut"),("quarts.FeuilleService","statut"),("logistics.Anomalie","statut"),("logistics.Anomalie","status"),("demandes.Demande","etat"),("demandes.Demande","statut"),("documentation.VersionDocument","etat"),("retex.Retex","statut"),("retex.Retex","etat"),("training.CandidatureFormation","statut"),("training.TrainingSession","statut"),("org.ReleveEquipage","statut"),("annonces.Annonce","niveau"),("notifications.Notification","level"),("logistics.MouvementStock","type_mouvement"),("absences.Absence","type_absence")]
for label,nom in machines:
    try:
        mod=M(label); f=mod._meta.get_field(nom)
    except Exception: continue
    choix=[c[0] for c in (f.choices or [])]
    pres=collections.Counter(mod.objects.values_list(nom,flat=True))
    absents=[c for c in choix if pres.get(c,0)==0]
    print("MAC",label+"."+nom,"| présents",dict(pres),"| ABSENTS",absents)
from logistics.models import StockPiece
print("MAC stock sous le seuil d'alerte:",[ (p.reference,p.quantite) for p in StockPiece.objects.all() if getattr(p,"seuil_alerte",None) is not None and p.quantite<=p.seuil_alerte][:5],"| pièces",StockPiece.objects.count())
from training.models import TrainingRecord
import datetime
champs=[f.name for f in TrainingRecord._meta.fields]
print("MAC qualifications : champs",champs[:12])
