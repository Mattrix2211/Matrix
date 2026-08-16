#!/bin/bash
# Hook PreToolUse — bloque un "git commit" si les tests Django échouent.
# Applique concrètement la règle QA déjà écrite dans CLAUDE.md, au lieu de dépendre
# uniquement de la discipline de l'agent.

input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // empty')

if [[ "$command" == *"git commit"* ]]; then
    cd "$CLAUDE_PROJECT_DIR" || exit 1
    if ! python manage.py test > /tmp/matrix_test_output.log 2>&1; then
        echo "❌ Commit bloqué : les tests Django échouent." >&2
        echo "Voir le détail : /tmp/matrix_test_output.log" >&2
        exit 2
    fi
fi

exit 0
