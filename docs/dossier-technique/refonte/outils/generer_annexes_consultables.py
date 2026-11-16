"""Phase 8 : annexes consultables hors PDF (D4) — un fichier HTML autonome et des CSV (UTF-8, séparateur « ; »).

Sources de vérité : inventaire du code de l'état B (couverture/etat_B/inventaire.json), annexes générées de l'édition initiale
(tableaux relus tels quels), sources Markdown des trois documents (registre des éléments non vérifiés), registre central, faits.yaml.
Usage : python generer_annexes_consultables.py
"""
import csv
import html
import io
import json
import re
from pathlib import Path

import yaml

R = Path(__file__).resolve().parent.parent
DT = R.parent
OUT = R / "4_annexes_consultables"
ident = yaml.safe_load((R / "config/identite.yaml").read_text(encoding="utf-8"))
faits = yaml.safe_load((R / "faits.yaml").read_text(encoding="utf-8"))
docs = yaml.safe_load((R / "config/documents.yaml").read_text(encoding="utf-8"))
INV = json.loads((DT / "couverture/etat_B/inventaire.json").read_text(encoding="utf-8"))
MENTION = f"{ident['mention']}. {ident['precaution']}"
ROLES = [("MASTER_ADMIN", 9, "Admin. général"), ("ADMIN_NAVIRE", 8, "Admin. unité"), ("COMMANDANT", 7, "Commandant"),
         ("COMMANDANT_EN_SECOND", 6, "Second"), ("ETAT_MAJOR", 5, "État-major"), ("CHEF_SERVICE", 4, "Chef service"),
         ("CHEF_SECTEUR", 3, "Chef secteur"), ("CHEF_SECTION", 2, "Chef section"), ("EQUIPIER", 1, "Équipier")]
NIV = {n: v for n, v, _ in ROLES}
TABLES = []          # (id, titre, source, colonnes, lignes, note)


