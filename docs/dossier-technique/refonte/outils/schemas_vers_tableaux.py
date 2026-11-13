"""Produit un brouillon de tableau à partir d'un schéma Mermaid « à remplacer par un tableau » (plan §4).
Usage : python schemas_vers_tableaux.py <dossier_src> <dossier_sortie> S02 S14 ...
Le brouillon liste les éléments et les transitions du schéma ; il sera rédigé en phrases aux phases 5 à 7."""
import re
import sys
from pathlib import Path

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
for sid in sys.argv[3:]:
    f = next(SRC.glob(f"{sid}_*.mmd"))
    t = f.read_text(encoding="utf-8")
    noms = {}
    for m in re.finditer(r'\b(\w+)\s*[\[\(]{1,2}"([^"]+)"[\]\)]{1,2}', t):
        noms.setdefault(m.group(1), re.sub(r"<br/?>", " ", m.group(2)))
    for m in re.finditer(r'^\s*(\w+)\s*$', t, re.M):
        pass
    liens = []
    for ligne in t.split("\n"):
        if "-->" not in ligne and "-.->" not in ligne and "---" not in ligne:
            continue
        parts = re.split(r"(?:--\s*\"[^\"]*\"\s*)?(?:-->|-\.->|---|-\.-|\.->)", ligne)
        # étiquettes : |"..."| au début de chaque segment suivant ; ou -- "..." --> avant la flèche
        labels = re.findall(r"\|\"([^\"]*)\"\|", ligne)
        precedents = None
        k = 0
        for i, seg in enumerate(parts):
            m_id = re.search(r"(\w+)\s*(?:[\[\(]{1,2}\"[^\"]*\"[\]\)]{1,2})?\s*(?:\|\"[^\"]*\"\|)?\s*$" if i == 0 else r"^\s*(?:\|\"[^\"]*\"\|)?\s*(\w+)", seg)
            cible = m_id.group(1) if m_id else None
            if i > 0 and precedents and cible:
                lab = ""
                m_l = re.match(r"^\s*\|\"([^\"]*)\"\|", seg)
                if m_l:
                    lab = m_l.group(1)
                liens.append((precedents, re.sub(r"<br/?>", " ", lab), cible))
            # nœud de sortie du segment : dernier identifiant du segment
            m_out = re.findall(r"\b([A-Za-z_]\w*)\b(?=\s*(?:[\[\(]{1,2}\"[^\"]*\"[\]\)]{1,2})?\s*$)", seg.strip())
            precedents = (cible if i > 0 else (m_id.group(1) if m_id else None)) or precedents
    L = [f"<!-- Brouillon généré depuis {f.name} : à rédiger en phrases ; le schéma est remplacé par ce tableau (plan §4). -->", "", "| Élément | Contenu |", "|---|---|"]
    L += [f"| `{k}` | {v} |" for k, v in noms.items()]
    L += ["", "| De | Condition ou passage | Vers |", "|---|---|---|"]
    L += [f"| {noms.get(a, a)} | {lab or '—'} | {noms.get(b, b)} |" for a, lab, b in liens]
    (OUT / f"{sid}_tableau.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(sid, len(noms), "éléments", len(liens), "transitions")
