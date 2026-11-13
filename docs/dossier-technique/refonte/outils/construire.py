"""Constructeur unique des documents de la refonte (GU, RF, DT, RE) : Markdown -> HTML -> PDF.

Usage : python construire.py <GU|RF|DT|RE> --sortie <dossier> [--pilote] [--fichiers a.md b.md] [--sans-pdf]

- numérotation automatique des titres (1, 1.1, 1.1.1) et ancres stables (rf-5-2) ;
- substitution {{fait:nom}} (faits.yaml), {{mention}}, {{ref}} ;
- renvois [[RF 5.2]] résolus et consignés (refs.json) ; ancres consignées (ancres.json) ;
- sommaire paginé en deux passes (page mesurée sur le PDF de la passe 1, insérée à la passe 2) ;
- mention provisoire en en-tête de chaque page ; aucune ressource distante.
Directives Markdown : @capture id=... titre="..." texte="..." [renvoi="..."] [provisoire=1]
                      <!-- paysage --> ... <!-- /paysage -->     <!-- partie: Titre -->
                      <!-- couvre: ancien_fichier | titre -->    <!-- retire: ancien_fichier | titre | motif -->
"""
import argparse
import html
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import markdown
import pypdfium2 as pdfium
import yaml

RACINE = Path(__file__).resolve().parent.parent          # refonte/
DT = RACINE.parent                                          # docs/dossier-technique/
ident = yaml.safe_load((RACINE / "config/identite.yaml").read_text(encoding="utf-8"))
docs = yaml.safe_load((RACINE / "config/documents.yaml").read_text(encoding="utf-8"))
faits = yaml.safe_load((RACINE / "faits.yaml").read_text(encoding="utf-8"))

ETIQUETTES = {"🟢": ("v", "🟢"), "🔵": ("b", "🔵"), "🟣": ("p", "🟣"), "⚪": ("n", "◯")}
CORRESPONDANCE_TECHNIQUE = ("EB-2026-11-11 = état applicatif `6d6d0be` (branche `claude/l03-suppression-sure-v11`), non fusionné dans `main`. "
                            "Cette correspondance n'existe que dans les documents techniques à accès restreint.")


def substituer(texte, code):
    def fait(m):
        nom = m.group(1)
        if nom not in faits:
            sys.exit(f"fait inconnu : {nom}")
        v = faits[nom]["valeur"]
        return f"{v:,}".replace(",", " ") if isinstance(v, int) and v >= 1000 else str(v)
    texte = re.sub(r"\{\{fait:([a-z_0-9]+)\}\}", fait, texte)
    texte = texte.replace("{{mention}}", ident["mention"]).replace("{{ref}}", ident["reference_documentaire"])
    return texte


def separer_listes(texte):
    sortie, precedent, dans_code = [], "", False
    for ligne in texte.split("\n"):
        if ligne.lstrip().startswith("```"):
            dans_code = not dans_code
        est_item = bool(re.match(r"^(\s*)([-*+]|\d+\.) ", ligne))
        prec_item = bool(re.match(r"^(\s*)([-*+]|\d+\.) ", precedent)) or precedent.startswith("  ")
        if not dans_code and est_item and precedent.strip() and not prec_item and not precedent.lstrip().startswith(("|", ">")):
            sortie.append("")
        sortie.append(ligne)
        precedent = ligne
    return "\n".join(sortie)


_REG = {}


def registre():
    if not _REG:
        _REG.update(json.loads((RACINE / "5_registre/registre.json").read_text(encoding="utf-8")))
    return _REG


def table_decisions(ids):
    reg = {d["id"]: d for d in registre()["decisions"]}
    L = ["| Décision | Règle validée par le PO | État dans l'état B |", "|---|---|---|"]
    for i in ids:
        if i not in reg:
            sys.exit(f"décision inconnue du registre : {i}")
        d = reg[i]
        lots = f" ({', '.join(d['lots'])})" if d["lots"] else ""
        L.append(f"| `{i}` | {d['regle'].replace('|', '/')} | {d['etat_dans_etat_b']}{lots} |")
    return "\n".join(L)


def court(t, n):
    if len(t) <= n:
        return t
    return t[:n].rsplit(' ', 1)[0].rstrip(' ,;(') + ' …'


