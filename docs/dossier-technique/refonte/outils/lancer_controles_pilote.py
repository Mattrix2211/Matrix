"""Construit les trois maquettes pilotes et leur applique les contrôles. Usage : python lancer_controles_pilote.py"""
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
CFG = {
    "RF": ("2_referentiel_fonctionnel", "Matrix_G0R2_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf", ["diffusable/12_maintenance_anomalies_tickets.md"]),
    "GU": ("1_guide_utilisateur", "Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf", []),
    "DT": ("3_dossier_technique", "Matrix_G0R2_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf", ["restreint/12_maintenance_anomalies_tickets_technique.md"]),
}
for code, (dossier, pdf, anciens) in CFG.items():
    subprocess.run([sys.executable, str(R / "outils/construire.py"), code, "--pilote", "--sortie", str(R / "apercus_V1")], check=True)
    sources = [str(p) for p in sorted((R / dossier).glob("[0-9][0-9]_*.md"))]
    cmd = [sys.executable, str(R / "outils/controles.py"), "doc", "--code", code, "--apercus", str(R / "apercus_V1"), "--sources", *sources,
           "--pdf", str(R / "apercus_V1" / pdf), "--rapport", str(R / f"apercus_V1/controles_{code}.md")]
    if anciens:
        cmd += ["--anciens", *anciens]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"=== {code} (code retour {r.returncode})")
    print(r.stdout[-900:] or r.stderr[-900:])
