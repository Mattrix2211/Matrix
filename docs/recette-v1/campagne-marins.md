# Procédure du passage B : campagne de l'équipage de testeurs

À exécuter dans une session Claude Code qui charge le serveur MCP `playwright` déclaré dans `.mcp.json` (approuvé par `enabledMcpjsonServers`). Une session qui n'expose pas les outils `mcp__playwright__*` ne peut **pas** mener cette campagne : ne pas la simuler.

## Isolation

- Les agents `marin-*` n'ont **que** les outils du navigateur (navigation, instantané de page, clic, saisie, formulaire, sélection, touche, attente, retour, capture, onglets, fermeture). Aucun `Read`, `Grep`, `Bash`, Notion, `browser_evaluate`, `browser_run_code_unsafe`, requêtes réseau ni dépôt de fichier.
- Le navigateur n'accepte que l'origine `http://127.0.0.1:8000` (toute autre origine est bloquée : `net::ERR_BLOCKED_BY_CLIENT`), sans service worker, avec un profil en mémoire.
- Un seul navigateur est partagé par la session : les marins passent **l'un après l'autre**. Fermer le navigateur (`browser_close`) entre deux marins pour effacer cookies et session.
- Le coordinateur ne transmet jamais `criteres-coordinateur.md`, le code, les menus ni les boutons.

## Préparation de la base (coordinateur)

```bash
git rev-parse HEAD                       # noter le SHA testé
export DJANGO_DEBUG=1
rm -f db.sqlite3 && python manage.py migrate && python manage.py seed_demo && python manage.py seed_recette
python manage.py runserver 127.0.0.1:8000 --noreload &
```

Remplacer SQLite par PostgreSQL (`scripts/recette/postgres_jetable.sh start`, variables `DB_*`) pour la contre-recette après correction d'ANO-001.

## Déroulement

1. Pour chaque mission de `missions-aveugle.md`, dans l'ordre de priorité (P1 d'abord) : relancer la base si la mission écrit des données déjà utilisées par une autre, `browser_close`, puis lancer l'agent marin avec **uniquement** : le persona, l'adresse `http://127.0.0.1:8000/`, le compte et le mot de passe (un vrai marin les possède), le texte exact de la mission, et la consigne de rendre un compte rendu au format « marin » de `protocole-comptes-rendus.md`.
2. Enregistrer chaque compte rendu tel quel dans `rapports/AAAA-MM-JJ-B-<mission>-<persona>.md`.
3. Lancer `observateur-ux` sur l'ensemble, enregistrer sa consolidation.
4. Contrôle : `git status --short` ne montre aucune modification de code (sinon, invalider).
5. Noter pour chaque mission : exécutée ou non, réussie ou non, avec la preuve (compte rendu, capture). Aucun marin non lancé n'est déclaré testé.
