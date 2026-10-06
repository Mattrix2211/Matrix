# Référence technique Matrix

Complément de `CLAUDE.md`. **Ne lis que la section utile à ta tâche**, pas tout le fichier.

## 1. Direction artistique

Source de vérité : `design/DESIGN_SYSTEM.md` (submodule), à lire avant tout template ou décision visuelle. Règles UX/UI : `docs/UX.md`.

- Usage principal : PC fixes partagés du bord, clavier et souris, résolution de référence 1366×768. Tablette et scan QR = options, aucun parcours n'en dépend. Maintenance : fiche papier imprimée, puis compte rendu saisi sur PC (grille façon tableur pour les séries).
- Mode clair par défaut + mode sombre activé par chaque marin (dérogation validée, `docs/UX.md` §17). Toutes les couleurs passent par des variables CSS.
- Typo : `Space Grotesk` (titres, cards, nav), `Inter` (texte), `JetBrains Mono` (données, dates, codes). Jamais `Syncopate`.
- Pas d'`--ember`. Vert unique `--green-tech` (jamais `--green-sport`). Accent unique `--signal` (#00B4D8), une seule action principale par vue.
- Logo : `design/assets/IMG_5292.PNG` + pictogramme ancre en bas à droite.
- Espacement base 4 px ; radius, ombres, composants : `design/DESIGN_SYSTEM.md` §4 à §8.
- Polices et Bootstrap Icons auto-hébergées dans `static/` (jamais le CDN Google Fonts). Aucun emoji dans l'interface.

## 2. Organisation et rôles (résumé — la page Notion « Organigramme et rôles » fait foi)

- **À bord** (configurable par navire) : Commandant → Commandant en second (même vision globale) → commandants adjoints COMAEQ (équipage), COMOPS (opérations), COMANAV (navire), COMAVIA (seulement avec capacité aviation) → chefs de service → chefs de secteur → chefs de section → opérateurs. Chaque service dépend d'un commandant adjoint. Afficher le sigle, jamais « chef de groupement ».
- **Double équipage** (FREMM, PSP, BSAM) : deux équipages en miroir sur un même bâtiment ; l'équipage à terre garde un accès en lecture seule. Le bâtiment porte installations, matériel, fiches, historique, stock ; l'équipage porte personnes, quarts, services, assignations, espace personnel.
- **À terre** : ALFAN → division Exploitation → spécialités (Mécan, Sécu, Élec, SIC, Artilleur), chacune avec un responsable de spécialité (`accounts.ResponsableSpecialite`), encadré par un chef du responsable de spécialité. Le SSF suit une classe ou une liste de bâtiments et peut agir (commenter un ticket…).
- **Codes techniques** : `MASTER_ADMIN → ADMIN_NAVIRE → COMMANDANT → ETAT_MAJOR → CHEF_SERVICE → CHEF_SECTEUR → CHEF_SECTION → EQUIPIER`.

## 3. Équipements

- **Installations** (`assets.Installation`) : équipements fixes propres au bâtiment. Mesures : heures de marche, vibrations (A/B/C), isolement (Ohms), détection de dérive (régression linéaire) avant seuil. Champ `critique` → signature par mot de passe sur les transitions sensibles.
- **Matériel mobile** (`assets.Asset`) : extincteurs, EPI, multimètres, élingues ; toujours rattaché à un navire ; fiche individuelle (n° de série, contrôle, péremption).
- Les deux ont une hiérarchie parent/enfant protégée contre les cycles.
- Décisions en cadrage (tâches Notion « [CADRAGE @po] … ») : catalogue de matériel flotte géré à terre ; une fiche de maintenance par gamme (checklist et/ou relevés), fiches matériel flotte publiées par le responsable de spécialité, fiches installation validées par chef de service puis commandant adjoint ; comptes rendus générés depuis les fiches, notifiés au chef de secteur.

## 4. Les 13 apps Django

