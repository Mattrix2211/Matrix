#!/bin/bash
# Hook PreToolUse — bloque un "git commit" si des migrations Django existent
# mais n'ont pas ete appliquees a la base de developpement locale (db.sqlite3).
#
# Distinct de verifier-migration-retrocompatible.sh : ce dernier verifie le
# SCHEMA d'une migration (retrocompatibilite d'un AddField), celui-ci verifie
# que les migrations ont bien ete APPLIQUEES a la vraie base de dev.
#
# Rattrape l'incident du 06/09/2026 : la migration 0002_personalevent_ends_at
# etait vue par la suite de tests automatises (base ephemere recreee a chaque
# "python manage.py test") mais n'avait jamais ete appliquee a db.sqlite3, la
# base persistante utilisee par "python manage.py runserver". Resultat : la
# page /calendar/ a plante en pleine campagne de tests manuels avec
# "OperationalError: no such column: calendar_app_personalevent.ends_at".

input=$(cat)
command=$(echo "$input" | python -c "import json,sys; print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))" 2>/dev/null)

if [[ "$command" == *"git commit"* ]]; then
    cd "$CLAUDE_PROJECT_DIR" || exit 1
    if ! python manage.py migrate --check > /tmp/matrix_migrate_check.log 2>&1; then
        echo "❌ Commit bloqué : des migrations Django ne sont pas appliquées à la base de développement locale (db.sqlite3)." >&2
        echo "Lancer 'python manage.py migrate' avant de committer, sinon la base réelle divergera du code déjà commité (voir incident du 06/09/2026 sur /calendar/)." >&2
        echo "Détail : /tmp/matrix_migrate_check.log" >&2
        exit 2
    fi
fi

exit 0
