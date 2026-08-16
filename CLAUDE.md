# CLAUDE.md — Projet Matrix

Ce fichier est la référence absolue pour Claude Code. Lis-le intégralement à chaque session.

## Identité du projet

**Matrix** — application de gestion opérationnelle pour la **Marine Nationale française**.
Le package Django s'appelle `matrix`, le projet s'appelle **Matrix**.

## Stack technique

- Python 3.12+, Django 5, Django REST Framework
- Frontend : Django Templates + Bootstrap 5 + HTMX
- Base de données : SQLite (dev), PostgreSQL (prod)
- Tâches asynchrones : Celery + Redis
- Graphiques : Chart.js + FullCalendar

## Principes fondamentaux — NON NÉGOCIABLES

1. **100 % français** — tout ce que voit l'utilisateur : labels, boutons, messages, statuts, placeholders, tooltips, titres, commentaires dans le code
2. **Plus rapide qu'Excel** — si une action prend plus de clics que dans un tableau Excel, c'est un échec. Formulaires pré-remplis, actions en un clic, zéro jargon informatique
3. **Espace personnel par marin** — chaque marin voit SES tâches, SES formations, SES maintenances assignées
4. **Fonctionne hors-ligne** — le navire n'a pas toujours internet, aucune dépendance CDN critique

## Direction artistique

La DA de Matrix suit le **MK Design System** (submodule `design/`, source de vérité : `design/DESIGN_SYSTEM.md`). Lis ce fichier en entier avant toute décision visuelle ou tout template.

