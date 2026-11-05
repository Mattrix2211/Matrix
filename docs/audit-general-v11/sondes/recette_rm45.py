# Recette RM-45 : vocabulaire du quart (musique, homme mort, bordée, tiers, au quart) dans l'interface et capacité à modéliser ces régimes. Lecture seule.
import re,html
from django.test import Client
from django.contrib.auth.models import User
from quarts.models import Quart, ServiceGarde, CreneauQuart
def cl(u): c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u)); return c
def texte(r): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<(script|style)[^>]*>.*?</\1>","",r.content.decode(errors="ignore"),flags=re.S|re.I))) if False else re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",re.sub(r"<(script|style)[^>]*>.*?</\1>","",r.content.decode(errors="ignore"),flags=re.S|re.I))))
MOTS=("musique","homme mort","bordée","bordées","tiers","au quart","quart de nuit","pas de quart","dispens","rattrapage","régime")
pages={"assistant de création (étape 1)":"/quarts/creer/","assistant quart":"/quarts/creer/?type=quart","assistant garde":"/quarts/creer/?type=garde","liste des quarts":"/quarts/","feuille de service":"/quarts/feuille-service/","réglages des chefs de liste":"/quarts/reglages/","réglages de la feuille de service":"/quarts/feuille-service/reglages/"}
q=Quart.objects.exclude(statut="BROUILLON").first(); sg=ServiceGarde.objects.first()
if q: pages["détail d'un quart"]=f"/quarts/quart/{q.pk}/"
if sg: pages["détail d'un service de garde"]=f"/quarts/garde/{sg.pk}/"
for nom,url in pages.items():
    r=cl("chef_secteur_a").get(url,HTTP_HOST="localhost"); t=texte(r).lower()
    print(f"RM45 page « {nom} » HTTP {r.status_code} : mots du vocabulaire présents → {[m for m in MOTS if m in t] or 'aucun'}")
print("RM45 données de démonstration : noms de listes contenant le vocabulaire :",[(x.nom) for x in Quart.objects.all() if re.search("musique|homme mort|bordée|tiers",x.nom,re.I)])
print("RM45 champs d'un quart :",[f.name for f in Quart._meta.fields if f.name not in ("created_at","updated_at","created_by","updated_by")])
print("RM45 champs d'un créneau de quart :",[f.name for f in CreneauQuart._meta.fields if f.name not in ("created_at","updated_at","created_by","updated_by")])
# caractère modélisable : un quart « de musique » est-il identifiable et exploitable (statistiques, alertes) ?
from quarts.models import CreneauQuart as C
print("RM45 postes distincts utilisés dans les créneaux de démonstration :",sorted(set(C.objects.values_list("poste",flat=True)))[:12])
