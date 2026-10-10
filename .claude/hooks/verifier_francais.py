#!/usr/bin/env python3
"""Contrôle de la langue des lignes ajoutées à l'index git (appelé par le hook de commit).

Règle (CLAUDE.md, principe n°1) : tout ce qui est lu par un humain est en français :
interface, commentaires, docstrings, documentation. Seul le code lui-même (identifiants,
mots-clés, noms de verbes HTTP...) peut être en anglais.

Le contrôle est heuristique : il repère des mots anglais courants, il ne comprend pas
la langue. Il ne regarde que les lignes AJOUTÉES (l'existant n'est pas concerné) et
uniquement les zones de texte : commentaires, docstrings, chaînes de caractères,
texte des gabarits, fichiers .md. Le code n'est jamais examiné.

Sortie : code 0 si rien de suspect, code 2 (avec la liste des lignes) sinon.
"""

import ast
import io
import re
import subprocess
import sys
import tokenize

# Mots d'interface typiquement laissés en anglais par oubli (sensibles à la casse :
# « Save » est suspect, « save » ou « SAVE » (nom technique) ne le sont pas).
MOTS_INTERFACE = re.compile(
    r"\b(Submit|Cancel|Loading|Save|Delete|Error:|Warning:|Success|Please|Click here)\b"
)

# Mots anglais courants qui ne sont pas des mots français. Une ligne est suspecte dès
# qu'elle en contient SEUIL_MOTS différents. On exclut volontairement les mots qui existent
# aussi en français (a, on, or, as, an, me, do, son...) ou qui sont du jargon de code
# (get, set, use, in, if).
MOTS_ANGLAIS = frozenset(
    """
    the with without should would could will which that this these those when where then
    than also from into only each every are was were been being have has does not but for
    of to it its you your can must all any see here there their they them what how why
    because before after between while during about above below over under again once
    just very more most some such other another both either neither much many few
    returns return raises called calls creates create checks check ensures ensure makes
    make gets sets uses used using allows allow needs need keeps keep means mean
    instead already still even since until unless whether
    """.split()
)
SEUIL_MOTS = 2

MOT = re.compile(r"[A-Za-z']+")
CODE_EN_LIGNE = re.compile(r"`[^`]*`")
URL = re.compile(r"https?://\S+")

# Chemins ignorés : code généré, bibliothèques tierces, archives, sous-module de design.
EXCLUS = re.compile(
    r"(^|/)(migrations|node_modules|vendor|archive|design|__pycache__)/"
    r"|\.min\.(js|css)$|package-lock\.json$"
    r"|(^|/)\.claude/hooks/verifier_francais\.py$"  # ce fichier contient les listes de mots anglais
)
EXTENSIONS = (".py", ".html", ".js", ".md", ".sh")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


# Mode « tout » (commit -a / -am) : l'index est encore vide au moment du contrôle, on
# compare donc l'arbre de travail à HEAD au lieu de l'index.
MODE_TOUT = "--tout" in sys.argv