def table_ecarts(ids):
    r = registre()
    tout = {e["id"]: e for k in ("ecarts", "nouveaux_ecarts", "points_a_confirmer", "propositions") for e in r[k]}
    L = ["| Identifiant | Sujet | Profils concernés | Statut |", "|---|---|---|---|"]
    for i in ids:
        if i not in tout:
            sys.exit(f"identifiant inconnu du registre : {i}")
        e = tout[i]
        L.append(f"| **{i}** | {court(re.sub(r'[`*]', '', e.get('titre', '')), 150).replace('|', '/')} | {e.get('profils_concernes') or '—'} | {e['statut']} |")
    return "\n".join(L)


def table_routes(prefixes):
    inv = json.loads((DT / "couverture/etat_B/inventaire.json").read_text(encoding="utf-8"))
    L = ["| Chemin | Nom | Vue |", "|---|---|---|"]
    n = 0
    for r in inv["routes"]:
        if any(r["route"].startswith(p) for p in prefixes):
            L.append(f"| `{r['route']}` | {r['nom'] or '—'} | `{r['vue']}` |")
            n += 1
    if not n:
        sys.exit(f"aucune route pour {prefixes}")
    return "\n".join(L)


def capture_html(args, code, captures_dir, manifeste):
    d = dict(a.split("=", 1) for a in shlex.split(args))
    m = manifeste.get(d["id"])
    if m is None:
        sys.exit(f"capture inconnue du manifeste : {d['id']}")
    fichier = (captures_dir / m["fichier"]).resolve()
    reperes = "".join(f'<div class="rep" style="left:{r["x"]*100:.2f}%;top:{r["y"]*100:.2f}%">{r["n"]}</div>' for r in m.get("reperes") or [])
    legende_rep = " ".join(f'<b>{r["n"]}</b> {html.escape(r["texte"])}' for r in m.get("reperes") or [])
    prov = '<span class="prov"> · capture provisoire du 12/11/2026, reprise prévue en phase 4</span>' if d.get("provisoire") else ""
    renvoi = f" · {html.escape(d['renvoi'])}" if d.get("renvoi") else ""
    sec = html.escape(d.get("section", ""))
    return (f'<section class="paysage capture"><div class="cap-sec">{sec}</div><div class="cap-titre">{html.escape(d["titre"])}</div>'
            f'<p class="cap-texte">{html.escape(d.get("texte", ""))}</p>'
            f'<div class="cap-cadre"><img src="{fichier.as_uri()}">{reperes}</div>'
            f'<p class="cap-legende"><b>Écran réel 🟢 · profil de démonstration : {html.escape(m["profil"])}</b>{renvoi}'
            f'{(" · Repères : " + legende_rep) if legende_rep else ""}{prov}</p></section>')


def convertir(chemin, code, cfg_doc, ctx):
    brut = substituer(chemin.read_text(encoding="utf-8"), code)
    couvre = [tuple(x.strip() for x in m.split("|")) for m in re.findall(r"<!--\s*couvre:\s*(.+?)\s*-->", brut)]
    retire = [tuple(x.strip() for x in m.split("|")) for m in re.findall(r"<!--\s*retire:\s*(.+?)\s*-->", brut)]
    ctx["couvre"] += couvre
    ctx["retire"] += retire
    partie = re.search(r"<!--\s*partie:\s*(.+?)\s*-->", brut)
    brut = re.sub(r"<!--\s*(couvre|retire|partie):.*?-->", "", brut)
    brut = re.sub(r"<!--\s*paysage\s*-->", '<section class="paysage tableau">', brut)
    brut = re.sub(r"<!--\s*/paysage\s*-->", "</section>", brut)
    brut = re.sub(r"^@decisions (.+)$", lambda m: "\n" + table_decisions(m.group(1).split()) + "\n", brut, flags=re.M)
    brut = re.sub(r"^@routes (.+)$", lambda m: "\n" + table_routes(m.group(1).split()) + "\n", brut, flags=re.M)
    brut = re.sub(r"^@ecarts (.+)$", lambda m: "\n" + table_ecarts(m.group(1).split()) + "\n", brut, flags=re.M)
    brut = re.sub(r"^@capture (.+)$", lambda m: "\n\n" + capture_html(m.group(1), code, ctx["captures_dir"], ctx["manifeste"]) + "\n\n", brut, flags=re.M)
    brut = separer_listes(brut)
    corps = markdown.markdown(brut, extensions=["tables", "fenced_code", "sane_lists", "md_in_html"])
    base = chemin.parent
    corps = re.sub(r'src="((?!file:|data:|http)[^"]+)"', lambda m: f'src="{(base / m.group(1)).resolve().as_uri()}"', corps)
    corps = re.sub(r"<p><img alt=\"([^\"]*)\" src=\"([^\"]+)\" ?/?></p>", r'<figure><img alt="\1" src="\2"><figcaption>\1</figcaption></figure>', corps)
    def taille_svg(m):
        chemin = Path(m.group(2).replace("file://", ""))
        try:
            vb = re.search(r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.]+) ([\d.]+)"', chemin.read_text(encoding="utf-8")[:2000])
            largeur = min(499.0, 0.52 * float(vb.group(3)))          # 0,52 pt par unité : texte de 18 px rendu à environ 9,4 pt
        except (OSError, AttributeError):
            largeur = 499.0
        return f'<img alt="{m.group(1)}" src="{m.group(2)}" style="width:{largeur:.0f}pt">'
    corps = re.sub(r'<img alt="([^"]*)" src="(file://[^"]+\.svg)"[^>]*>', taille_svg, corps)
    for e, (cls, glyphe) in ETIQUETTES.items():
        corps = corps.replace(e, f'<span class="et {cls}">{glyphe}</span>')
    return partie.group(1) if partie else None, corps


