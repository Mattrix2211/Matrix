import collections
from django.contrib.auth.models import User
from accounts.models import UserProfile
from org.models import Ship, ReferenceBatiment
from quarts.models import EchangeService, FeuilleService
from absences.models import Absence
from taches.models import Tache
print("DEM échanges:",EchangeService.objects.count(),dict(collections.Counter(EchangeService.objects.values_list("statut",flat=True))),"| feuilles:",FeuilleService.objects.count(),"| absences:",Absence.objects.count(),"| tâches:",Tache.objects.count(),dict(collections.Counter(Tache.objects.values_list("statut",flat=True))))
print("DEM rôles des profils:",dict(collections.Counter(UserProfile.objects.values_list("role",flat=True))))
print("DEM navires de la démo:",list(Ship.objects.values_list("name","code","double_equipage")))
noms={r.nom.lower() for r in ReferenceBatiment.objects.all()} if ReferenceBatiment.objects.exists() else set()
print("DEM référentiel de bâtiments chargé:",ReferenceBatiment.objects.count())
from org.data import referentiel_batiments as d
reels={t[1].lower() for t in d.INVENTAIRE_2025}|{t[1].lower() for t in d.ESSAIS_2025}
print("DEM noms de navires de la démo présents dans l'inventaire réel 2025:",[n for n in Ship.objects.values_list("name",flat=True) if n.lower() in reels or n.lower().replace('é','e') in {x.replace('é','e') for x in reels}])
print("DEM comptes avec mot de passe 'pass':",sum(1 for u in User.objects.all() if u.check_password('pass')),"/",User.objects.count(),"| 'admin':",sum(1 for u in User.objects.all() if u.check_password('admin')))
print("DEM secteurs sans section:",sum(1 for s in __import__('org.models',fromlist=['Sector']).Sector.objects.all() if not s.sections.exists()))
