"""Contrôles automatisés de la refonte documentaire (C1 à C14 du plan). Ils complètent la vérification métier, ils ne la remplacent pas.

Usage :
  python controles.py doc  --code RF --apercus <dossier> [--sources a.md ...] [--pdf f.pdf] [--rapport r.md] [--pilote]
  python controles.py ancien --rapport baseline.md                # mesure de base sur l'ancien dossier (calibrage)
Sortie : 0 si aucun défaut bloquant, 1 sinon. Les avertissements ne bloquent pas.
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import yaml

RACINE = Path(__file__).resolve().parent.parent
DT = RACINE.parent
DEPOT = DT.parents[1]
docs = yaml.safe_load((RACINE / "config/documents.yaml").read_text(encoding="utf-8"))
sep_cfg = yaml.safe_load((RACINE / "config/separation.yaml").read_text(encoding="utf-8"))
termes = yaml.safe_load((RACINE / "config/termes.yaml").read_text(encoding="utf-8"))
faits = yaml.safe_load((RACINE / "faits.yaml").read_text(encoding="utf-8"))
MENTION = "DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE"
BASE_APP = "637de94"

PREFIXE = [""]
R = {}   # contrôle -> {"bloquant": [..], "avertissement": [..], "info": [..]}


def noter(c, niveau, msg):
    R.setdefault(c, {"bloquant": [], "avertissement": [], "info": []})[niveau].append(PREFIXE[0] + msg)


def texte_pdf(chemin):
    pdf = pdfium.PdfDocument(str(chemin))
    return [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))], pdf


def nettoyer(t):
    return re.sub(r"⟦[^⟧]*⟧", "", t)


# ---------- C5 séparation et classification ----------
def c5(code, textes, pages_pdf, technique):
    if not technique:
        for nom, motif in sep_cfg["interdits_non_techniques"].items():
            rx = re.compile(motif)
            for src, t in textes.items():
                t2 = re.sub(r"<!--.*?-->", "", t, flags=re.S)
                for m in rx.finditer(t2):
                    noter("C5", "bloquant", f"{src} : motif « {nom} » : {m.group(0)[:60]}")
            for i, t in enumerate(pages_pdf):
                for m in rx.finditer(nettoyer(t)):
                    noter("C5", "bloquant", f"PDF p.{i+1} : motif « {nom} » : {m.group(0)[:60]}")
    for mot in termes["interdits_partout"]:
        for src, t in textes.items():
            if mot in t:
                noter("C5", "bloquant", f"{src} : terme interdit « {mot} »")
        for i, t in enumerate(pages_pdf):
            if mot in t:
                noter("C5", "bloquant", f"PDF p.{i+1} : terme interdit « {mot} »")
    for i, t in enumerate(pages_pdf):
        if MENTION not in t:
            noter("C5", "bloquant", f"PDF p.{i+1} : mention provisoire absente")
    noter("C5", "info", f"{len(pages_pdf)} pages PDF contrôlées pour la mention")


# ---------- C8 mise en page (automatique) ----------
def c8(pdf_path, souple=False, exempt=()):
    textes, pdf = texte_pdf(pdf_path)
    n = len(pdf)
    faibles, orphelins, legendes, petites, syntaxe, residuels = [], [], [], [], [], []
    for i in range(n):
        pg = pdf[i]
        W, H = pg.get_size()
        t = textes[i]
        if i == 0 or i + 1 in exempt:
            continue
        # taux de remplissage vertical (hors en-tête et pied)
        img = pg.render(scale=0.3).to_pil().convert("L")
        import numpy as np
        a = np.array(img)
        h = a.shape[0]
        corps = a[int(h * 0.08):int(h * 0.925)]
        lignes = np.where((corps < 200).sum(axis=1) > 0)[0]
        remplissage = (lignes.max() / corps.shape[0]) if len(lignes) else 0
        est_dernier_de_section = False
        if remplissage < 0.40 and not est_dernier_de_section:
            faibles.append((i + 1, round(remplissage, 2)))
        tp = pg.get_textpage()
        # titre orphelin : marqueur de titre dans le dernier huitième de la page
        for m in re.finditer(r"⟦[^⟧]+⟧", t):
            try:
                l, b, r_, top = tp.get_charbox(m.start())
                if (H - top) / H > 0.86:
                    orphelins.append((i + 1, m.group(0)))
            except Exception:
                pass
        # légende en haut de page
        for m in re.finditer(r"(?m)^(Schéma|Figure|Capture) ", t):
            try:
                l, b, r_, top = tp.get_charbox(m.start())
                if (H - top) / H < 0.12:
                    legendes.append((i + 1, t[m.start():m.start() + 40]))
            except Exception:
                pass
        # tailles de police
        total = 0
        bas = 0
        for k in range(tp.count_chars()):
            try:
                c = tp.get_text_range(k, 1)
                if not c.strip() or not c.isalnum():
                    continue
                fs = pdfium_c.FPDFText_GetFontSize(tp, k)
                l, b, r_, top = tp.get_charbox(k)
                if (H - top) / H < 0.07 or (H - b) / H > 0.93:
                    continue
                total += 1
                if fs < 7.0:
                    bas += 1
            except Exception:
                break
        if total and bas / total > 0.10:
            petites.append((i + 1, f"{100*bas/total:.0f} % < 7 pt"))
        tt = nettoyer(t)
        for nom, rx in (("**", r"\*\*\S"), ("séparateur Markdown", r"\|\s*-{3,}"), ("accent grave", r"`"), ("titre #", r"(?m)^#{2,4} \S"), ("{{", r"\{\{"), ("[[", r"\[\["), ("pipe parasite", r"\s\|\s\|\s")):
            if re.search(rx, tt):
                syntaxe.append((i + 1, nom))
        if re.search(r"\.{2,}\s*000\b|\s000\s*$", tt, re.M):
            residuels.append((i + 1, "numéro de page 000"))
    cible = "avertissement" if souple else "bloquant"
    for p, r in faibles:
        noter("C8", "avertissement", f"p.{p} remplie à {int(r*100)} % (< 40 %)")
    for p, m in orphelins:
        noter("C8", "bloquant", f"p.{p} titre orphelin en bas de page ({m})")
    for p, s in legendes:
        noter("C8", "bloquant", f"p.{p} légende en haut de page, à vérifier : {s}")
    for p, s in petites:
        noter("C8", cible, f"p.{p} texte petit : {s}")
    for p, s in syntaxe:
        noter("C8", "bloquant", f"p.{p} syntaxe visible : {s}")
    for p, s in residuels:
        noter("C8", "bloquant", f"p.{p} {s}")
    noter("C8", "info", f"{n} pages ; {len(faibles)} pages < 40 % ; {len(orphelins)} titres orphelins ; {len(legendes)} légendes en haut ; {len(petites)} pages à texte petit ; {len(syntaxe)} syntaxes visibles")


# ---------- C6 liens, renvois, sommaire ----------
def c6(code, apercus, pdf_path):
    ancres = {}
    for f in Path(apercus).glob("*.ancres.json"):
        ancres[f.name.split(".")[0]] = set(json.loads(f.read_text(encoding="utf-8")))
    for f in Path(apercus).glob(f"{code}.refs.json"):
        for src, doc, num in json.loads(f.read_text(encoding="utf-8")):
            ident = f"{doc.lower()}-{num.replace('.', '-')}"
            if doc not in ancres:
                noter("C6", "avertissement", f"renvoi {doc} §{num} : document {doc} non construit dans cet aperçu")
            elif ident not in ancres[doc]:
                noter("C6", "bloquant", f"renvoi {doc} §{num} : section inexistante")
    if pdf_path:
        textes, pdf = texte_pdf(pdf_path)
        toc = [t for t in textes[:6] if "Sommaire" in t]
        if not toc:
            noter("C6", "bloquant", "sommaire introuvable")
        else:
            lignes = re.findall(r"(?m)^(\d+(?:\.\d+){0,2})\u2002?\s*(.+?)\s+(\d+)\s*$", "\n".join(toc))
            ids = {}
            for i, t in enumerate(textes):
                for m in re.finditer(r"⟦([a-z]+-[0-9-]+)⟧", t):
                    ids.setdefault(m.group(1), i + 1)
            fautes = 0
            for num, titre, p in lignes:
                ident = f"{code.lower()}-{num.replace('.', '-')}"
                if ident in ids and ids[ident] != int(p):
                    fautes += 1
                    noter("C6", "bloquant", f"sommaire : {num} annoncé p.{p}, trouvé p.{ids[ident]}")
            noter("C6", "info", f"{len(lignes)} entrées de sommaire vérifiées, {fautes} écart(s)")


# ---------- C3 faits chiffrés ----------
NOMS = {
    "n_modeles": r"modèles", "n_routes": r"routes", "n_migrations": r"migrations", "n_taches_planifiees": r"tâches planifiées",
    "n_actions_seuil": r"actions (?:à seuil|configurables)", "n_commandes": r"commandes de gestion", "n_modules_activables": r"modules activables",
}


def c3(textes):
    for src, t in textes.items():
        t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
        for nom, mot in NOMS.items():
            for m in re.finditer(rf"(\d[\d\u202f\u00a0 ]*)\s+{mot}", t):
                v = int(re.sub(r"\D", "", m.group(1)))
                if v != faits[nom]["valeur"] and v > 30:
                    noter("C3", "bloquant", f"{src} : « {m.group(0)} » ≠ {nom} = {faits[nom]['valeur']}")
                elif v == faits[nom]["valeur"]:
                    noter("C3", "avertissement", f"{src} : « {m.group(0)} » en dur (utiliser {{{{fait:{nom}}}}})")


# ---------- C7 décisions ----------
def c7(textes):
    reg = RACINE / "5_registre/registre.json"
    ids = set()
    if reg.is_file():
        ids = {e["id"] for e in json.loads(reg.read_text(encoding="utf-8"))["decisions"]}
    for src, t in textes.items():
        t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
        for m in re.finditer(r"\bDEC-[A-Z]{2,4}-\d{2}\s*(?:à|–|-|et)\s*(?:DEC-[A-Z]{2,4}-)?\d{2}\b", t):
            noter("C7", "bloquant", f"{src} : plage de décisions interdite : {m.group(0)}")
        for m in re.finditer(r"\bDEC-[A-Z]{2,4}-\d{2}\b", t):
            if ids and m.group(0) not in ids:
                noter("C7", "bloquant", f"{src} : décision inconnue du registre : {m.group(0)}")


# ---------- C14 données sensibles ----------
SENS = {"adresse électronique": r"[\w.+-]+@[\w-]+\.[a-z]{2,}", "chemin absolu": r"(?:/home/|/tmp/|/root/|C:\\\\)", "mot de passe en clair": r"(?i)(?:mot de passe|password)\s*[:=]\s*\S{6,}",
        "jeton": r"(?i)(?:token|secret)\s*[:=]\s*[A-Za-z0-9_\-]{12,}"}


def c14(textes, pages_pdf=()):
    for nom, rx in SENS.items():
        for src, t in textes.items():
            for m in re.finditer(rx, t):
                noter("C14", "bloquant", f"{src} : {nom} : {m.group(0)[:40]}")
        for i, t in enumerate(pages_pdf):
            for m in re.finditer(rx, t):
                noter("C14", "bloquant", f"PDF p.{i+1} : {nom} : {m.group(0)[:40]}")
    pw = Path("/tmp/claude-0/-home-user-Matrix/5a9ffb65-0eb5-5851-be68-103a39fb63e7/scratchpad/pw.txt")
    if pw.is_file():
        secret = pw.read_text().strip()
        if secret:
            for src, t in textes.items():
                if secret in t:
                    noter("C14", "bloquant", f"{src} : mot de passe de démonstration présent")
            for i, t in enumerate(pages_pdf):
                if secret in t:
                    noter("C14", "bloquant", f"PDF p.{i+1} : mot de passe de démonstration présent")


# ---------- C13 application intacte ----------
def c13():
    r = subprocess.run(["git", "diff", "--name-only", BASE_APP, "--", ".", ":!docs/dossier-technique"], cwd=DEPOT, capture_output=True, text=True)
    fichiers = [x for x in r.stdout.split("\n") if x.strip()]
    for f in fichiers:
        noter("C13", "bloquant", f"fichier hors dossier documentaire modifié depuis {BASE_APP} : {f}")
    noter("C13", "info", f"{len(fichiers)} fichier(s) hors documentation modifié(s) depuis {BASE_APP}")
    r2 = subprocess.run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=DEPOT, capture_output=True, text=True)
    noter("C13", "info", f"tête distante de main : {r2.stdout.split()[0][:12] if r2.stdout.strip() else 'illisible'}")


# ---------- C1 / C2 non-régression du contenu ----------
def c1(apercus, perimetre_anciens):
    """Chaque titre des anciens fichiers du périmètre est couvert ou retiré (commentaires couvre/retire)."""
    couv, ret = set(), set()
    for f in Path(apercus).glob("*.couverture.json"):
        j = json.loads(f.read_text(encoding="utf-8"))
        couv |= {tuple(x[:2]) for x in j["couvre"]}
        ret |= {tuple(x[:2]) for x in j["retire"]}
    lignes = list(csv.DictReader((RACINE / "MAPPING_ANCIEN_NOUVEAU.csv").open(encoding="utf-8"), delimiter=";"))
    n = manquants = 0
    for l in lignes:
        if l["ancien_fichier"] in perimetre_anciens and l["type"] != "schéma":
            n += 1
            cle = (l["ancien_fichier"], l["titre"])
            if cle not in couv and cle not in ret:
                manquants += 1
                noter("C1", "bloquant", f"non couvert : {l['ancien_fichier']} — {l['titre']}")
    noter("C1", "info", f"{n} titres du périmètre ; {n-manquants} couverts ou retirés ; {manquants} orphelin(s)")


def phrases_etiquetees(texte):
    sortie = []
    for p in re.split(r"(?<=[.!?])\s+|\n", texte):
        for e in "🔵🟣⚪":
            if e in p:
                mots = re.findall(r"[a-zàâçéèêëîïôûùüÿ]{5,}", p.lower())
                if len(mots) >= 4:
                    sortie.append((e, set(mots)))
    return sortie


def c2(anciens, nouveaux):
    ancien = []
    for t in anciens.values():
        ancien += phrases_etiquetees(t)
    nouveau = []
    for t in nouveaux.values():
        nouveau += phrases_etiquetees(t)
    perdues = 0
    for e, mots in ancien:
        meilleur = 0.0
        etiq_meilleur = None
        for e2, m2 in nouveau:
            j = len(mots & m2) / max(1, len(mots))
            if j > meilleur:
                meilleur, etiq_meilleur = j, e2
        if meilleur < 0.5:
            perdues += 1
            noter("C2", "avertissement", f"phrase {e} sans équivalent (revue manuelle) : {' '.join(sorted(mots))[:90]}")
        elif etiq_meilleur != e:
            noter("C2", "bloquant", f"étiquette changée {e} -> {etiq_meilleur} : {' '.join(sorted(mots))[:90]}")
    noter("C2", "info", f"{len(ancien)} phrases étiquetées 🔵🟣⚪ dans l'ancien périmètre ; {perdues} sans équivalent à revoir manuellement")


# ---------- C11 cohérence ----------
def c11(textes_par_doc):
    reg = RACINE / "5_registre/registre.json"
    ids_reg = set()
    if reg.is_file():
        j = json.loads(reg.read_text(encoding="utf-8"))
        ids_reg = {e["id"] for k in j if isinstance(j[k], list) for e in j[k]}
    etats = {}
    for doc, textes in textes_par_doc.items():
        for src, t in textes.items():
            t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
            for e_id in set(re.findall(r"\b(A\d{1,2}|B\d|D\d|NE-\d{2})\b", t)):
                if ids_reg and e_id not in ids_reg:
                    noter("C11", "bloquant", f"{doc}/{src} : identifiant {e_id} inconnu du registre")
            for p in re.split(r"(?<=[.!?])\s+|\n", t):
                for e_id in re.findall(r"\b(A\d{1,2}|NE-\d{2}|DEC-[A-Z]{2,4}-\d{2})\b", p):
                    for e in "🟢🔵🟣":
                        if e in p:
                            etats.setdefault(e_id, {}).setdefault(e, set()).add(doc)
    for e_id, d in etats.items():
        if "🟢" in d and "🔵" in d:
            noter("C11", "avertissement", f"{e_id} : étiqueté 🟢 dans {sorted(d['🟢'])} et 🔵 dans {sorted(d['🔵'])} (revue manuelle)")
    noter("C11", "info", f"{len(etats)} identifiants étiquetés comparés entre documents")


def rapport(chemin, titre):
    L = [f"# {titre}", "", "| Contrôle | Bloquants | Avertissements | Information |", "|---|---|---|---|"]
    for c in sorted(R, key=lambda x: int(x[1:])):
        r = R[c]
        L.append(f"| {c} | {len(r['bloquant'])} | {len(r['avertissement'])} | {'; '.join(r['info'])[:160]} |")
    for c in sorted(R, key=lambda x: int(x[1:])):
        r = R[c]
        if r["bloquant"] or r["avertissement"]:
            L += ["", f"## {c}"]
            L += [f"- **bloquant** {m}" for m in r["bloquant"][:80]] + [f"- avertissement {m}" for m in r["avertissement"][:40]]
            if len(r["bloquant"]) > 80:
                L.append(f"- … {len(r['bloquant'])-80} autre(s) bloquant(s)")
    Path(chemin).write_text("\n".join(L) + "\n", encoding="utf-8")
    total = sum(len(R[c]["bloquant"]) for c in R)
    print("\n".join(L[:4 + len(R)]))
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["doc", "ancien"])
    ap.add_argument("--code")
    ap.add_argument("--apercus")
    ap.add_argument("--sources", nargs="*")
    ap.add_argument("--pdf")
    ap.add_argument("--rapport", required=True)
    ap.add_argument("--pilote", action="store_true")
    ap.add_argument("--anciens", nargs="*", default=[])
    a = ap.parse_args()
    if a.mode == "ancien":
        # calibrage : mêmes contrôles sur l'existant (ancien PDF « diffusable » traité comme non technique)
        anc = {}
        for p in list(DT.glob("diffusable/[0-9]*.md")):
            anc[str(p.relative_to(DT))] = p.read_text(encoding="utf-8")
        pdfs = {"diffusable": DT / "pdf/Matrix_Dossier_technique_G0_DIFFUSABLE.pdf", "restreint": DT / "pdf/Matrix_Dossier_technique_G0_RESTREINT.pdf"}
        t_dif, _ = texte_pdf(pdfs["diffusable"])
        c5("ancien", {k: v for k, v in anc.items()}, t_dif, False)
        c3(anc)
        c7(anc)
        c14(anc, t_dif)
        for nom, p in pdfs.items():
            PREFIXE[0] = f"[{nom}] "
            c8(p, souple=True)
        PREFIXE[0] = ""
        c13()
        rapport(a.rapport, "Mesure de base — contrôles appliqués à l'ancien dossier (calibrage, non bloquant)")
        sys.exit(0)
    code = a.code
    cfg = docs[code]
    textes = {Path(f).name: Path(f).read_text(encoding="utf-8") for f in (a.sources or [])}
    pages_pdf = texte_pdf(a.pdf)[0] if a.pdf else []
    c5(code, textes, pages_pdf, cfg["technique"])
    c3(textes)
    c7(textes)
    c14(textes, pages_pdf)
    c6(code, a.apercus, a.pdf)
    if a.pdf:
        c8(a.pdf)
    anciens = set(a.anciens)
    if anciens:
        c1(a.apercus, anciens)
        an = {x: (DT / x).read_text(encoding="utf-8") for x in anciens}
        c2(an, textes)
    c13()
    tot = rapport(a.rapport, f"Contrôles {code} — {', '.join(sorted(R))}")
    sys.exit(1 if tot else 0)


if __name__ == "__main__":
    main()
