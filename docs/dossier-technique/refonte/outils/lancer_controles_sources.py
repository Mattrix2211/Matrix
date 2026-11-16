"""Phase 9 : construit les aperçus HTML des quatre documents (sans PDF) et rejoue les contrôles sur les sources (barrière G1).
Usage : python lancer_controles_sources.py [--sortie <dossier>]"""
import argparse
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--sortie", default=str(R / "apercus_G1"))
a = ap.parse_args()
out = Path(a.sortie)
out.mkdir(parents=True, exist_ok=True)
DOSSIERS = {"GU": "1_guide_utilisateur", "RF": "2_referentiel_fonctionnel", "DT": "3_dossier_technique", "RE": "5_registre"}
ETAT_B = Path(sys.argv[0]).resolve().parent.joinpath("etat_B_chemin.txt")
bloquants = 0
for code in DOSSIERS:                       # tous les aperçus d'abord : les renvois entre documents se résolvent sur des ancres à jour
    subprocess.run([sys.executable, str(R / "outils/construire.py"), code, "--sortie", str(out), "--sans-pdf"], check=True)
for code, dossier in DOSSIERS.items():
    sources = [str(p) for p in sorted((R / dossier).glob("[0-9][0-9]_*.md"))]
    r = subprocess.run([sys.executable, str(R / "outils/controles.py"), "doc", "--code", code, "--apercus", str(out), "--sources", *sources,
                        "--rapport", str(out / f"controles_{code}.md")], capture_output=True, text=True)
    print(f"=== {code} : code retour {r.returncode}")
    print(r.stdout[-700:] or r.stderr[-700:])
    bloquants += r.returncode
r = subprocess.run([sys.executable, str(R / "outils/controles.py"), "global", "--apercus", str(out), "--rapport", str(out / "controles_transversaux.md")], capture_output=True, text=True)
print(f"=== transversaux : code retour {r.returncode}")
print(r.stdout[-900:] or r.stderr[-900:])
sys.exit(1 if bloquants or r.returncode else 0)
