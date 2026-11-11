"""Contrôle de séparation entre le contenu diffusable et le contenu restreint (lecture seule), avant tout export.

Usage : python controle_separation.py <dossier_dossier_technique>

Règles appliquées aux fichiers de `diffusable/` : aucune référence de code `fichier.py:ligne` ni `fichier:ligne`, aucun nom de variable
d'environnement ou de secret, aucune commande d'exploitation, aucune adresse ou port, aucun lien ni chemin vers `restreint/`, aucune image
issue d'un schéma d'un chapitre restreint. Règles appliquées aux fichiers de `restreint/` : mention explicite de la diffusion restreinte.
Sortie : code 0 si aucune violation.
"""
import re
import sys
from pathlib import Path

D = Path(sys.argv[1]).resolve()
erreurs = []
INTERDITS = [
    (r"[\w/]+\.py:\d+", "référence de code fichier:ligne"),
    (r"`:\d+`", "référence de ligne isolée"),
    (r"\b(?:DJANGO|MATRIX|VAPID|CELERY|POSTGRES|DB|EMAIL|MEDIA|INACTIVITE|BROUILLONS|DOCUMENT|WEBPUSH)_[A-Z_]{3,}\b", "nom de variable d'environnement"),
    (r"manage\.py|celery -A|docker compose|pg_dump|collectstatic", "commande d'exploitation"),
    (r"127\.0\.0\.1|localhost:\d+", "adresse ou port"),
    (r"restreint/|\.\./restreint", "chemin vers la partie restreinte"),
    (r"\.env\b|\.sh\b", "fichier de configuration ou script"),
    (r"\bpass\b\s*[:=`]|mot de passe\s*[:=]", "mot de passe"),
]
diff = sorted(D.glob("diffusable/*.md")) + sorted(D.glob("diffusable/annexes/*.md"))
rest = sorted(D.glob("restreint/*.md")) + sorted(D.glob("restreint/annexes/*.md"))
restr_chap = {p.name for p in rest if p.name[:2].isdigit()}
# Schémas utilisés par un chapitre restreint (ensemble) et par un chapitre diffusable
svg_restr = set()
for p in rest:
    svg_restr |= set(re.findall(r"schemas/svg/(S\d+_\w+)\.svg", p.read_text(encoding="utf-8")))
svg_diff = set()
for p in diff:
    svg_diff |= set(re.findall(r"schemas/svg/(S\d+_\w+)\.svg", p.read_text(encoding="utf-8")))
for p in diff:
    t = p.read_text(encoding="utf-8")
    nom = p.relative_to(D)
    for motif, libelle in INTERDITS:
        if motif.startswith("restreint/") and p.name == "03_lire_ce_dossier.md":
            continue  # le chapitre 3 explique l'organisation en deux parties
        for m in re.finditer(motif, t):
            ligne = t.count("\n", 0, m.start()) + 1
            erreurs.append(f"{nom}:{ligne}: {libelle} dans un fichier diffusable : « {m.group(0)[:60]} »")
    for sid in re.findall(r"schemas/svg/(S\d+_\w+)\.svg", t):
        if sid in svg_restr and sid not in svg_diff - svg_restr and sid in svg_restr and not (D / "diffusable").exists():
            pass
for sid in sorted(svg_diff & svg_restr):
    erreurs.append(f"schéma {sid} utilisé à la fois par un chapitre diffusable et par un chapitre restreint")
for p in rest:
    if "restreinte" not in p.read_text(encoding="utf-8").lower():
        erreurs.append(f"{p.relative_to(D)}: pas de mention de diffusion restreinte")
print(f"{len(diff)} fichiers diffusables et {len(rest)} fichiers restreints contrôlés ; schémas : {len(svg_diff)} diffusables, {len(svg_restr)} restreints")
for e in erreurs:
    print("ERREUR", e)
print(f"{len(erreurs)} violation(s)")
sys.exit(1 if erreurs else 0)
