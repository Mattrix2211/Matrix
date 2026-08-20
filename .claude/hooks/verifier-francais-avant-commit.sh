#!/bin/bash
# Hook PreToolUse — alerte (et bloque) si du texte visible potentiellement anglais
# est ajouté dans un template ou une vue. Best-effort : liste de mots suspects,
# pas une vérification linguistique complète, mais rattrape les oublis évidents.
# Applique la règle n°1 de CLAUDE.md : "100% français".

input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // empty')

if [[ "$command" == *"git commit"* ]]; then
    cd "$CLAUDE_PROJECT_DIR" || exit 1

    mots_suspects="\bSubmit\b|\bCancel\b|\bLoading\b|\bSave\b|\bDelete\b|\bError:|\bWarning:|\bSuccess\b|\bPlease\b|\bClick here\b"
    lignes_ajoutees=$(git diff --cached -- '*.html' '*.py' | grep -E '^\+' | grep -vE '^\+\+\+')
    # Exclut les faux positifs de code légitime, qui ne sont jamais du texte visible
    # par l'utilisateur : appel de méthode (ex. classeur.save(...), ticket.delete())
    # précédé d'un point, et classe CSS Bootstrap en kebab-case (ex. btn-outline-success,
    # text-danger) précédée d'un tiret. Le texte UI réel (labels, boutons, messages)
    # n'est jamais précédé de ces caractères, donc la détection sur celui-ci reste intacte.
    trouve=$(echo "$lignes_ajoutees" | grep -i -P "(?<![.\-])($mots_suspects)")

    if [[ -n "$trouve" ]]; then
        echo "⚠️  Commit bloqué : texte potentiellement anglais détecté (règle CLAUDE.md : 100% français)." >&2
        echo "$trouve" >&2
        echo "Si c'est un faux positif (ex: nom de variable technique), committer avec --no-verify n'est pas possible ici : corriger le texte visible avant de recommittez." >&2
        exit 2
    fi
fi

exit 0
