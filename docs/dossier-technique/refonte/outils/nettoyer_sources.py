"""Nettoyage mécanique des sources converties : plages de décisions dépliées, clés de rôle en libellés, chemins de code retirés des
paragraphes « Sources » des documents non techniques. Idempotent. Usage : python nettoyer_sources.py <RF|GU|DT> ..."""
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DOSSIER = {"GU": "1_guide_utilisateur", "RF": "2_referentiel_fonctionnel", "DT": "3_dossier_technique"}
ROLES = {"ADMIN_GENERAL": "administrateur général", "ADMIN_NAVIRE": "administrateur d'unité", "COMMANDANT_EN_SECOND": "commandant en second",
         "COMMANDANT": "commandant", "ETAT_MAJOR": "état-major", "CHEF_SERVICE": "chef de service", "CHEF_SECTEUR": "chef de secteur",
         "CHEF_SECTION": "chef de section", "EQUIPIER": "équipier"}


def deplier(m):
    pref, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    return ", ".join(f"`DEC-{pref}-{i:02d}`" for i in range(a, b + 1))


def nettoyer(t, technique):
    t = re.sub(r"`DEC-([A-Z]{2,4})-(\d{2})` (?:à|–) `?(?:DEC-[A-Z]{2,4}-)?(\d{2})`?", deplier, t)
    if technique:
        return t
    for k, v in ROLES.items():
        t = re.sub(rf"\(`?{k}`?\)", "", t) if False else re.sub(rf"\b{k}\b", v, t)
    t = t.replace("Chart.js", "bibliothèque de graphiques")
    def sources(m):
        p = m.group(0)
        p = re.sub(r"`[^`]*(?:\.py|\.html|\.js|\.md|/)[^`]*`(?: \([^)]*\))?", "", p)
        p = re.sub(r"références ligne par ligne dans la partie restreinte du dossier\.?", "références de code dans le dossier technique à accès restreint.", p)
        p = re.sub(r"\s+,", ",", p)
        p = re.sub(r"(?:,\s*){2,}", ", ", p)
        p = re.sub(r":\s*,\s*", ": ", p)
        p = re.sub(r"\s{2,}", " ", p)
        return p
    t = re.sub(r"(?m)^\*\*Sources[^\n]*", sources, t)
    return t


if __name__ == "__main__":
    for code in sys.argv[1:]:
        for f in sorted((R / DOSSIER[code]).glob("[0-9][0-9]_*.md")):
            a = f.read_text(encoding="utf-8")
            b = nettoyer(a, code == "DT")
            if a != b:
                f.write_text(b, encoding="utf-8")
                print("nettoyé", f.name)
