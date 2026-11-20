"""Dessine le schéma S02 (carte des modules) : un schéma de flux à placement explicite, car le placement automatique ne rend pas lisible
le croisement de trois sortes de liens. Chaque lien est vérifié par le contrôle `controle_relations_s02.py` contre le texte du référentiel
(§ « Comment les modules s'enchaînent ») et l'inventaire des dépendances du code.
Trois sortes de flèches, de significations distinctes :
  - bleu plein : le module alimente le calendrier central ;
  - orange tirets : le module émet des notifications (flèche fonctionnelle : dans le code, c'est le paquet notifications qui importe ces modules) ;
  - gris pointillé : le groupe s'appuie sur le noyau commun (dépendance technique) ;
  - vert : une discussion s'attache à un objet de n'importe quel module.
Usage : python dessiner_s02.py <sortie.svg>"""
import sys
from html import escape

CAL = {"maintenance", "logistics", "quarts", "absences", "taches", "programme", "training"}      # §4.5 et sources du calendrier (S14)
NOT = {"maintenance", "logistics", "assets", "quarts", "absences", "taches", "demandes", "programme", "annonces", "training", "documentation", "retex"}
GROUPES = [
    ("Technique et logistique", ["maintenance", "logistics : tickets, stock", "assets", "rondes (retiré)"]),
    ("Vie quotidienne", ["quarts", "absences", "taches", "demandes", "programme", "postes", "dashboard"]),
    ("Communication", ["annonces"]),
    ("Connaissance", ["training", "documentation", "retex"]),
    ("Personnes et organisation", ["accounts, org"]),
    ("Pilotage", ["reports"]),
]
HUBS = [("Calendrier central", "calendar_app (vie quotidienne)", "cal"), ("Notifications", "notifications (communication)", "not")]
FS = 17
out, y = [], 20
GX, GW, CX, CW = 40, 410, 52, 230
BUS_C, BUS_N, HX, BRK = 520, 562, 664, 480
chips = {}
bas_groupes = []
for nom, mods in GROUPES:
    h0 = y
    y += 26
    for m in mods:
        if m.startswith("logistics"):
            y += 58                                   # rangée réservée à la relation maintenance → logistics
        chips[m.split(" :")[0].split(",")[0].split(" (")[0]] = (y, y + 30)
        out.append(f'<rect x="{CX}" y="{y}" width="{CW}" height="30" rx="4" fill="#e8eef7" stroke="#1f3b63"/><text x="{CX + 10}" y="{y + 21}" font-size="{FS}">{escape(m)}</text>')
        y += 36
    out.insert(0, f'<rect x="{GX}" y="{h0}" width="{GW}" height="{y - h0}" rx="6" fill="#fafbfd" stroke="#8d9bb0"/><text x="{GX + 8}" y="{h0 + 19}" font-size="{FS}" font-weight="700">{escape(nom)}</text>')
    bas_groupes.append((h0, y))
    y += 14
cy = lambda m: (chips[m][0] + chips[m][1]) / 2
bas = y + 40
# noyau commun
out.append(f'<rect x="{GX}" y="{bas}" width="920" height="40" rx="6" fill="#dfe7f3" stroke="#1f3b63" stroke-width="2"/><text x="{GX + 12}" y="{bas + 26}" font-size="{FS}" font-weight="700">matrix.core : rôles, périmètres, modules, audit, sécurité</text>')
out.append(f'<line x1="14" y1="{bas_groupes[0][0] + 14}" x2="14" y2="{bas}" stroke="#5a6b7d" stroke-width="2.5" stroke-dasharray="3 5"/>')
for (a, b) in bas_groupes:
    out.append(f'<line x1="14" y1="{a + 14}" x2="{GX}" y2="{a + 14}" stroke="#5a6b7d" stroke-width="2.5" stroke-dasharray="3 5"/>')
out.append(f'<path d="M14 {bas - 1} l-6 -10 l12 0 z" fill="#5a6b7d"/>')
# lien ticket : maintenance → logistics
ym, yl = chips["maintenance"], chips["logistics"]
out.append(f'<line x1="72" y1="{ym[1]}" x2="72" y2="{yl[0] - 1}" stroke="#1f3b63" stroke-width="3"/><path d="M72 {yl[0]} l-7 -11 l14 0 z" fill="#1f3b63"/>')
for i, t in enumerate(("ticket correctif créé si un contrôle", "est non conforme (matériel mobile)")):
    out.append(f'<text x="86" y="{ym[1] + 22 + i * 17}" font-size="16.5">{t}</text>')
