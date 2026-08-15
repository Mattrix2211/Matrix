#!/bin/bash
# Hook PostToolUse — signale (sans bloquer) une migration Django qui ajoute un champ
# sans valeur par defaut visible, risque de retrocompatibilite sur les enregistrements
# existants. Informatif uniquement : PostToolUse ne peut pas bloquer l'action deja faite,
# mais alerte immediatement le Dev/Tech Lead avant que ca n'aille plus loin.

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

if [[ "$file_path" == *"/migrations/"*.py ]]; then
    if grep -q "AddField" "$file_path" 2>/dev/null && ! grep -q "default=" "$file_path" 2>/dev/null; then
        echo "Migration potentiellement non retrocompatible : $file_path" >&2
        echo "Un AddField sans 'default=' visible peut echouer sur les enregistrements existants." >&2
        echo "Verifier avant de committer (voir section Priorite 1 du document de spec BordOps)." >&2
    fi
fi

exit 0
