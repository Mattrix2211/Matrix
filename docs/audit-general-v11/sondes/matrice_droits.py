import json
from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
USERS=["equipier_a","equipier_a2","marin_b","chef_section_a","chef_secteur_a","chef_secteur_b","chef_service_a","coma_comaeq","coma_comanav","coma_comops","second_a","cdt_a","cdt_b","admin_navire","terre_classe","admin","cdt_abe","comaeq_abe","chef_liste_abe","marin_abe_1","historique_abe","chef_liste_jch","m_dupont" ]
USERS=[u for u in USERS if User.objects.filter(username=u).exists()]
cibles=[]
for q in (1,2): cibles.append((f"quart {q}", f"/quarts/quart/{q}/", ["ajouter_creneau","supprimer_creneau","publier","proposer","terminer_creneau"]))
for g in (2,5): cibles.append((f"garde {g}", f"/quarts/garde/{g}/", ["ajouter_creneau","supprimer_creneau","publier","proposer","activer","reporter","regler_echanges","retirer_previsionnelle"]))
cibles.append(("feuille 1 (nav.2, A)", "/quarts/feuille-service/2/2026-11-05/", ["enregistrer_entete","resynchroniser","ouvrir_rectificatif","proposer","viser_secteur","viser_service","viser_comaeq","modifier_comaeq","renvoyer","rattacher_feuille"]))
cibles.append(("feuille creer (nav.2, futur)", "/quarts/feuille-service/2/2027-04-01/", ["creer"]))
cibles.append(("feuille creer (nav.5, futur)", "/quarts/feuille-service/5/2027-04-01/", ["creer"]))
cibles.append(("reglages chefs de liste", "/quarts/reglages/", ["designer","remplacer","revoquer_remplacement","preciser","retirer"]))
cibles.append(("redacteurs feuille", "/quarts/feuille-service/redacteurs/", ["designer","retirer"]))
cibles.append(("reglages feuille", "/quarts/feuille-service/reglages/", ["enregistrer_rubriques","enregistrer_fonctions","supprimer_rubrique","supprimer_fonction"]))
cibles.append(("delais activation", "/quarts/reglages/delais-activation/", [""]))
cibles.append(("mouvements batiment", "/quarts/mouvements/", ["declarer","initialiser","annuler"]))
cibles.append(("creer liste", "/quarts/creer/", [""]))
out={}
for u in USERS:
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u))
    for nom,url,actions in cibles:
        g=c.get(url+("?ship=2" if "reglages" in url or "redacteurs" in url or "mouvements" in url else ""), HTTP_HOST="localhost")
        out[(u,nom,"GET")]=g.status_code
        for a in actions:
            if not a: 
                with transaction.atomic():
                    r=c.post(url,{}, HTTP_HOST="localhost"); transaction.set_rollback(True)
                out[(u,nom,"POST")]=r.status_code; continue
            with transaction.atomic():
                r=c.post(url+("?ship=2" if "reglages" in url or "redacteurs" in url or "mouvements" in url else ""),{"action":a,"ship":2}, HTTP_HOST="localhost"); transaction.set_rollback(True)
            out[(u,nom,a)]=r.status_code
json.dump({"|".join(k):v for k,v in out.items()}, open("matrice.json","w"))
print("OK", len(out), USERS)
