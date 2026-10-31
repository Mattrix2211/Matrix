"""Prépare une instance de démonstration isolée pour les tests avec des marins.

Base SQLite séparée, données entièrement fictives (seed_demo), aucune donnée opérationnelle.
À n'utiliser que sur un poste local ou un environnement isolé : mots de passe fictifs et DEBUG actif,
jamais sur un réseau opérationnel ou exposé.

Usage : python scripts/preparer_instance_test.py [--base chemin] [--reinitialiser | --verifier | --servir [--port N]]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DEMO = RACINE / "instance_test_marins"
HOTE = "127.0.0.1"  # jamais configurable : la démonstration n'écoute que sur la machine locale
PORT_PAR_DEFAUT = 8800
HOTES_LOCAUX = {"localhost", "127.0.0.1", "[::1]", "::1"}
# Seules ces variables du poste sont transmises ; tout le reste (bases, e-mail, Redis, clés) est volontairement absent.
VARIABLES_CONSERVEES = ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "PATHEXT",
                        "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "VIRTUAL_ENV")
SUFFIXE_MARQUEUR = ".instance_demo"  # fichier voisin écrit à la création : seule une base ainsi marquée peut être supprimée
COMPTES = (
    ("equipier_a", "Marin, équipage A : journée chargée (10 actions)"),
    ("equipier_a2", "Marin, équipage A : peu d'actions, dont une tâche en retard"),
    ("equipier_nor", "Marin, frégate Normandie : aucune action (liste vide)"),
    ("chef_secteur_a", "Chef de secteur, équipage A : supervision et équipe"),
    ("chef_secteur_b", "Chef de secteur, équipage B à terre : accès limité"),
)
# Lu par la sous-commande de contrôle : la connexion réelle doit viser la base de démonstration.
_CONTROLE = """
import json, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'matrix.settings'
import django
django.setup()
from django.db import connection
reglages = connection.settings_dict
from django.conf import settings
resultat = {'vendeur': connection.vendor, 'nom': str(reglages['NAME']), 'courriel': settings.EMAIL_BACKEND,
            'serveur_courriel': settings.EMAIL_HOST, 'push': bool(settings.VAPID_PRIVATE_KEY),
            'courtier': settings.CELERY_BROKER_URL + ' ' + settings.CELERY_RESULT_BACKEND,
            'hotes': list(settings.ALLOWED_HOSTS), 'media': str(settings.MEDIA_ROOT)}
if os.path.exists(resultat['nom']):
    connection.ensure_connection()
    resultat['fichier'] = connection.cursor().execute('PRAGMA database_list').fetchall()[0][2]
print(json.dumps(resultat))
"""


class RefusError(Exception):
    pass


def marqueur(base):
    return base.with_name(base.name + SUFFIXE_MARQUEUR)


def verifier_chemin(base, dossier_autorise, reinitialiser=False, lecture_seule=False):
    """Chemin de base validé et résolu, ou RefusError. Seul un fichier .sqlite3 situé directement dans le dossier
    de démonstration est admis ; un fichier existant doit y avoir été créé par ce script (marqueur voisin) pour être supprimé.
    En lecture seule (contrôle), l'existence du fichier est sans importance."""
    base = Path(base)
    if base.is_symlink() or dossier_autorise.is_symlink():
        raise RefusError("lien symbolique refusé")
    base = base.resolve()
    dossier = dossier_autorise.resolve()
    if base.suffix != ".sqlite3" or base.parent != dossier:
        raise RefusError(f"la base doit être un fichier .sqlite3 placé directement dans {dossier}")
    if base == (RACINE / "db.sqlite3").resolve():
        raise RefusError("cette base est celle de développement")
    if base.is_dir():
        raise RefusError("le chemin est un dossier")
    if base.exists() and not lecture_seule:
        if not reinitialiser:
            raise RefusError(f"{base} existe déjà : utilisez --reinitialiser pour repartir de zéro")
        if not marqueur(base).exists():
            raise RefusError("fichier existant non créé par ce script (marqueur absent) : suppression refusée, supprimez-le à la main")
    return base


def environnement_demo(base):
    """Environnement du processus fils, construit en liste blanche : base SQLite explicite, .env du poste ignoré,
    aucun PostgreSQL, serveur d'e-mail, Redis, clé d'envoi ni hôte autorisé hérités du poste, tâches Celery en mémoire."""
    env = {cle: os.environ[cle] for cle in VARIABLES_CONSERVEES if cle in os.environ}
    return {**env, "MATRIX_SQLITE_PATH": str(base), "DJANGO_DEBUG": "1", "DJANGO_SETTINGS_MODULE": "matrix.settings",
            "MATRIX_ENV_FILE": str(base.parent / "aucun.env"), "MATRIX_MEDIA_ROOT": str(base.parent / "media"),
            "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
            # Tâches Celery gardées dans le processus : rien n'est envoyé à un Redis du poste, même local.
            "CELERY_BROKER_URL": "memory://", "CELERY_RESULT_BACKEND": "cache+memory://",
            "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend"}


