"""Barrière G2 : intégrité du registre vivant. Usage : python controler_registre.py <5_registre> <dossier-technique> <rapport.md>"""
import json
import re
import sys
from pathlib import Path

REG, DT, RAPPORT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
j = json.loads((REG / "registre.json").read_text(encoding="utf-8"))
ok, ko = [], []
def verif(c, msg):
    (ok if c else ko).append(msg)
verif(len(j["ecarts"]) == 26 and [e["id"] for e in j["ecarts"]] == [f"A{i}" for i in range(1, 27)], "26 écarts A1 à A26, dans l'ordre")
verif(len(j["points_a_confirmer"]) == 8, "8 points à confirmer (B1 à B8)")
verif(len(j["propositions"]) == 7, "7 propositions (D1 à D7)")
verif(len(j["nouveaux_ecarts"]) == 6, "6 nouveaux écarts (NE-01 à NE-06)")
verif(len(j["decisions"]) == 125, "125 décisions du dossier V1.2")
verif(len(j["anomalies_documentaires"]) == 38 and sum(1 for a in j["anomalies_documentaires"] if a["statut"].startswith("fusionnée")) == 2, "38 anomalies documentaires, dont 2 fusionnées (36 actives)")
verif(all(d["etat_dans_etat_b"] for d in j["decisions"]), "chaque décision porte un état dans l'état B")
verif(all(d["etat_methode"] for d in j["decisions"]), "chaque état de décision porte sa méthode")
txt = (REG / "ECARTS_ET_DECISIONS.md").read_text(encoding="utf-8")
plages = re.findall(r"`?\bDEC-[A-Z]{2,4}-\d{2}`?\s*(?:à|–)\s*`?(?:DEC-[A-Z]{2,4}-)?\d{2}\b", txt)
verif(not plages, f"aucune plage « DEC-… à … » ({len(plages)} trouvée(s))")
for a in ("A14", "A20", "A25"):
    e = next(x for x in j["ecarts"] if x["id"] == a)
    verif(bool(e.get("verifications")), f"{a} porte ses vérifications datées")
for f in ["tests_verification/verif_g0_a14.py", "tests_verification/verif_g0_a20.py", "tests_verification/verif_g0_a25.py", "navigateur_droits.md", "a14_navigateur_chef_section.png"]:
    verif((DT / "audit_preuves" / f).is_file(), f"preuve présente : audit_preuves/{f}")
verif(all(a["traite_par"] for a in j["anomalies_documentaires"]), "chaque anomalie documentaire a un traitement prévu")
verif(all(e["statut"].startswith("documenté, non arbitré") for e in j["ecarts"] + j["nouveaux_ecarts"]), "tous les écarts du logiciel sont « documenté, non arbitré »")
verif(all(p["statut"].startswith("🟣") for p in j["propositions"]), "les propositions restent 🟣 (jamais décisions)")
decis = {d["id"] for d in j["decisions"]}
verif(len(decis) == 125, "125 identifiants distincts")
from collections import Counter
c = Counter(d["etat_dans_etat_b"] for d in j["decisions"])
L = ["# Barrière G2 — registre vivant", "", "> Document de travail provisoire — 13/11/2026.", "", "| Contrôle | Résultat |", "|---|---|"]
L += [f"| {m} | ✅ |" for m in ok] + [f"| {m} | ❌ |" for m in ko]
L += ["", "## Répartition de l'état des 125 décisions", "", "| État dans l'état B | Nombre |", "|---|---|"] + [f"| {k} | {v} |" for k, v in c.most_common()]
L += ["", "Limite : « à instruire » (décisions sans lot dans le plan V1.2) n'est **pas** un constat de non-réalisation ; ces décisions devront être instruites une à une avant toute affirmation."]
RAPPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L[:6 + len(ok) + len(ko)]))
sys.exit(1 if ko else 0)
