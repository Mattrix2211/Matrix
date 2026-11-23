"""Chemins de l'ancienne édition : à sa place d'origine ou, après le basculement V3, dans archive_G0_initial/.
Les clés de la correspondance (« diffusable/01_vision.md ») restent celles de l'édition initiale."""
from pathlib import Path

DT = Path(__file__).resolve().parents[2]
ARCHIVE = DT / "archive_G0_initial"


def ancien(rel):
    p = DT / rel
    return p if p.exists() else ARCHIVE / rel


def glob_ancien(motif):
    trouves = {cle(p): p for base in (DT, ARCHIVE) for p in base.glob(motif)}
    return [trouves[k] for k in sorted(trouves)]


def cle(p):
    rel = Path(p).resolve().relative_to(DT)
    return str(rel.relative_to("archive_G0_initial") if rel.parts[0] == "archive_G0_initial" else rel)
