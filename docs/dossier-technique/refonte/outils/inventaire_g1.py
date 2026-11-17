"""Inventaire des documents rédigés pour le rapport de barrière G1 : fichiers, mots, sections, captures, tables d'annexes."""
import json
import re
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DOCS = {"GU": ("1_guide_utilisateur", "Guide utilisateur illustré"), "RF": ("2_referentiel_fonctionnel", "Référentiel fonctionnel et de gouvernance"),
        "DT": ("3_dossier_technique", "Dossier technique de reprise"), "RE": ("5_registre", "Registre des écarts et décisions")}
L = ["| Document | Fichier source | Mots | Sections (niv. 1 / 2) | Captures |", "|---|---|---|---|---|"]
tot = {}
for code, (d, nom) in DOCS.items():
    mots = h1 = h2 = cap = 0
    for f in sorted((R / d).glob("[0-9][0-9]_*.md")):
        t = f.read_text(encoding="utf-8")
        corps = re.sub(r"<!--.*?-->", "", t, flags=re.S)
        m = len(re.findall(r"\w+", corps))
        a, b = len(re.findall(r"(?m)^# ", corps)), len(re.findall(r"(?m)^## ", corps))
        c = len(re.findall(r"(?m)^@capture", corps))
        L.append(f"| {code} | `{d}/{f.name}` | {m} | {a} / {b} | {c or ''} |")
        mots += m; h1 += a; h2 += b; cap += c
    tot[code] = (mots, h1, h2, cap)
S = ["| Document | Fichiers | Mots | Sections niv. 1 | Sections niv. 2 | Pages de capture |", "|---|---|---|---|---|---|"]
for code, (d, nom) in DOCS.items():
    n = len(list((R / d).glob("[0-9][0-9]_*.md")))
    S.append(f"| {nom} ({code}) | {n} | {tot[code][0]} | {tot[code][1]} | {tot[code][2]} | {tot[code][3] or '—'} |")
ms = json.loads((R / "captures/manifeste.json").read_text(encoding="utf-8"))
utilisees = set()
for code, (d, _) in DOCS.items():
    for f in (R / d).glob("*.md"):
        for m in re.finditer(r"^@capture (.+)$", f.read_text(encoding="utf-8"), flags=re.M):
            utilisees |= set(re.findall(r'\bc\d+="?([a-z0-9_]+)', m.group(1)))
inutilisees = sorted(m["id"] for m in ms if m.get("fichier") and m["id"] not in utilisees)
print("\n".join(S))
print()
print(f"Captures : {len(ms)} entrées au manifeste dont {sum(1 for m in ms if m.get('fichier'))} images ({len(utilisees)} utilisées, {len(inutilisees)} non utilisées) et {sum(1 for m in ms if not m.get('fichier'))} sans image ; non utilisées : {', '.join(inutilisees) or 'aucune'}")
(R / "baseline/inventaire_g1_fichiers.md").write_text("\n".join(L) + "\n", encoding="utf-8")
(R / "baseline/inventaire_g1_synthese.md").write_text("\n".join(S) + f"\n\nCaptures : {len(ms)} entrées au manifeste dont {sum(1 for m in ms if m.get('fichier'))} images ({len(utilisees)} utilisées, {len(inutilisees)} non utilisées) et {sum(1 for m in ms if not m.get('fichier'))} sans image ; non utilisées : {', '.join(inutilisees) or 'aucune'}.\n", encoding="utf-8")
