"""
Garde-fous de démarrage exécutés par le système de checks Django (registre
"django.core.checks"), en complément des hooks Git de pré-commit.

1) verifier_migrations_en_attente : complète le hook Git
   verifier-migrations-appliquees-avant-commit.sh, qui protège uniquement le
   poste de la personne qui committe. Il ne protège pas un autre marin qui
   récupère le code à jour (git pull) sur son propre poste, avec sa propre
   base de développement locale, et lance directement
   "python manage.py runserver" sans avoir relancé "python manage.py
   migrate" au préalable.

   Rattrape l'incident du 06/09/2026 : la page /calendar/ a planté en pleine
   campagne de tests manuels avec "OperationalError: no such column:
   calendar_app_personalevent.ends_at" car une migration n'avait jamais été
   appliquée à la base de développement réelle.

2) verifier_debug_desactive_hors_developpement_local : avertit si DEBUG=True
   est actif en dehors du serveur de développement local, pour qu'un
   DJANGO_DEBUG=1 oublié en production soit visible dès le démarrage d'une
   commande "manage.py" plutôt que découvert par un incident.
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


@register()
def verifier_debug_desactive_hors_developpement_local(app_configs, **kwargs):
    """Avertit si DEBUG=True est actif alors que la commande lancée n'est
    pas le serveur de développement local ("runserver").

    Objectif : un DJANGO_DEBUG=1 oublié en production (ou dans tout script de
    déploiement qui invoque une commande "manage.py", par exemple "migrate")
    doit être visible dès le démarrage plutôt que découvert par un incident —
    DEBUG=True expose des informations sensibles (traces d'erreur détaillées,
    requêtes SQL, variables de contexte) aux utilisateurs.
    """
    from django.conf import settings

    if "runserver" in sys.argv:
        return []

    if not settings.DEBUG:
        return []

    message = (
        "DEBUG est activé (DJANGO_DEBUG=1) alors que ce n'est pas le serveur de "
        "développement local qui est lancé. En production, DJANGO_DEBUG doit "
        "valoir 0 : DEBUG=True expose des informations sensibles (traces "
        "d'erreur détaillées, requêtes SQL) aux utilisateurs."
    )
    return [Warning(message, id="matrix.W002")]
