#!/bin/bash
# Hook PreToolUse — contrôle léger à chaque "git commit", suite complète à la demande.
# La suite complète est longue : elle ne tourne qu'une fois en fin de chantier, en préfixant
# la commande de commit par MATRIX_SUITE_COMPLETE=1 (ex. : MATRIX_SUITE_COMPLETE=1 git commit ...).

input=$(cat)
command=$(echo "$input" | python -c "import json,sys; print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))" 2>/dev/null)

if [[ "$command" == *"git commit"* ]]; then
    cd "$CLAUDE_PROJECT_DIR" || exit 1
    if [[ "$command" == *"MATRIX_SUITE_COMPLETE=1"* ]]; then
        if ! python manage.py test > /tmp/matrix_test_output.log 2>&1; then
            echo "❌ Commit bloqué : les tests Django échouent." >&2
            echo "Voir le détail : /tmp/matrix_test_output.log" >&2
            exit 2
        fi
    elif ! python manage.py check > /tmp/matrix_check_output.log 2>&1; then
        echo "❌ Commit bloqué : python manage.py check signale une erreur." >&2
        echo "Voir le détail : /tmp/matrix_check_output.log" >&2
        exit 2
    fi
fi

exit 0
