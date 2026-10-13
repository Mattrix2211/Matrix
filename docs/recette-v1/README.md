# Recette V1 de Matrix : organisation et procédure

Campagne de qualification de la V1 avant présentation à la Marine. **Priorité : la qualité, pas de nouvelle fonctionnalité.** Les fonctions Notion « À faire plus tard » ne sont ni testées comme exigences ni comptées comme échecs. Ce dossier complète `docs/RECETTE.md` (contrôles visuels) et `docs/DEMO.md` (parcours de démonstration) sans les remplacer.

Sources de vérité : Notion fait foi pour les décisions métier (Équipage de testeurs, Organigramme et rôles, Décisions et gouvernance) ; le code et les tests établissent ce qui est réellement développé. Tout écart est consigné dans `personas-comptes.md`.

## Référence testée

| Élément | Valeur |
|---|---|
| PR de référence | #8, **fusionnée** dans `main` le 2026-10-13 12:17 UTC (commit de fusion) |
| SHA de référence | `59dd2f2bfca412ae97f5f006406fecfc7b0fd359` |
| Base de test | SQLite jetable (`db.sqlite3`, ignorée par git) + `seed_demo`, `DJANGO_DEBUG=1` |
| Aucune fusion, aucun déploiement, aucune écriture au backlog Notion sans accord | |

## Deux équipes indépendantes

### Équipe A : agents techniques (peuvent lire le code, ne le modifient pas)

| Agent | Rôle | Outils |
|---|---|---|
| `qa-securite` | RBAC, périmètres, isolation bâtiment/équipage, tâches privées, pièces jointes, sessions, transitions critiques | Read, Grep, Glob, Bash |
| `qa-integration` | Tests Django, PostgreSQL et migrations, cohérence entre modules, traçabilité, transitions, notifications, concurrence, dégradé, non-régression | Read, Grep, Glob, Bash |
| `qa-ergonomie` | Navigation, 1366×768, clavier/contrastes, impression, sombre, mobile, design system, performance | Read, Grep, Glob, Bash |

Aucun n'a `Write`, `Edit` ni accès Notion : ils rendent un rapport que le coordinateur enregistre. `Bash` reste un outil puissant : l'interdiction de modifier le dépôt est une consigne, vérifiée après coup par `git status` (voir procédure, étape 5).

### Équipe B : équipage de testeurs (utilisateurs, jamais développeurs)

| Agent | Persona | Outils |
|---|---|---|
| `marin-lucas` | MOT Lucas Morel, jeune équipier | navigateur uniquement |
| `marin-julien` | QM1 Julien Martin, équipier expérimenté | navigateur uniquement |
| `marin-claire` | PM Claire Bernard, chef de section | navigateur uniquement |
| `marin-antoine` | LV Antoine Le Goff, chef de service | navigateur uniquement |
| `marin-complementaire` | Rôle complémentaire, profil injecté par mission | navigateur uniquement |
| `observateur-ux` | Consolide les comptes rendus, ne teste pas | Read, Grep, Glob (rapports) |

**Isolation réelle** : les marins n'ont ni `Read`, ni `Grep`, ni `Bash`, ni Notion, ni `browser_evaluate`/requêtes réseau. Leur liste d'outils se limite aux outils du serveur MCP `playwright` (navigation, clic, saisie). Ils ne peuvent donc matériellement ni lire le code, ni les tests, ni les critères de réussite, ni appeler une API.

**Prérequis non satisfait dans cette session** : aucun serveur MCP navigateur n'est déclaré (`.mcp.json` absent, aucun outil `mcp__playwright__*` disponible). Sans lui, un marin n'a aucun outil, et **aucun test utilisateur réel n'est possible**. Ne jamais compenser en lui donnant `Bash` : cela détruirait l'isolation. Voir `rapports/passage-A-preparation.md` pour l'état exact et les options.

