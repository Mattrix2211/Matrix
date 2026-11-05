import ast, subprocess, json, sys, os, time
WT=os.environ["WT"]  # copie jetable du dépôt (git worktree), jamais le dépôt de travail
PY=os.environ.get("PYTHON","python")
def early_return(fichier, fonction, expr):
    p=os.path.join(WT,fichier); src=open(p,encoding="utf-8").read(); tree=ast.parse(src); lines=src.split("\n")
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,)) and n.name==fonction:
            b=n.body; i=0
            if isinstance(b[0],ast.Expr) and isinstance(getattr(b[0],"value",None),ast.Constant) and isinstance(b[0].value.value,str): i=1
            indent=" "*b[0].col_offset
            ligne=(b[i].lineno-1) if i<len(b) else b[-1].end_lineno
            lines.insert(ligne,indent+expr); open(p,"w",encoding="utf-8").write("\n".join(lines)); return
    raise SystemExit("fonction introuvable "+fonction)
def replace(fichier, a, b):
    p=os.path.join(WT,fichier); s=open(p,encoding="utf-8").read(); assert a in s,(fichier,a); open(p,"w",encoding="utf-8").write(s.replace(a,b,1))
FE="quarts.tests.test_feuille_service quarts.tests.test_feuille_service_redaction quarts.tests.test_feuille_service_circuit_bsc quarts.tests.test_feuille_service_designation quarts.tests.test_visa_comaeq quarts.tests.test_feuille_service_equipage quarts.tests.test_feuille_service_a_terre quarts.tests.test_feuille_service_durcissement"
LI="quarts.tests.test_web_views quarts.tests.test_refus_serveur quarts.tests.test_services quarts.tests.test_double_equipage quarts.tests.test_chef_de_liste_par_type"
ET="matrix.tests.test_etancheite_equipage matrix.tests.test_etancheite_equipage_vues matrix.tests.test_fuites_sans_rattachement matrix.tests.test_core_scopes matrix.tests.test_securite_ecritures org.tests.test_scope_navire"
M=[
("M01 rédaction de la feuille ouverte à tous","fn",("quarts/models.py","peut_rediger_feuille_service","return True"),FE),
("M02 visa COMAEQ ouvert à tous","fn",("quarts/models.py","peut_viser_comaeq","return True"),FE),
("M03 visa chef de secteur ouvert à tous","fn",("quarts/models.py","peut_viser_secteur","return True"),FE),
("M04 visa chef de service ouvert à tous","fn",("quarts/models.py","peut_viser_service","return True"),FE),
("M05 désignation des rédacteurs ouverte à tous","fn",("quarts/models.py","peut_designer_redacteurs","return True"),FE),
("M06 publication d'une liste ouverte à tous","fn",("quarts/models.py","peut_publier_liste","return True"),LI),
("M07 gestion d'une liste ouverte à tous","fn",("quarts/models.py","peut_gerer_liste","return True"),LI),
("M08 validation d'une qualification ouverte à tous","fn",("training/models.py","peut_valider_formation","return True"),"training.tests"),
("M09 périmètre supprimé (build_scope_q → tout)","fn",("matrix/core/mixins.py","build_scope_q","from django.db.models import Q as _Q\n    return _Q()"),ET),
("M10 périmètre des tickets sans étanchéité","fn",("logistics/perimetre.py","perimetre_tickets_q","from django.db.models import Q as _Q\n    return _Q()"),"logistics.tests.test_scope_leak logistics.tests.test_web_scope_leak logistics.tests.test_rbac_transitions "+ET),
("M11 seuils de rôle désactivés (tout le monde EQUIPIER)","fn",("matrix/core/role_thresholds.py","niveau_requis_pour","from matrix.core.roles import RoleLevel as _R\n    return _R.EQUIPIER"),"matrix.tests.test_core_permissions matrix.tests.test_securite_ecritures logistics.tests.test_rbac_transitions quarts.tests.test_web_views"),
("M12 stock négatif accepté","rep",("logistics/stock.py","raise StockInsuffisant(verrouillee.reference, verrouillee.quantite)","pass"),"logistics.tests.test_mouvements_stock logistics.tests.test_stock_piece"),
]

import re
CAS=[
("M11c seuils désactivés — suite COMPLÈTE sans failfast","fn",("matrix/core/role_thresholds.py","niveau_requis_pour","from matrix.core.roles import RoleLevel as _R\n    return _R.EQUIPIER"),"",False),
]
res=[]
for nom,typ,arg,labels,ff in CAS:
    subprocess.run(["git","checkout","--","."],cwd=WT,capture_output=True)
    (early_return if typ=="fn" else replace)(*arg)
    t0=time.time(); cmd=[PY,"manage.py","test",*labels.split(),"--parallel","4","--noinput"]+(["--failfast"] if ff else [])
    r=subprocess.run(cmd,cwd=WT,capture_output=True,text=True,timeout=3000,env={**os.environ,"DJANGO_DEBUG":"1","DJANGO_SECRET_KEY":"x"})
    out=r.stdout+r.stderr; ran=re.search(r"Ran (\d+) tests?",out); fa=re.search(r"FAILED \((.*?)\)",out); premier=re.search(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)",out,re.M)
    ligne={"mutation":nom,"tests_lances":ran.group(1) if ran else "?","resultat":"TUÉE" if r.returncode!=0 else "SURVIVANTE","echecs":fa.group(1) if fa else None,"premier":(premier.group(3) if premier else None),"duree_s":round(time.time()-t0)}
    res.append(ligne); print(json.dumps(ligne,ensure_ascii=False),flush=True)
    open(os.path.dirname(WT)+"/mutations3.json","w").write(json.dumps(res,ensure_ascii=False,indent=1))
subprocess.run(["git","checkout","--","."],cwd=WT); print("FINI")
