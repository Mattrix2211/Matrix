from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from logistics.models import StockPiece, MouvementStock
from logistics.stock import enregistrer_mouvement, StockInsuffisant
ecarts=[(p.pk,p.quantite,p.quantite_calculee()) for p in StockPiece.objects.all() if p.quantite!=p.quantite_calculee()]
print("STK pièces:",StockPiece.objects.count(),"mouvements:",MouvementStock.objects.count(),"| pièces dont la quantité ≠ somme des mouvements:",ecarts)
p=StockPiece.objects.filter(quantite__gt=0).first(); u=User.objects.get(username="chef_section_a")
import inspect; print("STK signature:",inspect.signature(enregistrer_mouvement))
T=MouvementStock
print("STK types:",[a for a in dir(T) if a.isupper()][:10])
with transaction.atomic():
    q0=p.quantite
    try: enregistrer_mouvement(u,p,"SORTIE",q0+1,"audit"); print("STK sortie supérieure au stock : ACCEPTÉE (anormal)")
    except StockInsuffisant as e: print("STK sortie supérieure au stock : refusée (StockInsuffisant)")
    except Exception as e: print("STK sortie : exception",type(e).__name__,str(e)[:80])
    m=enregistrer_mouvement(u,p,"SORTIE",1,"audit"); p.refresh_from_db(); print("STK sortie 1 :",q0,"→",p.quantite,"| somme mouvements =",p.quantite_calculee())
    try: enregistrer_mouvement(u,p,"INVENTAIRE",0,""); print("STK inventaire sans motif : ACCEPTÉ")
    except Exception as e: print("STK inventaire sans motif : refusé",type(e).__name__)
    try: m.delete(); print("STK suppression d'un mouvement : POSSIBLE par le modèle")
    except Exception as e: print("STK suppression d'un mouvement : refusée",type(e).__name__)
    transaction.set_rollback(True)
for nom in ("equipier_a","chef_section_a","chef_secteur_a","terre_classe"):
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=nom))
    with transaction.atomic():
        r=c.post(f"/logistics/stock/{p.pk}/mouvements/",{"type":"SORTIE","quantite":1,"motif":"audit"},HTTP_HOST="localhost"); p.refresh_from_db()
        print("STK POST mouvement par",nom,r.status_code,"quantité",p.quantite); transaction.set_rollback(True)
