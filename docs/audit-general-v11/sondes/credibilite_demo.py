"""Crédibilité, diversité et cas limites des données de démonstration (lecture seule)."""
import collections, datetime
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import UserProfile
from quarts.models import RemplacementChefDeListe, ChefDeListe, Quart, ServiceGarde, CreneauQuart, CreneauServiceGarde
from postes.models import Poste, AffectationPoste
g=collections.defaultdict(collections.Counter)
for p in UserProfile.objects.select_related("user"):
    g[p.role][p.grade or "—"]+=1
for r,c in g.items(): print("CRD grades par rôle",r,dict(c))
n=User.objects.count(); print("CRD comptes",n,"| inactifs",User.objects.filter(is_active=False).count(),"| prénoms distincts",len(set(User.objects.values_list("first_name",flat=True))),"| noms distincts",len(set(User.objects.values_list("last_name",flat=True))))
techniques=[u.username for u in User.objects.all() if any(x in (u.last_name+u.first_name).lower() for x in ("equipier","cdt","comaeq","comanav","comops","chef","second","admin","terre"))]
print("CRD comptes à identité « étiquette technique » (nom ou prénom du type Equipier A, Cdt A…):",len(techniques),"sur",n)
print("CRD spécialités distinctes:",len(set(UserProfile.objects.values_list("specialite",flat=True))-{""}),"| grades distincts:",len(set(UserProfile.objects.values_list("grade",flat=True))-{""}),"| fonctions de service:",len(set(UserProfile.objects.values_list("fonction_service",flat=True))-{""}))
print("CRD postes:",Poste.objects.count(),"| affectations:",AffectationPoste.objects.count())
now=timezone.now()
print("CRD remplacements de chef de liste: actifs",RemplacementChefDeListe.objects.filter(revoque_le__isnull=True,debut__lte=now,fin__gt=now).count(),"| à venir",RemplacementChefDeListe.objects.filter(revoque_le__isnull=True,debut__gt=now).count(),"| expirés",RemplacementChefDeListe.objects.filter(revoque_le__isnull=True,fin__lte=now).count(),"| révoqués",RemplacementChefDeListe.objects.filter(revoque_le__isnull=False).count())
from quarts.models import CreneauQuart as CQ
dates=list(CQ.objects.values_list("debut",flat=True)); print("CRD créneaux de quart : de",min(dates).date(),"à",max(dates).date(),"(aujourd'hui",now.date(),")")
print("CRD marins sans équipage sur bâtiment à double équipage:",UserProfile.objects.filter(ship__double_equipage=True,equipage="").exclude(role__in=("MASTER_ADMIN",)).count(),"| marins sans service ni secteur ni section (hors commandement):",UserProfile.objects.filter(service__isnull=True,sector__isnull=True,section__isnull=True,ship__isnull=False).exclude(role__in=("COMMANDANT","COMMANDANT_EN_SECOND","ETAT_MAJOR","ADMIN_NAVIRE")).count())
from taches.models import Tache
print("CRD tâches en retard:",Tache.objects.exclude(statut="TERMINEE").filter(echeance__lt=now.date()).count(),"| sans échéance:",Tache.objects.filter(echeance__isnull=True).count())
from org.models import Sector
print("CRD secteurs sans section:",sum(1 for s in Sector.objects.all() if not s.sections.exists()),"| services sans commandant adjoint:",__import__('org.models',fromlist=['Service']).Service.objects.filter(commandant_adjoint="").count())
from logistics.models import StockPiece
print("CRD pièces de stock:",StockPiece.objects.count(),"| quantité nulle:",StockPiece.objects.filter(quantite=0).count())