Les rôles complémentaires ne sont **pas** des agents permanents : `marin-complementaire` est lancé à la demande avec le profil copié de la page Notion « Équipage de testeurs » et le compte réel de `personas-comptes.md`.

Les agents `po`, `dev`, `relecteur` sont inchangés.

## Campagne en trois passages

| Passage | Contenu | Modification de Matrix |
|---|---|---|
| **A** | Équipe A : suite de tests, PostgreSQL/migrations, sécurité et permissions, ergonomie experte | Interdite |
| **B** | Équipe B : missions à l'aveugle (`missions-aveugle.md`), puis `observateur-ux` | Interdite |
| **C** | Consolidation, arbitrage du Product Owner humain, corrections validées via po → dev → relecteur, contre-recette | Autorisée après arbitrage |

Priorités : d'abord les parcours de démonstration (P1 dans `missions-aveugle.md`), puis les scénarios à risque. Pas de campagne exhaustive.

## Procédure reproductible

1. **Préparer** (depuis la racine du dépôt, venv avec `requirements.txt`) :
   ```bash
   export DJANGO_DEBUG=1
   git rev-parse HEAD            # doit être 59dd2f2 ou le SHA de contre-recette noté dans le rapport
   python manage.py check && python manage.py makemigrations --check --dry-run
   rm -f db.sqlite3 && python manage.py migrate && python manage.py seed_demo
   python manage.py seed_demo    # relance : aucun doublon attendu
   ```
2. **Passage A** : lancer chaque agent de l'équipe A avec : le SHA, l'identifiant de rapport (`A-securite`, `A-integration`, `A-ergonomie`), la liste des lignes de `couverture.md` à couvrir. Enregistrer chaque rapport dans `rapports/` (`AAAA-MM-JJ-<id>.md`).
3. **Passage B** : démarrer `python manage.py runserver 127.0.0.1:8000` sur une base fraîche (étape 1), navigateur à **1366×768**. Pour chaque mission, lancer l'agent marin avec **uniquement** : son nom de persona, le compte, l'adresse, le contexte et le texte de la mission (copié de `missions-aveugle.md`). Ne jamais transmettre `criteres-coordinateur.md`, ni de menu, page ou bouton. Rejouer `seed_demo` sur base fraîche entre deux marins dont les missions modifient les mêmes données.
4. **Observateur** : lancer `observateur-ux` sur les comptes rendus du passage B.
5. **Garde-fous** : après chaque agent, `git status --short` ne doit montrer aucun fichier de code modifié ; sinon la campagne est invalidée pour ce passage et le coordinateur le consigne.
6. **Consolider** : classer P0 à P3, présenter au Product Owner humain, attendre l'arbitrage avant toute tâche Notion ou correction.

## Priorités des anomalies

P0 : sécurité ou perte de données · P1 : empêche un parcours V1 essentiel · P2 : friction UX importante ou défaut non bloquant · P3 : confort ou cosmétique. P0 et P1 peuvent bloquer la présentation. Une idée supplémentaire n'est pas un défaut V1.

## Statuts de résultat (obligatoires dans tous les rapports)

**Prévu · Exécuté · Réussi · Échoué · Non testé · Impossible à vérifier avec les outils disponibles.** Une affirmation « déclaré dans la PR » n'est pas « exécuté ». Aucun « réussi » sans preuve (commande et sortie, capture, compte rendu de marin).

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `personas-comptes.md` | Personas ↔ comptes de démo ↔ permissions, écarts Notion/fixtures/code |
| `couverture.md` | Matrice de couverture fonctionnelle et technique avec statuts |
| `missions-aveugle.md` | Missions en langage métier (seul fichier dont des extraits sont donnés aux marins) |
| `criteres-coordinateur.md` | Critères de réussite et frontières attendues : **jamais donné aux marins** |
| `protocole-comptes-rendus.md` | Format commun de compte rendu et de preuves |
| `notation-ergonomie.md` | Méthode de notation de la praticité |
| `rapports/` | Rapports de passage, un fichier par exécution |
