"""Prépare une instance de démonstration isolée pour les tests avec des marins.

Base SQLite séparée, données entièrement fictives (seed_demo), aucune donnée opérationnelle.
Usage : python scripts/preparer_instance_test.py [--base chemin] [--reinitialiser]
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
COMPTES = (
    ("equipier_a", "Marin, équipage A : journée chargée (10 actions)"),
    ("equipier_a2", "Marin, équipage A : peu d'actions, dont une tâche en retard"),
    ("equipier_nor", "Marin, frégate Normandie : aucune action (liste vide)"),
    ("chef_secteur_a", "Chef de secteur, équipage A : supervision et équipe"),
    ("chef_secteur_b", "Chef de secteur, équipage B à terre : accès limité"),
)


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--base", default=str(RACINE / "instance_test_marins" / "db.sqlite3"))
    analyseur.add_argument("--reinitialiser", action="store_true", help="repart d'une base vide (entre deux participants)")
    args = analyseur.parse_args()
    base = Path(args.base).resolve()
    if base == (RACINE / "db.sqlite3").resolve():
        sys.exit("Refus : cette base est celle de développement. Choisissez un autre chemin.")
    if base.exists() and not args.reinitialiser:
        sys.exit(f"{base} existe déjà : utilisez --reinitialiser pour repartir de zéro.")
    base.parent.mkdir(parents=True, exist_ok=True)
    if base.exists():
        base.unlink()
    env = {**os.environ, "MATRIX_SQLITE_PATH": str(base), "DJANGO_DEBUG": "1"}
    env.pop("DB_HOST", None)
    for commande in ("migrate", "seed_demo"):
        subprocess.run([sys.executable, "manage.py", commande], cwd=RACINE, env=env, check=True)
    print(f"\nBase prête : {base}\nLancement : MATRIX_SQLITE_PATH={base} DJANGO_DEBUG=1 python manage.py runserver 8800")
    print("Mot de passe de tous les comptes de démonstration : « pass ».")
    for compte, role in COMPTES:
        print(f"  {compte:16} {role}")


if __name__ == "__main__":
    main()