def numeroter(corps, code, compteurs, entrees):
    """Numérote h1/h2/h3 ; ajoute ancres et marqueurs de pagination ; remplit le sommaire."""
    def rep(m):
        niv = int(m.group(1))
        texte = m.group(2)
        if niv == 1:
            compteurs[0] += 1; compteurs[1] = compteurs[2] = 0
            num = f"{compteurs[0]}"
        elif niv == 2:
            compteurs[1] += 1; compteurs[2] = 0
            num = f"{compteurs[0]}.{compteurs[1]}"
        else:
            compteurs[2] += 1
            num = f"{compteurs[0]}.{compteurs[1]}.{compteurs[2]}"
        ident_ = f"{code.lower()}-{num.replace('.', '-')}"
        propre = re.sub(r"<[^>]+>", "", texte)
        entrees.append((niv, num, propre, ident_))
        return (f'<h{niv} id="{ident_}"><span class="marqueur">⟦{ident_}⟧</span>{num} {texte}</h{niv}>')
    return re.sub(r"<h([123])>(.*?)</h\1>", rep, corps, flags=re.S)


def resoudre_renvois(corps, code, ancres_globales, refs):
    def rep(m):
        cible_doc, num = m.group(1), m.group(2)
        refs.append((code, cible_doc, num))
        ident_ = f"{cible_doc.lower()}-{num.replace('.', '-')}"
        if cible_doc == code:
            return f'<a href="#{ident_}">{cible_doc} §{num}</a>'
        return f'<span class="renvoi">{cible_doc} §{num}</span>'
    return re.sub(r"\[\[(GU|RF|DT|RE|AC)\s+([0-9]+(?:\.[0-9]+){0,2})\]\]", rep, corps)


def construire_html(code, fichiers, pilote, pages=None):
    cfg = docs[code]
    ctx = {"couvre": [], "retire": [], "captures_dir": DT / "guide-visuel/captures", "manifeste": {}}
    mf = ctx["captures_dir"] / "manifeste.json"
    if mf.is_file():
        ctx["manifeste"] = {m["id"]: m for m in json.loads(mf.read_text(encoding="utf-8"))}
    compteurs, entrees, refs, blocs = [0, 0, 0], [], [], []
    for f in fichiers:
        partie, corps = convertir(f, code, cfg, ctx)
        corps = numeroter(corps, code, compteurs, entrees)
        corps = resoudre_renvois(corps, code, None, refs)
        if partie:
            blocs.append(f'<section class="partie"><h1 class="titre-partie">{html.escape(partie)}</h1></section>')
        classe = "chapitre" + (" fiche-module" if "fiche" in f.name else "")
        blocs.append(f'<section class="{classe}">{corps}</section>')
    # sommaire
    lis = []
    for niv, num, titre, ident_ in entrees:
        pg = (pages or {}).get(ident_, "000")
        lis.append(f'<li class="niv{niv}"><span class="t"><a href="#{ident_}">{num} {html.escape(titre)}</a></span><span class="p"></span><span class="n">{pg}</span></li>')
    toc = '<section class="toc"><h2>Sommaire</h2><ul>' + "".join(lis) + "</ul></section>"
    meta = [("Référence documentaire", ident["reference_documentaire"]), ("Série", ident["serie"]), ("Édition", ident["date_edition"]),
            ("État documentaire", ident["etat_documentaire"]), ("État décrit", ident["etat_reference"])]
    if cfg["technique"]:
        meta.append(("Correspondance applicative (accès restreint)", CORRESPONDANCE_TECHNIQUE.replace("`", "")))
    leg = " · ".join(f'<span class="et {c}">{g}</span> {html.escape(ident["legende_etiquettes"][k])}'
                     for k, (c, g) in zip(["reel", "cible", "proposition", "non_verifie"], ETIQUETTES.values()))
    couv = (f'<section class="couverture"><div class="mention">{html.escape(ident["mention"])}</div>'
            f'<div class="precaution">{html.escape(ident["precaution"])}</div>'
            f'<p class="serie">{html.escape(ident["serie"])}</p><h1>{html.escape(cfg["titre"])}</h1>'
            f'<div class="public">{html.escape(cfg["public"])}</div>'
            + ('<p><b>Maquette pilote (jalon V1)</b> : seul le chapitre « Maintenance » est rédigé ; le reste du document sera rédigé après validation du PO.</p>' if pilote else "")
            + '<table class="meta">' + "".join(f"<tr><td>{html.escape(a)}</td><td><b>{html.escape(b)}</b></td></tr>" for a, b in meta) + "</table>"
            f'<div class="legende">{leg}</div></section>')
    css = (RACINE / "gabarits/refonte.css").read_text(encoding="utf-8")
    page = (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{html.escape(cfg["titre"])} — {ident["reference_documentaire"]}</title>'
            f"<style>{css}</style></head><body>{couv}{toc}{''.join(blocs)}</body></html>")
    return page, entrees, refs, ctx


