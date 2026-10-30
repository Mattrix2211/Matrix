"""Prépare une instance de démonstration isolée pour les tests avec des marins.

Base SQLite séparée, données entièrement fictives (seed_demo), aucune donnée opérationnelle.
À n'utiliser que sur un poste local ou un environnement isolé : mots de passe fictifs et DEBUG actif,
jamais sur un réseau opérationnel ou exposé.

Usage : python scripts/preparer_instance_test.py [--base chemin] [--reinitialiser] [--verifier]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DEMO = RACINE / "instance_test_marins"
MARQUEUR = ".instance_demo_matrix"  # écrit à la création : seul un dossier ainsi marqué peut être réinitialisé
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
resultat = {'vendeur': connection.vendor, 'nom': str(reglages['NAME'])}
if os.path.exists(resultat['nom']):
    connection.ensure_connection()
    resultat['fichier'] = connection.cursor().execute('PRAGMA database_list').fetchall()[0][2]
print(json.dumps(resultat))
"""


class RefusError(Exception):
    pass


def verifier_chemin(base, dossier_autorise, reinitialiser=False):
    """Chemin de base validé et résolu, ou RefusError. Seul un fichier .sqlite3 situé directement dans le dossier
    de démonstration est admis ; un fichier existant doit y avoir été créé par ce script (marqueur) pour être supprimé."""
    base = Path(base)
    if base.is_symlink() or dossier_autorise.is_symlink():
        raise RefusError("lien symbolique refusé")
    base = base.resolve()
    dossier = dossier_autorise.resolve()
    if base.suffix != ".sqlite3" or base.parent != dossier:
        raise RefusError(f"la base doit être un fichier .sqlite3 placé directement dans {dossier}")
    if base == (RACINE / "db.sqlite3").resolve():
        raise RefusError("cette base est celle de développement")
    if base.exists():
        if base.is_dir():
            raise RefusError("le chemin est un dossier")
        if not reinitialiser:
            raise RefusError(f"{base} existe déjà : utilisez --reinitialiser pour repartir de zéro")
        if not (dossier / MARQUEUR).exists():
            raise RefusError("fichier existant non créé par ce script : suppression refusée")
    return base


def environnement_demo(base):
    """Environnement du processus fils : base SQLite explicite, .env du poste ignoré, aucun PostgreSQL ni envoi réel."""
    env = {**os.environ, "MATRIX_SQLITE_PATH": str(base), "DJANGO_DEBUG": "1",
           "MATRIX_ENV_FILE": str(base.parent / "aucun.env"),
           "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
    for variable in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_PORT", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"):
        env.pop(variable, None)
    return env


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


def preparer(base, reinitialiser=False, verifier_seulement=False, dossier_autorise=DOSSIER_DEMO):
    base = verifier_chemin(base, dossier_autorise, reinitialiser)
    env = environnement_demo(base)
    controler_connexion(base, env)
    if verifier_seulement:
        return base
    base.parent.mkdir(parents=True, exist_ok=True)
    (base.parent / MARQUEUR).touch()
    if base.exists():
        base.unlink()
    for commande in ("migrate", "seed_demo"):
        subprocess.run([sys.executable, "manage.py", commande], cwd=RACINE, env=env, check=True)
    return base


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--base", default=str(DOSSIER_DEMO / "db.sqlite3"))
    analyseur.add_argument("--reinitialiser", action="store_true", help="repart d'une base vide (entre deux participants)")
    analyseur.add_argument("--verifier", action="store_true", help="contrôle sans rien écrire que la configuration vise bien la base de démonstration")
    args = analyseur.parse_args()
    try:
        base = preparer(args.base, args.reinitialiser, args.verifier)
    except RefusError as erreur:
        sys.exit(f"Refus : {erreur}")
    if args.verifier:
        print(f"Contrôle réussi : la connexion vise bien {base} (SQLite).")
        return
    print(f"\nBase prête : {base}\nLancement (local uniquement) :")
    print(f"  MATRIX_SQLITE_PATH={base} MATRIX_ENV_FILE={base.parent / 'aucun.env'} DJANGO_DEBUG=1 python manage.py runserver 127.0.0.1:8800")
    print("Mot de passe fictif de tous les comptes : « pass ». Ne jamais exposer cette instance sur un réseau.")
    for compte, role in COMPTES:
        print(f"  {compte:16} {role}")


if __name__ == "__main__":
    main()