**Config Matrix / Naval** (voir tableau "Contextes par projet" du design system) :
- **Mode Light** — pas de dark mode ici (le light est réservé aux contextes naval/pro)
- Typo : `Space Grotesk` (titres de section, cards, nav) + `Inter` (corps de texte) + `JetBrains Mono` (données techniques, dates, codes, labels) — **jamais `Syncopate`** (réservé hero/sport)
- **Pas d'Ember** (`--ember` réservé au sport)
- Vert unique : `--green-tech` (statuts systèmes/validations navales) — jamais `--green-sport`
- Accent unique : `--signal` (#00B4D8), une seule action principale par vue
- Logo : `design/assets/IMG_5292.PNG` (requin marteau), pictogramme ancre en overlay bas-droite pour Matrix
- Espacement base 4px strict, radius/shadows/composants (cards, badges, progress bars) : voir `design/DESIGN_SYSTEM.md` §4 à §8

**Conflit avec le principe hors-ligne (à respecter) :** le design system référence les polices via Google Fonts CDN — **auto-héberger** `Space Grotesk`, `Inter` et `JetBrains Mono` dans `static/fonts/` plutôt que d'utiliser le lien CDN, conformément au principe fondamental n°4 (aucune dépendance CDN critique).

## Deux types d'équipements

- **Installations** : équipements fixes du navire (propulseurs, pompes, circuits électriques). Propres à chaque bâtiment. Modèle `Installation` dans l'app `assets`. Mesures techniques associées : heures de marche, vibrations (A/B/C), isolement (Ohms)
- **Matériel mobile** : équipements transverses (extincteurs, EPI, multimètres, élingues). Modèle `Asset` dans l'app `assets`. Suivi par catégorie avec fiche individuelle (numéro de série, date de contrôle, péremption)

## Architecture Django — 10 modules

| App | Rôle |
|-----|------|
| `accounts` | Utilisateurs, profils, rôles (Commandant → Équipier), grades, spécialités |
| `org` | Hiérarchie : Navire → Service → Secteur → Section |
| `assets` | Installations fixes + Matériel mobile, checklists, documents, mesures techniques |
| `maintenance` | Plans préventifs, occurrences, exécutions, checklists guidées |
| `logistics` | Tickets correctifs, demandes de pièces, retours d'expérience (REX) |
| `training` | Formations, sessions, qualifications, expiration, portabilité entre bâtiments |
| `threads` | Discussions génériques (attachées à n'importe quel objet) |
| `notifications` | Alertes in-app (maintenance en retard, formation expirée) |
| `dashboard` | Tableau de bord, graphiques Chart.js |
| `calendar_app` | Calendrier central (colonne vertébrale), vue globale + personnelle, alertes |

## Structure des URLs

- `/api/*` — API REST (DRF)
- `/` — Interface web (templates Django)
- Chaque app a `views.py` (API) et `web_views.py` (templates)

## Hiérarchie des rôles

`MASTER_ADMIN → ADMIN_NAVIRE → COMMANDANT → ETAT_MAJOR → CHEF_SERVICE → CHEF_SECTEUR → CHEF_SECTION → EQUIPIER`

Chaque rôle ne voit que ce qui le concerne. Les chefs gèrent leur périmètre. Les équipiers exécutent.

## Workflows clés

### Maintenance préventive (Celery)
- `generate_occurrences` quotidien : crée les occurrences 90 jours à l'avance
- `compute_overdue` horaire : marque les retards
- Cycle : `PLANNED → ASSIGNED → IN_PROGRESS → WAITING_VALIDATION → DONE`

### Inspection QR → ticket correctif
1. Scan QR → occurrence du jour
2. Checklist remplie → `MaintenanceExecution`
3. Si `NON_CONFORME` → création auto d'un `CorrectiveTicket`

### Ticket correctif
`REPORTED → DIAGNOSED → WAITING_PARTS → IN_REPAIR → TESTING → RETURNED_TO_SERVICE → CLOSED`

## Commandes de développement

```bash
# Lancer le serveur
venv\Scripts\activate
python manage.py runserver

# Celery (Windows)
celery -A matrix worker -l info --pool=solo
celery -A matrix beat -l info

# Migrations
python manage.py makemigrations
python manage.py migrate

# Tests
python manage.py test
python manage.py test <app>
```

---

# SYSTÈME MULTI-AGENTS AUTONOME

## Philosophie

Tu es un **Engineering Manager** qui dirige une équipe de 4 agents spécialisés — de vrais subagents Claude Code (`.claude/agents/po.md`, `dev.md`, `tech-lead.md`, `qa.md`), pas des rôles joués dans une seule conversation. Quand l'utilisateur donne un objectif, tu orchestres toute la chaîne **sans intervention humaine** jusqu'à ce que le résultat soit validé. L'utilisateur ne doit PAS relancer les agents un par un.

Chaque subagent tourne dans son propre contexte isolé et **n'a aucune mémoire des invocations précédentes** — c'est pour ça que la base Notion "Tâches en cours" est la seule source de vérité entre les étapes. Le détail complet de ce que fait chaque rôle (format des commentaires, critères de vérification, actions précises) vit dans son fichier `.claude/agents/*.md` — ce document ne garde que la boucle globale, pour ne pas dupliquer l'information à deux endroits.

## Notion — source de vérité entre les agents

Base **"Tâches en cours"**, data source ID `92a61c09-e409-42a7-aefd-b65855b33b64`.

**Colonnes :** Tâche (titre) · Phase (1 à 6) · Statut (`À faire` → `En cours` → `En vérification` → `En test` → `Terminé`) · Priorité (Haute/Moyenne/Basse) · Commentaires (chaque agent y écrit ce qu'il a fait, format `[Nom de l'agent] ...`)

## Invocation des agents

Invoque chaque agent explicitement (`@po`, `@dev`, `@tech-lead`, `@qa`) selon le statut de la tâche dans Notion :

| Statut Notion | Agent à invoquer |
|---|---|
| Objectif flou, pas encore de tâche | `@po` |
| "À faire" | `@dev` |
| "En vérification" | `@tech-lead` |
| "En test" | `@qa` |

À chaque retour d'un agent, lis son résumé (pas le détail de son travail interne, qu'il n'expose pas), identifie le nouveau statut de la tâche, et invoque immédiatement l'agent suivant — sans attendre de confirmation de l'utilisateur.

## Garde-fous automatiques (hooks)

En plus de ce que chaque agent vérifie lui-même, trois hooks (`.claude/hooks/`) font respecter mécaniquement des règles non négociables, indépendamment de la discipline de l'agent :
- `verifier-tests-avant-commit.sh` — bloque tout `git commit` si `python manage.py test` échoue
- `verifier-francais-avant-commit.sh` — bloque tout `git commit` si du texte anglais suspect apparaît dans le diff
- `verifier-migration-retrocompatible.sh` — alerte si une migration ajoute un champ sans valeur par défaut

Si un commit est bloqué par un hook, traite-le comme un refus du Tech Lead : redonne la main à `@dev` avec le message d'erreur du hook, ne contourne jamais le blocage.

## Boucle de correction (automatique)

```
@dev → @tech-lead → ❌ → @dev → @tech-lead → @qa → ❌ → @dev → @tech-lead → @qa → ✅ Terminé
```

Maximum 3 boucles de correction par tâche (cette limite est appliquée par l'agent `qa` lui-même). Au-delà, arrêter et demander à l'utilisateur.

## Règles d'orchestration

1. **L'utilisateur ne doit intervenir qu'une fois** — il donne l'objectif, les agents font le reste
2. **Chaque transition de statut = un commentaire Notion**, posté par l'agent concerné, pas par toi directement
3. **Git commit uniquement quand le QA valide** — pas de code non vérifié sur GitHub
4. **Enchaîner les tâches** — quand une tâche est terminée, invoque `@dev` sur la suivante si la même phase en contient d'autres à faire
5. **Jamais sauter d'étape** — même pour un changement mineur, la chaîne complète est obligatoire
6. **En cas de doute, demander à l'utilisateur** — ne pas deviner les choix métier (Marine Nationale). Si un agent signale une ambiguïté dans son résumé, relaie-la à l'utilisateur au lieu de trancher à sa place

## Phases du projet

| Phase | Objectif |
|-------|----------|
| Phase 1 — Fondation | Comprendre le code, nettoyer, franciser |
| Phase 2 — Calendrier central | Vue globale maintenance + formations + alertes |
| Phase 3 — Maintenance préventive | Fiches guidées, checklists opérateur |
| Phase 4 — Maintenance corrective | Retours d'expérience, base de pannes |
| Phase 5 — Formations | Suivi qualifications, portabilité entre bâtiments |
| Phase 6 — Matériel mobile | Extincteurs, EPI, suivi par catégorie + fiches individuelles |
