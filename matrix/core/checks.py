"""
Garde-fou complémentaire au hook Git verifier-migrations-appliquees-avant-commit.sh.

Le hook Git protège uniquement le poste de la personne qui committe. Il ne
protège pas un autre marin qui récupère le code à jour (git pull) sur son
propre poste, avec sa propre base de développement locale, et lance
directement "python manage.py runserver" sans avoir relancé
"python manage.py migrate" au préalable.

Rattrape l'incident du 06/09/2026 : la page /calendar/ a planté en pleine
campagne de tests manuels avec "OperationalError: no such column:
calendar_app_personalevent.ends_at" car une migration n'avait jamais été
appliquée à la base de développement réelle.
"""
import sys

from django.core.checks import Warning, register


@register()
def verifier_migrations_en_attente(app_configs, **kwargs):
    """Avertit au démarrage de "runserver" si des migrations Django restent
    à appliquer sur la base de développement réelle."""
    if "runserver" not in sys.argv:
        return []

    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor

    try:
        executor = MigrationExecutor(connections["default"])
    except Exception:
        # Base injoignable ou pas encore créée : une erreur plus explicite
        # remontera de toute façon au démarrage du serveur, inutile de la
        # doubler ici.
        return []

    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if not plan:
        return []

    en_attente = ", ".join(f"{migration.app_label}.{migration.name}" for migration, _ in plan)
    message = (
        f"Migrations Django en attente sur la base de développement réelle : {en_attente}. "
        "Lancer 'python manage.py migrate' avant de continuer, sinon certaines pages "
        "vont planter (colonne ou table manquante)."
    )
    return [Warning(message, id="matrix.W001")]
