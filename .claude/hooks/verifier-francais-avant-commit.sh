#!/bin/bash
# Hook PreToolUse — bloque un "git commit" si une ligne ajoutée contient du texte
# probablement anglais là où le français est exigé.
# Règle n°1 de CLAUDE.md : tout ce qui est lu par un humain est en français (interface,
# commentaires, docstrings, documentation). Seul le code lui-même (identifiants, mots-clés,
# noms de verbes HTTP...) peut être en anglais.
#
# Le contrôle est heuristique (mots anglais courants) et ne porte que sur les lignes
# ajoutées : voir verifier_francais.py pour le détail des zones examinées.

input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // empty')

if [[ "$command" == *"git commit"* ]]; then
    cd "$CLAUDE_PROJECT_DIR" || exit 1

    # Avec -a / -am / --all, l'index est encore vide au moment du contrôle : on compare
    # alors l'arbre de travail à HEAD (option --tout du script).
    option=""
    if [[ "$command" =~ git[[:space:]]+commit([[:space:]]+[^|\&\;]*)?[[:space:]]-[a-zA-Z]*a || "$command" == *"--all"* ]]; then
        option="--tout"
    fi

    if ! trouve=$(python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/verifier_francais.py" $option 2>&1 >/dev/null); then
        echo "⚠️  Commit bloqué : texte probablement anglais (règle CLAUDE.md : commentaires, documentation et interface en français ; seul le code peut être en anglais)." >&2
        echo "$trouve" >&2
        echo "S'il s'agit d'un faux positif, reformule le texte en français ou signale le cas à l'utilisateur : le hook ne se contourne pas avec --no-verify." >&2
        exit 2
    fi
fi

exit 0