| App | Rôle |
|-----|------|
| `accounts` | Utilisateurs, profils, rôles, grades, spécialités, responsables de spécialité |
| `org` | Unités typées → Service → Secteur → Section ; classes de navire, seuils de rôle, modules activables |
| `assets` | Installations + matériel mobile, checklists, documents, mesures, dérive, plan du navire |
| `maintenance` | Plans préventifs, occurrences, exécutions, checklists, signature sur transitions critiques |
| `logistics` | Tickets correctifs, anomalies, demandes de pièces, stock, REX |
| `training` | Formations, prérequis, arbre de compétences, référents, sessions, candidatures |
| `quarts` | Quarts, services et gardes, chef de liste, échanges, équité |
| `rondes` | Modèles de rondes, points de contrôle, exécutions |
| `threads` | Discussions attachées à n'importe quel objet |
| `notifications` | Alertes in-app + Web Push (niveau danger) |
| `dashboard` | Tableau de bord personnel et par périmètre |
| `calendar_app` | Calendrier central, vue globale et personnelle, export iCal |
| `reports` | Bilans instantané/période, PDF / CSV / Excel |

URLs : `/api/*` = DRF (`views.py`), `/` = templates (`web_views.py`).

## 5. Workflows clés

- **Maintenance préventive (Celery)** : `generate_occurrences` quotidien (90 jours d'avance), `compute_overdue` horaire. Cycle `PLANNED → ASSIGNED → IN_PROGRESS → WAITING_VALIDATION → DONE`.
- **Inspection → ticket** : occurrence du jour (« Aujourd'hui », fiche, ou QR en option) → checklist → `MaintenanceExecution` → si `NON_CONFORME`, création auto d'un `CorrectiveTicket`.
- **Ticket correctif** : `REPORTED → DIAGNOSED → WAITING_PARTS → IN_REPAIR → TESTING → RETURNED_TO_SERVICE → CLOSED`. Mot de passe sur `RETURNED_TO_SERVICE` si installation `critique` ; REX obligatoire à `CLOSED`.
- **Formations** : prérequis anti-cycle ; validation réservée aux référents de CETTE formation ou à COMMANDANT+ ; arbre de compétences 100 % CSS/HTML/SVG ; réservation self-service d'une place de session (distincte de la validation).

## 6. Hooks (`.claude/hooks/`)

- `verifier-tests-avant-commit.sh` : bloque `git commit` si `python manage.py test` échoue.
- `verifier-francais-avant-commit.sh` (logique dans `verifier_francais.py`) : bloque si une ligne **ajoutée** contient du texte probablement anglais dans une zone qui doit être en français (commentaires, docstrings, chaînes, texte des gabarits, fichiers `.md`) ; le code n'est jamais examiné, l'existant non plus ; contrôle aussi `commit -a`. En cas de faux positif : reformuler en français ou demander à l'utilisateur, ne jamais contourner.
- `verifier-migration-retrocompatible.sh` : alerte si une migration ajoute un champ sans valeur par défaut.
- `verifier-migrations-appliquees-avant-commit.sh` : bloque si des migrations ne sont pas appliquées à `db.sqlite3`. `matrix/core/checks.py` avertit aussi au `runserver`.

## 7. Phases (feuille de route Matrix 2.0, cahier des charges §42)

| Phase | Objectif |
|-------|----------|
| 0 — Assainissement | Sécurité, permissions, scoping, tests, audit, architecture |
| 1 — Socle | Organisation, utilisateurs, permissions, configuration, notifications, recherche, audit |
| 2 — Vie quotidienne | Mon espace, calendrier, tâches, quarts, services, chefs de liste, échanges |
| 3 — Communication | Discussions, annonces, conversations contextuelles |
| 4 — Opérationnel | Équipements, catalogue, fiches de maintenance, comptes rendus, anomalies, rondes, logistique |
| 5 — Connaissance | Documentation, formations, qualifications, RETEX |
| 6 — Pilotage | Tableaux de bord par niveau, indicateurs, rapports, vue SSF |
| 7 — Écosystème | Synchronisation bâtiment ↔ terre, API, interopérabilité, multi-bâtiments |

Contenu des phases UX : `docs/UX.md` §27. Les anciennes étiquettes (« Phase 1 - Fondation », « Phase 3 - Maintenance Préventive »…) ne restent que sur des tâches terminées.