def lire_source(chemin):
    if MODE_TOUT:
        try:
            with open(chemin, encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return ""
    return git("show", f":{chemin}")


def lignes_ajoutees(chemin):
    """Renvoie {numéro de ligne: texte} des lignes ajoutées pour un fichier."""
    sortie = git("diff", "HEAD" if MODE_TOUT else "--cached", "-U0", "--", chemin)
    resultat, courant = {}, 0
    for ligne in sortie.splitlines():
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", ligne)
        if m:
            courant = int(m.group(1))
        elif ligne.startswith("+") and not ligne.startswith("+++"):
            resultat[courant] = ligne[1:]
            courant += 1
    return resultat


def mots_anglais(texte):
    texte = URL.sub(" ", CODE_EN_LIGNE.sub(" ", texte))
    trouves = {m.lower() for m in MOT.findall(texte)} & MOTS_ANGLAIS
    return trouves


def suspect(texte, avec_interface=True):
    """Renvoie une explication si le texte semble anglais, sinon None."""
    if avec_interface:
        m = MOTS_INTERFACE.search(texte)
        if m:
            return f"mot d'interface en anglais : « {m.group(1)} »"
    mots = mots_anglais(texte)
    if len(mots) >= SEUIL_MOTS:
        return "phrase probablement en anglais (" + ", ".join(sorted(mots)[:5]) + ")"
    return None


# --- Python : commentaires, docstrings, chaînes ---------------------------------------


def zones_python(source):
    """Renvoie (commentaires, docstrings, chaînes) sous forme de listes (ligne, texte)."""
    commentaires, docstrings, chaines = [], [], []
    plages_doc = []
    try:
        arbre = ast.parse(source)
        for noeud in ast.walk(arbre):
            if isinstance(noeud, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                corps = noeud.body
                if (
                    corps
                    and isinstance(corps[0], ast.Expr)
                    and isinstance(corps[0].value, ast.Constant)
                    and isinstance(corps[0].value.value, str)
                ):
                    plages_doc.append((corps[0].lineno, corps[0].end_lineno))
        for debut, fin in plages_doc:
            for n in range(debut, fin + 1):
                docstrings.append(n)
        for jeton in tokenize.generate_tokens(io.StringIO(source).readline):
            if jeton.type == tokenize.COMMENT:
                commentaires.append((jeton.start[0], jeton.string.lstrip("#")))
            elif jeton.type == tokenize.STRING or jeton.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
                # Python 3.12 découpe les f-strings : le texte est dans FSTRING_MIDDLE.
                for n in range(jeton.start[0], jeton.end[0] + 1):
                    if n not in docstrings:
                        chaines.append((n, jeton.string))
    except (SyntaxError, tokenize.TokenError, IndentationError):
        # Repli : seules les lignes de commentaire pur sont examinées.
        for n, ligne in enumerate(source.splitlines(), 1):
            if ligne.strip().startswith("#"):
                commentaires.append((n, ligne.strip().lstrip("#")))
    return commentaires, docstrings, chaines


def controler_python(chemin, ajoutees, source):
    problemes = []
    commentaires, docstrings, chaines = zones_python(source)
    lignes = source.splitlines()
    vus = set()
    for n, texte in commentaires:
        if n in ajoutees and (n, "c") not in vus:
            vus.add((n, "c"))
            raison = suspect(texte, avec_interface=False)
            if raison:
                problemes.append((n, ajoutees[n], raison))
    for n in docstrings:
        if n in ajoutees and (n, "d") not in vus:
            vus.add((n, "d"))
            raison = suspect(lignes[n - 1] if n - 1 < len(lignes) else "", avec_interface=False)
            if raison:
                problemes.append((n, ajoutees[n], raison))
    for n, texte in chaines:
        if n in ajoutees and (n, "s") not in vus:
            vus.add((n, "s"))
            raison = suspect(texte)
            if raison:
                problemes.append((n, ajoutees[n], raison))
    return problemes


# --- Gabarits HTML --------------------------------------------------------------------

BALISES_TEMPLATE = re.compile(r"\{%.*?%\}|\{\{.*?\}\}")
COMMENTAIRE_GABARIT = re.compile(r"\{#(.*?)#\}|<!--(.*?)-->")
ATTRIBUTS_VISIBLES = re.compile(
    r"""\b(?:title|placeholder|aria-label|alt|label)\s*=\s*(?:"([^"]*)"|'([^']*)')"""
)
BALISE_HTML = re.compile(r"<[^>]*>?|^[^<]*>")


def textes_html(ligne):
    """Extrait les textes lisibles d'une ligne de gabarit (jamais le balisage)."""
    textes = []
    for m in COMMENTAIRE_GABARIT.finditer(ligne):
        textes.append(m.group(1) or m.group(2) or "")
    ligne = COMMENTAIRE_GABARIT.sub(" ", ligne)
    for m in ATTRIBUTS_VISIBLES.finditer(ligne):
        textes.append(m.group(1) or m.group(2) or "")
    ligne = BALISES_TEMPLATE.sub(" ", ligne)
    ligne = BALISE_HTML.sub(" ", ligne)
    # Une ligne sans balise ni guillemet d'attribut est du texte (ou du texte de bloc {% comment %}).
    if "=" not in ligne:
        textes.append(ligne)
    return textes


def controler_html(chemin, ajoutees):
    problemes = []
    for n, ligne in ajoutees.items():
        for texte in textes_html(ligne):
            raison = suspect(texte)
            if raison:
                problemes.append((n, ligne, raison))
                break
    return problemes


# --- JavaScript : commentaires et chaînes ---------------------------------------------

COMMENTAIRE_JS = re.compile(r"(?<![:\"'])//(.*)$|/\*(.*?)\*/|^\s*\*\s?(.*)$")
CHAINE_JS = re.compile(r"""(["'`])((?:\\.|(?!\1).)*)\1""")


def controler_js(chemin, ajoutees):
    problemes = []
    for n, ligne in ajoutees.items():
        raison = None
        for m in COMMENTAIRE_JS.finditer(ligne):
            texte = next((g for g in m.groups() if g), "")
            raison = suspect(texte, avec_interface=False)
            if raison:
                break
        if not raison:
            for m in CHAINE_JS.finditer(ligne):
                raison = suspect(m.group(2))
                if raison:
                    break
        if raison:
            problemes.append((n, ligne, raison))
    return problemes


# --- Markdown : documentation ---------------------------------------------------------


def controler_markdown(chemin, ajoutees, source):
    """Examine les lignes ajoutées hors blocs de code."""
    en_bloc, interdits = False, set()
    for n, ligne in enumerate(source.splitlines(), 1):
        if ligne.strip().startswith("```"):
            en_bloc = not en_bloc
            interdits.add(n)
        elif en_bloc:
            interdits.add(n)
    problemes = []
    for n, ligne in ajoutees.items():
        if n in interdits:
            continue
        raison = suspect(ligne)
        if raison:
            problemes.append((n, ligne, raison))
    return problemes


# --- Scripts shell : commentaires -----------------------------------------------------


def controler_shell(chemin, ajoutees):
    problemes = []
    for n, ligne in ajoutees.items():
        s = ligne.strip()
        if s.startswith("#") and not s.startswith("#!"):
            raison = suspect(s.lstrip("#"), avec_interface=False)
            if raison:
                problemes.append((n, ligne, raison))
    return problemes


def main():
    if MODE_TOUT:
        fichiers = git("diff", "HEAD", "--name-only", "--diff-filter=AM").splitlines()
    else:
        fichiers = git("diff", "--cached", "--name-only", "--diff-filter=AM").splitlines()
    rapport = []
    for chemin in fichiers:
        if not chemin.endswith(EXTENSIONS) or EXCLUS.search(chemin):
            continue
        ajoutees = lignes_ajoutees(chemin)
        if not ajoutees:
            continue
        source = lire_source(chemin)
        if chemin.endswith(".py"):
            problemes = controler_python(chemin, ajoutees, source)
        elif chemin.endswith(".html"):
            problemes = controler_html(chemin, ajoutees)
        elif chemin.endswith(".js"):
            problemes = controler_js(chemin, ajoutees)
        elif chemin.endswith(".md"):
            problemes = controler_markdown(chemin, ajoutees, source)
        else:
            problemes = controler_shell(chemin, ajoutees)
        for n, ligne, raison in sorted(problemes):
            rapport.append(f"{chemin}:{n}: {raison}\n    {ligne.strip()[:160]}")
    if rapport:
        print("\n".join(rapport), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