def propre(t):
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("\\|", "|")
    t = re.sub(r"[`*]|\[\[|\]\]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def ajouter(tid, titre, source, cols, lignes, note=""):
    TABLES.append({"id": tid, "titre": titre, "source": source, "colonnes": cols, "lignes": [[str(c) for c in l] for l in lignes], "note": note})


def tables_md(chemin):
    """Renvoie [(titre de section, colonnes, lignes)] pour chaque tableau Markdown du fichier."""
    titre, sortie, cur = "", [], None
    for l in chemin.read_text(encoding="utf-8").split("\n"):
        if l.startswith("#"):
            titre = propre(l.lstrip("# "))
        if l.startswith("|"):
            cells = [propre(c) for c in re.split(r"(?<!\\)\|", l.strip().strip("|"))]
            if cur is None:
                cur = [titre, cells, []]
            elif all(re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells):
                continue
            else:
                cur[2].append(cells)
        elif cur is not None:
            sortie.append(tuple(cur)); cur = None
    if cur:
        sortie.append(tuple(cur))
    return sortie


# ---------- B : matrice rôle × action ----------
actions = INV["actions_seuils"]
lignes = []
for a in actions:
    niv = NIV[a["defaut"]]
    marques = []
    for nom, v, _ in ROLES:
        if v < niv:
            marques.append("—")
        elif nom == "ETAT_MAJOR":
            marques.append("✔†")
        elif nom == "COMMANDANT_EN_SECOND":
            marques.append("✔" if a["ouverte_au_second"] else "✱")
        else:
            marques.append("✔")
    lignes.append([a["cle"], a["categorie"], a["libelle"], a["defaut"], a["portee"]] + marques)
ajouter("B1", "Matrice rôle × action : actions à seuil de rôle (valeurs par défaut)", "inventaire du code de l'état B (REGISTRE_ACTIONS)",
        ["Clé", "Catégorie", "Action", "Seuil par défaut", "Portée"] + [n for _, _, n in ROLES], lignes,
        "✔ : le rôle atteint le seuil par défaut ; ✔† : idem mais un état-major n'écrit que dans les services rattachés à sa fonction ; ✱ : commandant en second, vision globale, écriture attribuée par des responsabilités explicites. Le niveau n'est qu'une condition : le périmètre s'y ajoute.")
for titre, cols, rows in tables_md(DT / "restreint/annexes/B_matrice_role_action.md"):
    if "attribuer" in titre:
        ajouter("B2", "Qui peut attribuer ou gérer quel rôle (comptes)", "annexe B de l'édition initiale, relue", cols, rows)

# ---------- C : routes ----------
def groupe(r):
    return "API" if r["route"].startswith("api/") else ("Administration" if r["route"].startswith("admin/") else "Pages")
for tid, nom, titre in (("C1", "Pages", "Routes : pages web, fichiers et recherche"), ("C2", "API", "Routes : interface de programmation (API REST)"), ("C3", "Administration", "Routes : administration Django")):
    ajouter(tid, titre, "inventaire du code de l'état B (URLconf résolue)", ["Chemin", "Nom", "Vue"],
            [[r["route"], r["nom"] or "—", r["vue"]] for r in INV["routes"] if groupe(r) == nom])

# ---------- D : modèles ----------
ajouter("D1", "Index des modèles de données", "inventaire du code de l'état B", ["Application", "Modèle", "Champs", "Relations", "Identifiant UUID"],
        [[m["app"], m["modele"], len(m["champs"]), len(m["relations"]), "oui" if m["uuid"] else "non"] for m in INV["modeles"]])

# ---------- E : tâches, commandes, variables ----------
ajouter("E1", "Tâches planifiées (Celery beat)", "inventaire du code de l'état B", ["Nom", "Tâche", "Planification (secondes)"],
        [[b["nom"], b["tache"], b["planification"]] for b in INV["beat"]])
ajouter("E2", "Commandes de gestion", "inventaire du code de l'état B", ["Fichier"], [[c] for c in INV["commandes"]])
for titre, cols, rows in tables_md(DT / "restreint/annexes/E_taches_commandes_variables.md"):
    if "Variable" in cols[0]:
        ajouter("E3", "Variables d'environnement lues par le fichier de réglages", "annexe E de l'édition initiale, relue", cols, rows)

# ---------- F : sources, branches ----------
noms = {"F.1": ("F1", "Sources lues"), "F.2": ("F2", "Sources non lues ou lues seulement par résultat de recherche"), "F.3": ("F3", "Décisions du PO citées"), "F.4": ("F4", "Branches distantes de l'inventaire")}
for titre, cols, rows in tables_md(DT / "restreint/annexes/F_sources_branches_non_verifies.md"):
    for k, (tid, t) in noms.items():
        if titre.startswith(k) and not any(x["id"] == tid for x in TABLES):
            ajouter(tid, t, "annexe F de l'édition initiale, relue", cols, rows)

# F.5 refaite : un passage ⚪ par ligne, phrase entière, document et section d'origine
f5 = []
for code, dossier in (("GU", "1_guide_utilisateur"), ("RF", "2_referentiel_fonctionnel"), ("DT", "3_dossier_technique")):
    for f in sorted((R / dossier).glob("[0-9][0-9]_*.md")):
        section, h1 = "", ""
        for l in f.read_text(encoding="utf-8").split("\n"):
            if l.startswith("<!--"):
                continue
            m = re.match(r"^(#{1,3}) (.+)", l)
            if m:
                if len(m.group(1)) == 1:
                    h1 = propre(m.group(2))
                section = propre(m.group(2))
                continue
            if "⚪" not in l or l.startswith("@capture"):
                continue
            brut = l.strip()
            if brut.startswith("|"):
                cells = [propre(c) for c in re.split(r"(?<!\\)\|", brut.strip("|"))]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    continue
                passages = [" — ".join(c for c in cells if c)]
            else:
                brut = re.sub(r"^[-*>\d.]+\s+", "", brut)
                passages = [propre(p) for p in re.split(r"(?<=[.!?])\s+(?=[A-ZÀÉÈ🟢🔵🟣⚪])", brut) if "⚪" in p] or [propre(brut)]
            for p in passages:
                autres = "".join(e for e in "🟢🔵🟣" if e in p)
                f5.append([code, f.name, h1 if h1 == section else f"{h1} › {section}", p, "⚪" + (" (avec " + autres + ")" if autres else "")])
ajouter("F5", "Registre des éléments non vérifiés (⚪)", "sources Markdown des trois documents (généré à chaque construction)", ["Document", "Fichier", "Section", "Point", "Étiquettes"], f5,
        "Chaque ligne reprend un passage marqué ⚪, en entier et sans mise en forme Markdown. Aucune ligne n'est ajoutée ni retirée à la main.")

# ---------- G : matrice de couverture ----------
for titre, cols, rows in tables_md(DT / "restreint/annexes/G_matrice_couverture.md"):
    m = re.match(r"G\.(\d)", titre)
    if m:
        n = len([x for x in TABLES if x["id"].startswith("G")]) + 1
        ajouter(f"G{m.group(1)}" + ("" if not any(x["id"] == f"G{m.group(1)}" for x in TABLES) else chr(96 + n)), titre.replace("G." + m.group(1), "").strip(), "annexe G de l'édition initiale, relue (numéros de chapitre de l'édition initiale : voir MAPPING_ANCIEN_NOUVEAU.csv)", cols, rows)

# ---------- H : index des schémas ----------
SCH = []
for f in sorted((R / "schemas/src").glob("S*.mmd")):
    m = re.match(r"(S\d+[a-z]?)_(.+)\.mmd", f.name)
    en = next(((R / "schemas/tableaux").glob(f"{m.group(1)}_*.md")), None)
    ent = f.read_text(encoding="utf-8")[:300]
    titre = re.search(r"%%\s*(.+)", ent)
    SCH.append([m.group(1), m.group(2).replace("_", " "), f"schemas/src/{f.name}", f"schemas/svg/{m.group(1)}_{m.group(2)}.svg", "remplacé par un tableau dans le référentiel" if en else "figure"])
ajouter("H1", "Index des schémas", "dossier refonte/schemas", ["N°", "Sujet", "Source Mermaid", "Export SVG", "Présentation"], SCH)


# F.2 : puces de l'annexe F de l'édition initiale -> une ligne par source non lue
txt = (DT / "restreint/annexes/F_sources_branches_non_verifies.md").read_text(encoding="utf-8")
bloc = txt[txt.index("## F.2"):txt.index("## F.3")]
ajouter("F2", "Sources non lues ou lues seulement par résultat de recherche", "annexe F de l'édition initiale, relue", ["Source non lue ou partiellement lue"],
        [[propre(l[2:])] for l in bloc.split("\n") if l.startswith("- ")])
# F.3 refaite : décisions du PO citées dans les trois documents, avec leur état dans le registre
reg = json.loads((R / "5_registre/registre.json").read_text(encoding="utf-8"))
etat = {d["id"]: d for d in reg["decisions"]}
cit = {}
for code, dossier in (("GU", "1_guide_utilisateur"), ("RF", "2_referentiel_fonctionnel"), ("DT", "3_dossier_technique")):
    for f in sorted((R / dossier).glob("[0-9][0-9]_*.md")):
        t = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
        for i in set(re.findall(r"\bDEC-[A-Z]{2,4}-\d{2}\b", t)) | set(re.findall(r"^@decisions (.+)$", t, flags=re.M) and [x for l in re.findall(r"^@decisions (.+)$", t, flags=re.M) for x in l.split()]):
            cit.setdefault(i, set()).add(code)
ajouter("F3", "Décisions du PO citées dans les documents", "sources Markdown et registre central", ["Décision", "État dans l'état B", "Règle", "Citée dans"],
        [[i, etat[i]["etat_dans_etat_b"], etat[i]["regle"], ", ".join(sorted(c))] for i, c in sorted(cit.items()) if i in etat],
        "Les {} décisions du registre sont toutes portées par le registre des écarts et décisions ; ce tableau liste celles qui sont citées dans le guide, le référentiel ou le dossier technique.".format(len(etat)))
# G.5 / G.7
ajouter("G5", "Actions à seuil de rôle", "inventaire du code de l'état B", ["Clé", "Catégorie", "Seuil par défaut"], [[a["cle"], a["categorie"], a["defaut"]] for a in actions])
ajouter("G7", "Dépendances entre paquets", "inventaire du code de l'état B", ["Paquet", "Dépend de", "Nombre de liaisons"],
        [[p, ", ".join(f"{q} ({n})" for q, n in sorted(d.items())) or "—", sum(d.values())] for p, d in sorted(INV["dependances"].items())])
TABLES.sort(key=lambda t: (t["id"][0], int(re.sub(r"\D", "", t["id"]) or 0), t["id"]))

# ---------- totaux contrôlés ----------
TOTAUX = [("Modèles", len(INV["modeles"]), faits["n_modeles"]["valeur"]), ("Routes", len(INV["routes"]), faits["n_routes"]["valeur"]),
          ("Tâches planifiées", len(INV["beat"]), faits["n_taches_planifiees"]["valeur"]), ("Commandes de gestion", len(INV["commandes"]), faits["n_commandes"]["valeur"]),
          ("Actions à seuil", len(actions), faits["n_actions_seuil"]["valeur"]), ("Variables d'environnement", len(next(t for t in TABLES if t["id"] == "E3")["lignes"]), faits["n_variables_environnement"]["valeur"])]
for nom, a, b in TOTAUX:
    assert a == b, f"total incohérent : {nom} = {a} ≠ {b}"

OUT.mkdir(exist_ok=True)
for f in OUT.glob("*.csv"):
    f.unlink()
for t in TABLES:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow([f"# {MENTION}"])
    w.writerow([f"# {t['id']} — {t['titre']} ({t['source']})"])
    w.writerow(t["colonnes"])
    w.writerows(t["lignes"])
    nom = re.sub(r"[^a-z0-9]+", "_", t["titre"].lower().replace("é", "e").replace("è", "e").replace("à", "a").replace("ô", "o").replace("û", "u").replace("ç", "c"))[:48].strip("_")
    t["csv"] = f"{t['id']}_{nom}.csv"
    (OUT / t["csv"]).write_text(buf.getvalue(), encoding="utf-8-sig")

donnees = {"mention": MENTION, "reference": ident["reference_documentaire"], "edition": ident["date_edition"], "tables": TABLES,
           "totaux": [{"nom": n, "calcule": a, "attendu": b} for n, a, b in TOTAUX]}
page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Annexes consultables — {html.escape(ident['reference_documentaire'])}</title>
<style>
:root{{--fond:#f3f5f8;--carte:#fff;--texte:#16202c;--att:#5a6778;--ligne:#d6dce5;--acc:#0b6b8a;--bandeau:#7a1d1d}}
@media(prefers-color-scheme:dark){{:root{{--fond:#10161d;--carte:#18212b;--texte:#e6ebf1;--att:#9aa7b6;--ligne:#2b3846;--acc:#4cb4d6;--bandeau:#a63a3a}}}}
*{{box-sizing:border-box}}body{{margin:0;font:14px/1.45 system-ui,"Segoe UI",sans-serif;background:var(--fond);color:var(--texte)}}
.bandeau{{background:var(--bandeau);color:#fff;padding:8px 16px;font-weight:600;font-size:13px}}
header{{padding:12px 16px 0}}h1{{margin:0 0 4px;font-size:20px}}.sous{{color:var(--att);margin:0 0 8px}}
.layout{{display:flex;gap:12px;padding:8px 16px 24px;align-items:flex-start}}
nav{{flex:0 0 250px;max-height:calc(100vh - 150px);overflow:auto;background:var(--carte);border:1px solid var(--ligne);border-radius:6px}}
nav button{{display:block;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--ligne);padding:7px 10px;color:var(--texte);cursor:pointer;font:inherit}}
nav button[aria-current=true]{{background:var(--acc);color:#fff}}nav small{{color:inherit;opacity:.75}}
main{{flex:1;min-width:0;background:var(--carte);border:1px solid var(--ligne);border-radius:6px;padding:12px}}
.outils{{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}}input[type=search]{{flex:1;min-width:200px;padding:7px;border:1px solid var(--ligne);border-radius:4px;background:var(--fond);color:var(--texte)}}
a.btn,button.btn{{padding:7px 10px;border:1px solid var(--acc);border-radius:4px;color:var(--acc);text-decoration:none;background:none;cursor:pointer;font:inherit}}
.cadre{{overflow:auto;max-height:calc(100vh - 290px);border:1px solid var(--ligne)}}table{{border-collapse:collapse;width:100%}}
th,td{{padding:5px 8px;border-bottom:1px solid var(--ligne);text-align:left;vertical-align:top;overflow-wrap:anywhere}}
th{{position:sticky;top:0;background:var(--carte);cursor:pointer;white-space:nowrap}}th[aria-sort=ascending]::after{{content:" ▲"}}th[aria-sort=descending]::after{{content:" ▼"}}
.note{{color:var(--att);font-size:13px}}.ok{{color:#1a7f37}}.ko{{color:#b42318;font-weight:700}}
@media(max-width:1100px){{.layout{{flex-direction:column}}nav{{flex:none;width:100%;max-height:150px}}.cadre{{max-height:none}}}}
</style></head><body>
<div class="bandeau">{html.escape(MENTION)}</div>
<header><h1>Annexes consultables — Matrix, état B du 11/11/2026</h1>
<p class="sous">Accès restreint · fichier autonome (aucune connexion, aucune police distante) · {len(TABLES)} tables · un CSV par table est fourni à côté de ce fichier.</p></header>
<div class="layout"><nav id="nav" aria-label="Tables"></nav><main id="main"></main></div>
<script id="donnees" type="application/json">{json.dumps(donnees, ensure_ascii=False).replace("</", "<\\/")}</script>
<script>
(function(){{
var D=JSON.parse(document.getElementById('donnees').textContent), nav=document.getElementById('nav'), main=document.getElementById('main');
function el(t,a,c){{var e=document.createElement(t);for(var k in (a||{{}}))e.setAttribute(k,a[k]);if(c!=null)e.textContent=c;return e;}}
function ouvrir(i){{
  var T=D.tables[i], tri={{col:-1,sens:1}}, lignes=T.lignes.slice();
  [].forEach.call(nav.children,function(b,j){{b.setAttribute('aria-current',j===i?'true':'false');}});
  main.textContent='';location.hash=T.id;
  main.appendChild(el('h2',{{style:'margin:0 0 4px;font-size:17px'}},T.id+' — '+T.titre));
  main.appendChild(el('p',{{class:'note'}},'Source : '+T.source+(T.note?' — '+T.note:'')));
  var outils=el('div',{{class:'outils'}}), q=el('input',{{type:'search',placeholder:'Filtrer ('+T.lignes.length+' lignes)',id:'filtre','aria-label':'Filtrer le tableau'}}), cnt=el('span',{{class:'note',id:'compte',style:'align-self:center'}});
  var dl=el('a',{{class:'btn',href:T.csv,download:T.csv}},'Télécharger le CSV');
  outils.appendChild(q);outils.appendChild(cnt);outils.appendChild(dl);main.appendChild(outils);
  var cadre=el('div',{{class:'cadre'}}), tab=el('table'), th=el('thead'), tr=el('tr'), tb=el('tbody');
  T.colonnes.forEach(function(c,j){{var h=el('th',{{tabindex:'0',role:'columnheader'}},c);function t(){{tri.sens=tri.col===j?-tri.sens:1;tri.col=j;[].forEach.call(tr.children,function(x){{x.removeAttribute('aria-sort');}});h.setAttribute('aria-sort',tri.sens>0?'ascending':'descending');rendre();}}h.onclick=t;h.onkeydown=function(e){{if(e.key==='Enter')t();}};tr.appendChild(h);}});
  th.appendChild(tr);tab.appendChild(th);tab.appendChild(tb);cadre.appendChild(tab);main.appendChild(cadre);
  function rendre(){{
    var f=q.value.toLowerCase(), r=lignes.filter(function(l){{return !f||l.join(' ').toLowerCase().indexOf(f)>=0;}});
    if(tri.col>=0)r.sort(function(a,b){{var x=a[tri.col],y=b[tri.col],nx=parseFloat(x),ny=parseFloat(y);return (isNaN(nx)||isNaN(ny)?x.localeCompare(y,'fr'):nx-ny)*tri.sens;}});
    tb.textContent='';r.slice(0,2000).forEach(function(l){{var row=el('tr');l.forEach(function(c){{row.appendChild(el('td',null,c));}});tb.appendChild(row);}});
    cnt.textContent=r.length+' ligne(s) affichée(s) sur '+lignes.length;
  }}
  q.oninput=rendre;rendre();
}}
D.tables.forEach(function(t,i){{var b=el('button',{{type:'button'}},'');b.appendChild(document.createTextNode(t.id+' — '+t.titre+' '));b.appendChild(el('small',null,'('+t.lignes.length+')'));b.onclick=function(){{ouvrir(i);}};nav.appendChild(b);}});
var tot=el('button',{{type:'button'}},'Totaux contrôlés');tot.onclick=function(){{
  [].forEach.call(nav.children,function(b){{b.setAttribute('aria-current',b===tot?'true':'false');}});main.textContent='';location.hash='totaux';
  main.appendChild(el('h2',{{style:'margin:0 0 8px;font-size:17px'}},'Totaux contrôlés'));
  main.appendChild(el('p',{{class:'note'}},'Le total de chaque table est comparé au registre des faits de la refonte (généré depuis l\\'inventaire du code).'));
  var t=el('table'),h=el('tr');['Élément','Calculé ici','Registre des faits','Résultat'].forEach(function(c){{h.appendChild(el('th',null,c));}});t.appendChild(h);
  D.totaux.forEach(function(x){{var r=el('tr');r.appendChild(el('td',null,x.nom));r.appendChild(el('td',null,x.calcule));r.appendChild(el('td',null,x.attendu));r.appendChild(el('td',{{class:x.calcule===x.attendu?'ok':'ko'}},x.calcule===x.attendu?'identique':'ÉCART'));t.appendChild(r);}});
  main.appendChild(t);}};
nav.appendChild(tot);
var h=location.hash.replace('#',''), i=D.tables.findIndex(function(t){{return t.id===h;}});
if(h==='totaux')tot.onclick();else ouvrir(i>=0?i:0);
}})();
</script></body></html>"""
(OUT / "index.html").write_text(page, encoding="utf-8")
(OUT / "LISEZ-MOI.txt").write_text(f"{MENTION}\n\nAnnexes consultables : ouvrir index.html dans un navigateur (fichier autonome, hors ligne). Un fichier CSV par table (UTF-8, séparateur « ; »).\nRégénérer : python refonte/outils/generer_annexes_consultables.py\n", encoding="utf-8")
print(len(TABLES), "tables ;", sum(len(t["lignes"]) for t in TABLES), "lignes ;", len(f5), "passages ⚪ ;", (OUT / "index.html").stat().st_size // 1024, "Ko")
for t in TABLES:
    print(" ", t["id"], len(t["lignes"]), t["titre"][:60])