def controler_connexion(base, env):
    """Interroge la configuration réellement chargée ; RefusError si elle ne vise pas exactement la base attendue."""
    sortie = subprocess.run([sys.executable, "-c", _CONTROLE], cwd=RACINE, env=env, capture_output=True, text=True)
    if sortie.returncode != 0:
        raise RefusError(f"contrôle de la connexion impossible : {sortie.stderr.strip()[-300:]}")
    reel = json.loads(sortie.stdout.strip().splitlines()[-1])
    if reel["vendeur"] != "sqlite" or Path(reel["nom"]).resolve() != base:
        raise RefusError(f"la connexion visée ({reel['vendeur']} : {reel['nom']}) n'est pas la base de démonstration {base}")
    if "fichier" in reel and Path(reel["fichier"]).resolve() != base:
        raise RefusError(f"la connexion ouverte ({reel['fichier']}) n'est pas la base de démonstration {base}")
    verifier_isolement(reel)
    if Path(reel["media"]).resolve() != (base.parent / "media").resolve():
        raise RefusError(f"les fichiers téléversés iraient dans {reel['media']} et non dans le dossier de démonstration")


def verifier_isolement(reel):
    """RefusError si la configuration chargée pourrait joindre un service extérieur ou accepter un hôte distant."""
    if "locmem" not in reel["courriel"] or reel["serveur_courriel"] or reel["push"]:
        raise RefusError("envoi d'e-mails ou de notifications réels possible : refus")
    if reel["courtier"].split() != ["memory://", "cache+memory://"]:
        raise RefusError("le courtier de tâches n'est pas isolé en mémoire (un Redis du poste pourrait recevoir des tâches) : refus")
    if not reel["hotes"] or not set(reel["hotes"]) <= HOTES_LOCAUX:
        raise RefusError(f"hôtes autorisés non locaux {reel['hotes']} : refus")


def preparer(base, reinitialiser=False, verifier_seulement=False, dossier_autorise=DOSSIER_DEMO):
    base = verifier_chemin(base, dossier_autorise, reinitialiser, lecture_seule=verifier_seulement)
    env = environnement_demo(base)
    controler_connexion(base, env)
    if verifier_seulement:
        return base
    base.parent.mkdir(parents=True, exist_ok=True)
    if base.exists():
        base.unlink()
    marqueur(base).touch()
    for commande in ("migrate", "seed_demo"):
        subprocess.run([sys.executable, "manage.py", commande], cwd=RACINE, env=env, check=True)
    return base


def servir(base, port=PORT_PAR_DEFAUT, dossier_autorise=DOSSIER_DEMO, lancer=subprocess.run):
    """Lance le serveur de démonstration avec le même environnement isolé que la préparation, sur 127.0.0.1 seulement."""
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise RefusError("port invalide (1024 à 65535)")
    base = verifier_chemin(base, dossier_autorise, lecture_seule=True)
    if not base.exists() or not marqueur(base).exists():
        raise RefusError("base de démonstration absente ou non préparée par ce script : lancez d'abord la préparation")
    env = environnement_demo(base)
    controler_connexion(base, env)
    lancer([sys.executable, "manage.py", "runserver", f"{HOTE}:{port}", "--noreload"], cwd=RACINE, env=env)
    return base


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--base", default=str(DOSSIER_DEMO / "db.sqlite3"))
    analyseur.add_argument("--reinitialiser", action="store_true", help="repart d'une base vide (entre deux participants)")
    mode = analyseur.add_mutually_exclusive_group()
    mode.add_argument("--verifier", action="store_true", help="contrôle sans rien écrire que la configuration vise bien la base de démonstration")
    mode.add_argument("--servir", action="store_true", help=f"lance le serveur de démonstration sur {HOTE} (Ctrl+C pour arrêter)")
    analyseur.add_argument("--port", type=int, default=PORT_PAR_DEFAUT, help="port local du serveur (avec --servir)")
    args = analyseur.parse_args()
    if args.servir and args.reinitialiser:
        analyseur.error("--servir ne se combine pas avec --reinitialiser")
    try:
        if args.servir:
            print(f"Démonstration sur http://{HOTE}:{args.port}/ (cette machine seulement). Arrêt : Ctrl+C.")
            servir(args.base, args.port)
            return
        base = preparer(args.base, args.reinitialiser, args.verifier)
    except RefusError as erreur:
        sys.exit(f"Refus : {erreur}")
    if args.verifier:
        print(f"Contrôle réussi : la connexion vise bien {base} (SQLite).")
        return
    print(f"\nBase prête : {base}\nPour lancer la démonstration (cette machine seulement) :")
    print("  python scripts/preparer_instance_test.py --servir")
    print("Mot de passe fictif de tous les comptes : « pass ». Ne jamais exposer cette instance sur un réseau.")
    for compte, role in COMPTES:
        print(f"  {compte:16} {role}")


if __name__ == "__main__":
    main()