def imprimer(html_path, pdf_path, code):
    cfg = docs[code]
    conf = {"entete_gauche": f'{ident["reference_documentaire"]} · {code} · édition {ident["date_edition"]}',
            "entete_centre": ident["mention"], "entete_droite": ident["serie"],
            "pied_gauche": f'{cfg["titre"]} — {ident["etat_documentaire"]}'}
    cj = Path(str(pdf_path) + ".config.json")
    cj.write_text(json.dumps(conf, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["node", str(RACINE / "outils/imprimer.js"), str(html_path), str(pdf_path), str(cj)], capture_output=True, text=True)
    cj.unlink()
    if r.returncode:
        sys.exit(r.stderr)


def pages_des_titres(pdf_path, entrees):
    pdf = pdfium.PdfDocument(str(pdf_path))
    texte = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
    trouve = {}
    for _, _, _, ident_ in entrees:
        for i, t in enumerate(texte):
            if f"⟦{ident_}⟧" in t:
                trouve[ident_] = str(i + 1)
                break
    return trouve, len(pdf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code", choices=list(docs))
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--pilote", action="store_true")
    ap.add_argument("--fichiers", nargs="*")
    ap.add_argument("--sans-pdf", action="store_true")
    a = ap.parse_args()
    cfg = docs[a.code]
    dossier = RACINE / cfg["dossier"]
    fichiers = [dossier / f for f in a.fichiers] if a.fichiers else sorted(dossier.glob("[0-9][0-9]_*.md"))
    if not fichiers:
        sys.exit("aucun fichier source")
    out = Path(a.sortie).resolve(); out.mkdir(parents=True, exist_ok=True)
    page, entrees, refs, ctx = construire_html(a.code, fichiers, a.pilote)
    h = out / f"{a.code}.html"
    h.write_text(page, encoding="utf-8")
    (out / f"{a.code}.ancres.json").write_text(json.dumps([e[3] for e in entrees]), encoding="utf-8")
    (out / f"{a.code}.refs.json").write_text(json.dumps(refs), encoding="utf-8")
    (out / f"{a.code}.couverture.json").write_text(json.dumps({"couvre": ctx["couvre"], "retire": ctx["retire"]}, ensure_ascii=False), encoding="utf-8")
    if a.sans_pdf:
        print("HTML seulement :", h); return
    pdf = out / cfg["fichier_pdf"]
    imprimer(h, pdf, a.code)                                   # passe 1 : mesure des pages
    pages, n = pages_des_titres(pdf, entrees)
    page2, *_ = construire_html(a.code, fichiers, a.pilote, pages)
    h.write_text(page2, encoding="utf-8")
    imprimer(h, pdf, a.code)                                   # passe 2 : sommaire paginé
    pages2, n2 = pages_des_titres(pdf, entrees)
    if pages2 != pages:
        sys.exit("pagination instable entre les deux passes : sommaire inexact")
    print(f"{a.code} : {n2} pages -> {pdf.name}")


main()
