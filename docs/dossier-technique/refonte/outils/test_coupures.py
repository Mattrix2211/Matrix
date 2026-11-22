"""Test ciblé du moteur de rendu : titres de chapitre et encadrés « Public » placés à toutes les hauteurs de page.
Usage : python test_coupures.py <dossier_temporaire>
Vérifie (1) qu'avec le gabarit actuel le contrôle ne signale aucune coupure, (2) qu'avec les règles de maintien retirées
le contrôle en signale (preuve que le contrôle et le banc d'essai détectent bien le défaut)."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import controles as c

RACINE = Path(__file__).parent.parent
css = (RACINE / "gabarits/refonte.css").read_text(encoding="utf-8")
sans_regles = re.sub(r"\.ligne-public \{ break-after: avoid; break-inside: avoid; \}", ".ligne-public { }", css).replace("h1 { break-inside: avoid; }", "")


def document(feuille, n=60):
    corps = []
    for k in range(n):
        lignes = " ".join(f"Ligne de remplissage {k}.{j} avec un peu de texte pour occuper la largeur de la page entière." for j in range(1 + (k * 7) % 31))
        corps.append(f"<p>{lignes}</p>")
        corps.append(f'<section class="chapitre suite"><h1 id="zz-{k + 1}"><span class="marqueur">⟦zz-{k + 1}⟧</span>{k + 1} Un titre de chapitre volontairement assez long pour occuper deux lignes de la page : mécanismes</h1>'
                     f'<div class="ligne-public"><p><b>Public :</b> développeurs, administrateurs · <b>Ce que vous y trouverez :</b> un encadré introductif assez long pour tenir sur trois lignes, avec plusieurs mots afin de forcer le retour à la ligne dans la largeur utile de la page imprimée.</p></div>'
                     f'<h2>{k + 1}.1 Premier titre</h2><p>Début du contenu.</p></section>')
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{feuille}</style></head><body>{"".join(corps)}</body></html>'


def rendre(dossier, nom, feuille):
    h = dossier / f"{nom}.html"
    h.write_text(document(feuille), encoding="utf-8")
    cfg = dossier / "cfg.json"
    cfg.write_text(json.dumps({"entete_gauche": "essai", "entete_centre": "essai", "pied_gauche": "essai"}), encoding="utf-8")
    pdf = dossier / f"{nom}.pdf"
    subprocess.run(["node", str(Path(__file__).parent / "imprimer.js"), str(h), str(pdf), str(cfg)], check=True)
    textes, _ = c.texte_pdf(pdf)
    return c.coupures_chapitres(textes, h)


if __name__ == "__main__":
    d = Path(sys.argv[1])
    d.mkdir(parents=True, exist_ok=True)
    ok = rendre(d, "gabarit_actuel", css)
    ko = rendre(d, "sans_regles", sans_regles)
    print(f"gabarit actuel : {len(ok)} coupure(s) sur 60 chapitres {ok[:3]}")
    print(f"sans les règles de maintien : {len(ko)} coupure(s) détectée(s)")
    sys.exit(0 if not ok and ko else 1)