# buses
def bus(xb, mods, couleur, tirets, hy):
    ys = [cy(m) for m in mods]
    dash = ' stroke-dasharray="9 5"' if tirets else ""
    for m in mods:
        out.append(f'<line x1="{CX + CW}" y1="{cy(m) + (-4 if xb == BUS_C else 4)}" x2="{xb}" y2="{cy(m) + (-4 if xb == BUS_C else 4)}" stroke="{couleur}" stroke-width="2.5"{dash}/>')
    top, bot = min(ys + [hy]) - 4, max(ys + [hy]) + 4
    out.append(f'<line x1="{xb}" y1="{top}" x2="{xb}" y2="{bot}" stroke="{couleur}" stroke-width="2.5"{dash}/>')
    out.append(f'<line x1="{xb}" y1="{hy}" x2="{HX - 2}" y2="{hy}" stroke="{couleur}" stroke-width="3"{dash}/><path d="M{HX - 1} {hy} l-10 -6 l0 12 z" fill="{couleur}"/>')
hy_c, hy_n = 130, 330
bus(BUS_C, sorted(CAL), "#1f3b63", False, hy_c)
bus(BUS_N, sorted(NOT), "#b35a00", True, hy_n)
for (titre, sous, k), hy in zip(HUBS, (hy_c, hy_n)):
    out.append(f'<rect x="{HX}" y="{hy - 30}" width="320" height="60" rx="6" fill="#e8eef7" stroke="#1f3b63" stroke-width="2"/><text x="{HX + 12}" y="{hy - 4}" font-size="{FS}" font-weight="700">{titre}</text><text x="{HX + 12}" y="{hy + 20}" font-size="16.5">{escape(sous)}</text>')
# discussions : accolade verte le long des groupes, reliée au pôle « Discussions »
hd = bas - 80
tops = [bas_groupes[0][0] + 14, bas_groupes[1][0] + 14, bas_groupes[2][0] + 14, bas_groupes[3][0] + 14]
out.append(f'<rect x="{HX}" y="{hd - 30}" width="320" height="60" rx="6" fill="#e9f4ea" stroke="#2f7d3a" stroke-width="2"/><text x="{HX + 12}" y="{hd - 4}" font-size="{FS}" font-weight="700">Discussions</text><text x="{HX + 12}" y="{hd + 20}" font-size="16.5">threads (communication)</text>')
out.append(f'<polyline points="{HX},{hd} {BRK},{hd} {BRK},{tops[0]}" fill="none" stroke="#2f7d3a" stroke-width="3"/>')
for t in tops:
    out.append(f'<line x1="{BRK}" y1="{t}" x2="{GX + GW + 3}" y2="{t}" stroke="#2f7d3a" stroke-width="3"/><path d="M{GX + GW} {t} l10 -6 l0 12 z" fill="#2f7d3a"/>')
out.append(f'<text x="{HX}" y="{hd - 58}" font-size="16.5" fill="#2f7d3a">s\'attache à un objet</text><text x="{HX}" y="{hd - 40}" font-size="16.5" fill="#2f7d3a">de n\'importe quel module</text>')
# légende
ly = bas + 70
leg = [("#1f3b63", "", "alimente le calendrier central"), ("#b35a00", "9 5", "émet des notifications"), ("#5a6b7d", "3 5", "s'appuie sur le noyau commun"), ("#2f7d3a", "", "discussion attachée à un objet")]
for i, (c, d, t) in enumerate(leg):
    x, yy = GX + (i % 2) * 460, ly + (i // 2) * 26
    dash = f' stroke-dasharray="{d}"' if d else ""
    out.append(f'<line x1="{x}" y1="{yy}" x2="{x + 36}" y2="{yy}" stroke="{c}" stroke-width="3"{dash}/><text x="{x + 46}" y="{yy + 5}" font-size="16.5">{escape(t)}</text>')
W, H = 1000, ly + 50
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="max-width:{W}px" font-family="DejaVu Sans, Arial, sans-serif" fill="#10213a">'
       + "".join(out) + "</svg>")
open(sys.argv[1], "w", encoding="utf-8").write(svg)
print(W, H)
