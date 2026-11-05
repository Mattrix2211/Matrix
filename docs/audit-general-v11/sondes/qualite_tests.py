import ast, glob, re, collections, os
fichiers=[f for f in glob.glob("**/test*.py",recursive=True)+glob.glob("**/tests/*.py",recursive=True) if "venv" not in f and "docs/" not in f]
fichiers=sorted(set(fichiers)); nt=0; sans=[]; dens=[]; ambig=0; mocks=0; tryexc=0; trivial=0; skips=0; par_app=collections.defaultdict(lambda:[0,0])
def a_assertion(n):
    for x in ast.walk(n):
        if isinstance(x,ast.Assert): return True
        if isinstance(x,ast.Call):
            f=x.func; nom=f.attr if isinstance(f,ast.Attribute) else (f.id if isinstance(f,ast.Name) else "")
            if nom.startswith("assert") or nom in ("fail",): return True
        if isinstance(x,(ast.With,)) :
            for it in x.items:
                c=it.context_expr
                if isinstance(c,ast.Call):
                    f=c.func; nom=f.attr if isinstance(f,ast.Attribute) else ""
                    if nom.startswith("assert"): return True
    return False
for f in fichiers:
    src=open(f,encoding="utf-8").read(); app=f.split("/")[0]
    mocks+=len(re.findall(r"mock\.patch|patch\(",src)); ambig+=len(re.findall(r"in \(403, ?404\)|in \(404, ?403\)|\[403, ?404\]",src)); skips+=len(re.findall(r"skip(If|Unless)?\(",src)); trivial+=len(re.findall(r"assertTrue\(True\)|assertFalse\(False\)",src))
    try: tree=ast.parse(src)
    except SyntaxError: continue
    for n in ast.walk(tree):
        if isinstance(n,ast.FunctionDef) and n.name.startswith("test"):
            nt+=1; par_app[app][0]+=1
            nb=sum(1 for x in ast.walk(n) if isinstance(x,ast.Assert) or (isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr.startswith("assert")))
            dens.append(nb)
            if not a_assertion(n): sans.append(f"{f}::{n.name}"); par_app[app][1]+=1
            if any(isinstance(x,ast.Try) for x in ast.walk(n)): tryexc+=1
print("QT fichiers",len(fichiers),"tests",nt,"| assertions par test: moyenne %.1f médiane %d"%(sum(dens)/len(dens),sorted(dens)[len(dens)//2]),"| tests avec 1 seule assertion:",sum(1 for d in dens if d==1),"| sans aucune assertion:",len(sans))
print("QT échantillon sans assertion:",sans[:12])
print("QT tolérances 403/404 interchangeables:",ambig,"| mock.patch:",mocks,"| tests avec try/except:",tryexc,"| assertTrue(True):",trivial,"| skip:",skips)
print("QT sans assertion par app:",{k:v[1] for k,v in par_app.items() if v[1]})
# couverture des clés du registre de seuils par les tests
import subprocess
cles=re.findall(r'ActionSeuil\(\s*"([a-z_]+)"',open("matrix/core/role_thresholds.py",encoding="utf-8").read())
tests_src="\n".join(open(f,encoding="utf-8").read() for f in fichiers)
cov={c:len(re.findall(c,tests_src)) for c in cles}
print("QT clés du registre jamais citées dans un test:",[c for c,n in cov.items() if n==0])
print("QT clés citées 1 à 2 fois:",[c for c,n in cov.items() if 0<n<=2])
print("QT clés les plus testées:",sorted(cov.items(),key=lambda x:-x[1])[:5])
