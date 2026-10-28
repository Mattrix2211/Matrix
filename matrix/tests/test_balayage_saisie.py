"""Balayage générique : aucune route ne doit répondre 500 à un identifiant mal formé.

Pour chaque route (jeu de démonstration, deux comptes de rôles différents), chaque paramètre
d'identifiant lu par le code de l'application reçoit tour à tour une valeur non numérique, une
valeur énorme et un NUL. Les exceptions de programmation (500) sont listées avec leur emplacement."""
import re
import sys
import traceback
import uuid
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.db import transaction
from django.test import Client, TestCase
from django.urls import URLResolver, get_resolver, resolve

# Routes sans rapport avec la saisie d'identifiants (administration Django, fichiers, session).
EXCLUSIONS = ("admin/", "static", "media", "logout", "login", "accounts/login")
NOMS_EXPLICITES = {
    "marin", "asset", "section", "ship", "service", "sector", "user", "version", "creneau", "ordre", "assigne",
    "interlocuteur", "responsable", "document", "tache", "piece", "fonction", "course", "poste", "navire", "type",
    "folder", "location", "parent", "batiment", "cible", "perimetre", "objet", "equipement", "specialite",
}
# Paramètres de structure d'un assistant en plusieurs étapes : ils restent valides pour que la requête
# aille jusqu'aux contrôles d'identifiants des étapes suivantes (« etape » : règles puis vérification).
COMPAGNONS = {"type_liste": "creer_quart", "date_debut": "2026-11-01", "date_fin": "2026-11-30"}
ETAPES = ("3", "4")
MOTIF_ID = re.compile(r"(^|_)(id|ids|pk)$|fonction|ordre|rang|numero|cible|perimetre")
LECTURE_PARAMETRE = re.compile(
    r"(?:POST|GET|data|donnees|valeurs)(?:\.get|\.getlist)?\(\s*['\"](\w+)['\"]|(?:POST|GET)\[['\"](\w+)['\"]\]")
TOUS_LES_ACTIONS = re.compile(r"action\s+in\s+\(([^)]*)\)", re.S)


def _routes(patterns, prefixe=""):
    for motif in patterns:
        brut = prefixe + str(motif.pattern)
        if isinstance(motif, URLResolver):
            yield from _routes(motif.url_patterns, brut)
        else:
            yield brut


def _url(brut):
    if brut.startswith("^") or "(?P" in brut or "[" in brut:
        brut = re.sub(r"\(\?P<\w+>[^)]*\)", "1", brut).replace("^", "").replace("$", "").replace("\\.", ".")
        if any(c in brut for c in "[(*+?\\"):
            return None
    brut = re.sub(r"<int:\w+>", "1", brut)
    brut = re.sub(r"<uuid:\w+>", str(uuid.uuid4()), brut)
    brut = re.sub(r"<(str|slug|path):\w+>", "x", brut)
    brut = re.sub(r"<\w+>", "x", brut)
    return None if "<" in brut else "/" + brut


def _module_de_la_vue(url):
    try:
        vue = resolve(url).func
    except Exception:
        return None
    classe = getattr(vue, "view_class", None) or getattr(vue, "cls", None) or vue
    return sys.modules.get(getattr(classe, "__module__", ""))


def _sources_de_l_app(url):
    """Texte des fichiers Python de l'application qui porte la vue (les actions y sont réparties)."""
    module = _module_de_la_vue(url)
    fichier = getattr(module, "__file__", None)
    if not fichier:
        return ""
    dossier = Path(fichier).parent
    return "\n".join(f.read_text(errors="ignore") for f in sorted(dossier.glob("*.py")) if "test" not in f.name)


def _extraire(texte):
    noms = {a or b for a, b in LECTURE_PARAMETRE.findall(texte)}
    noms = sorted(n for n in noms if MOTIF_ID.search(n) or n in NOMS_EXPLICITES)
    actions = set(re.findall(r"action\s*==\s*['\"]([\w-]+)['\"]", texte))
    for liste in TOUS_LES_ACTIONS.findall(texte):
        actions |= set(re.findall(r"['\"]([\w-]+)['\"]", liste))
    return noms, sorted(actions)


def _parametres_et_actions(url):
    """(paramètres et actions de l'application, paramètres et actions du seul module de la vue)."""
    module = _module_de_la_vue(url)
    propre = Path(module.__file__).read_text(errors="ignore") if getattr(module, "__file__", None) else ""
    compagnons = {nom: valeur for nom, valeur in COMPAGNONS.items() if f'"{nom}"' in propre or f"'{nom}'" in propre}
    if '"etape"' in propre:
        compagnons["etape"] = ETAPES
    return _extraire(_sources_de_l_app(url)), _extraire(propre), compagnons


class BalayageIdentifiantsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def test_aucune_route_ne_repond_500_a_un_identifiant_mal_forme(self):
        urls = sorted({u for u in map(_url, _routes(get_resolver().url_patterns))
                       if u and not any(u.lstrip("/").startswith(e) for e in EXCLUSIONS)})
        plan = [(u, *_parametres_et_actions(u)) for u in urls]
        erreurs = {}
        requetes = 0
        for compte in ("admin", "chef_section_a"):
            client = Client(raise_request_exception=True)
            client.login(username=compte, password="admin" if compte == "admin" else "pass")
            for url, (noms, actions), (noms_propres, actions_propres), compagnons in plan:
                if not noms:
                    continue
                # Tous les paramètres ensemble pour chaque valeur hostile, puis un par un dans le module de la vue.
                essais = [({n: valeur for n in noms}, "tous", actions) for valeur in ("abc", "9" * 30, "a\x00b")]
                essais += [({n: "abc"}, n, actions_propres) for n in noms_propres]
                variantes = [dict(compagnons, etape=e) for e in ETAPES] if "etape" in compagnons else [compagnons]
                essais = [(donnees, etiquette, liste_actions, base) for donnees, etiquette, liste_actions in essais for base in variantes]
                for donnees, etiquette, liste_actions, base in essais:
                    for action in (liste_actions or [None]):
                        corps = {**donnees, **base, **({"action": action} if action else {})}
                        for methode in ("get", "post"):
                            if methode == "get" and action:
                                continue
                            requetes += 1
                            try:
                                with transaction.atomic():
                                    getattr(client, methode)(url, corps)
                            except Exception as exc:
                                pile = [t for t in traceback.extract_tb(exc.__traceback__)
                                        if ("/pgc/" in t.filename or "/Matrix/" in t.filename) and "/tests/" not in t.filename]
                                lieu = f"{pile[-1].filename.rsplit('/', 2)[-2]}/{pile[-1].filename.rsplit('/', 1)[-1]}:{pile[-1].lineno}" if pile else "?"
                                erreurs.setdefault((lieu, type(exc).__name__), f"{methode.upper()} {url} {etiquette} action={action}")
        self.assertGreater(requetes, 1000)
        self.assertEqual(erreurs, {}, "Routes en erreur 500 (emplacement, exception) :\n" + "\n".join(
            f"{k} <- {v}" for k, v in sorted(erreurs.items())))
