#!/usr/bin/env bash
# Rejoue les sondes côté serveur sur une base temporaire de démonstration et compare aux résultats attendus.
# Usage : PYTHON=/chemin/python docs/audit-general-v11/sondes/rejouer_tout.sh [dossier_de_travail]
# Aucune base réelle n'est touchée : la base est créée dans le dossier de travail, hors dépôt.
set -u
RACINE="$(cd "$(dirname "$0")/../../.." && pwd)"
PYTHON="${PYTHON:-python}"
TRAVAIL="${1:-$(mktemp -d)}"
mkdir -p "$TRAVAIL/resultats"
export DJANGO_DEBUG=1 DJANGO_SECRET_KEY=audit-temporaire DJANGO_ALLOWED_HOSTS=testserver,localhost MATRIX_SQLITE_PATH="$TRAVAIL/audit.sqlite3"
rm -f "$MATRIX_SQLITE_PATH"
cd "$RACINE" || exit 2
echo "[base] migration et pipeline complet de démonstration dans $TRAVAIL"
"$PYTHON" manage.py migrate -v0 >/dev/null 2>&1 || { echo "échec de migrate"; exit 2; }
for g in seed_demo seed_demo_mer_quai seed_demo_dense seed_demo_metier; do
  "$PYTHON" manage.py "$g" >/dev/null 2>&1 || { echo "échec de $g"; exit 2; }
done
ok=0; ko=0
for s in $("$PYTHON" -c "import json;print(' '.join(json.load(open('docs/audit-general-v11/sondes/attendus.json'))))"); do
  [ "$s" = "prod_proxy.py" ] && continue
  sortie="$TRAVAIL/resultats/$s.txt"
  if [ ! -f "$RACINE/docs/audit-general-v11/sondes/$s" ]; then echo "[KO ] $s : script absent"; ko=$((ko+1)); continue; fi
  (cd "$TRAVAIL" && "$PYTHON" "$RACINE/manage.py" shell < "$RACINE/docs/audit-general-v11/sondes/$s" > "$sortie" 2>&1)
  manque=$("$PYTHON" - "$s" "$sortie" <<'PY'
import json,sys
attendus=json.load(open("docs/audit-general-v11/sondes/attendus.json"))[sys.argv[1]]
texte=open(sys.argv[2],encoding="utf-8",errors="ignore").read()
print(" ; ".join(a for a in attendus if a not in texte))
PY
) || manque="vérification impossible"
  if [ -z "$manque" ]; then echo "[OK ] $s"; ok=$((ok+1)); else echo "[KO ] $s : attendu non trouvé : $manque"; ko=$((ko+1)); fi
done
echo "[bilan] $ok sondes conformes, $ko écarts (sorties dans $TRAVAIL/resultats)"
[ "$ko" -eq 0 ]
