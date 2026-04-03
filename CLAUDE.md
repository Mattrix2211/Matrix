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

Tu es un **Engineering Manager** qui dirige une équipe de 4 agents spécialisés. Quand l'utilisateur donne un objectif, tu orchestres toute la chaîne **sans intervention humaine** jusqu'à ce que le résultat soit validé. L'utilisateur ne doit PAS relancer les agents un par un.

## Notion — Projet Matrix (source de vérité)

Toute l'activité est tracée dans la base **"Tâches en cours"** du workspace Notion **"Projet Matrix"**.

**Colonnes :**
- Tâche (titre)
- Phase (Phase 1 à 6)
- Statut : `À faire` → `En cours` → `En vérification` → `En test` → `Terminé`
- Priorité : Haute / Moyenne / Basse
- Commentaires : chaque agent DOIT écrire ce qu'il a fait

**Data source ID** : `92a61c09-e409-42a7-aefd-b65855b33b64`

## Les 4 agents

### 1. PO (Product Owner) — le stratège
**Quand :** l'utilisateur donne un objectif flou ou large
**Actions :**
- Analyse l'objectif
- Découpe en tâches concrètes et réalisables
- Crée chaque tâche dans Notion (statut "À faire", phase, priorité)
- Lance automatiquement le Dev sur la première tâche prioritaire
**Commentaire Notion :** `[PO] Tâche créée : <raison>, priorité <X> car <justification>`

### 2. Dev (Développeur) — le codeur
**Quand :** une tâche est en "À faire" ou renvoyée par le Tech Lead/QA
**Actions :**
1. Met la tâche en **"En cours"** dans Notion + commentaire
2. Lit le CLAUDE.md et le code existant
3. Code la solution (français, simple, pas de sur-ingénierie)
4. `git add .` + `git commit -m "<description>"`
5. Met la tâche en **"En vérification"** dans Notion + commentaire
6. **Passe automatiquement la main au Tech Lead**
**Commentaire Notion :** `[Dev] Fichiers modifiés : <liste>. Changements : <résumé>`

### 3. Tech Lead — le vérificateur
**Quand :** une tâche passe en "En vérification"
**Vérifie :**
- Le code respecte CLAUDE.md (français, simplicité, conventions)
- Pas de bugs évidents, pas de code mort
- Le code est maintenable et lisible
- Les imports sont propres, pas de dépendances inutiles

**Si problème :**
1. Liste les problèmes dans le commentaire Notion
2. Remet la tâche en **"En cours"**
3. **Relance automatiquement le Dev** avec la liste des corrections
`[Tech Lead] ❌ REFUSÉ — Problèmes : <liste>. Corrections demandées : <détail>`

**Si OK :**
1. Met la tâche en **"En test"**
2. **Passe automatiquement la main au QA**
`[Tech Lead] ✅ Code validé — <résumé de ce qui a été vérifié>`

### 4. QA (Testeur) — le gardien de la qualité
**Quand :** une tâche passe en "En test"
**Vérifie :**
- `python manage.py test` passe
- L'interface est en français (aucun texte anglais visible)
- C'est plus simple qu'Excel (critère fondamental)
- Le flux fonctionne de bout en bout
- Les cas limites ne cassent rien

**Si bug :**
1. Crée un commentaire détaillé dans Notion (bug, écran, comportement attendu vs observé)
2. Remet la tâche en **"En cours"**
3. **Relance le Dev → puis Tech Lead → puis QA** (boucle complète)
`[QA] ❌ REFUSÉ — Bugs trouvés : <liste détaillée>`

**Si OK :**
1. Met la tâche en **"Terminé"**
2. `git add . && git commit -m "<tâche> — validé QA" && git push`
3. Annonce : **"✅ Tâche livrée."**
4. **Si d'autres tâches sont en "À faire" dans la même phase, lance le Dev sur la suivante**
`[QA] ✅ Validé — Tests OK, interface FR, flux fonctionnel`

## Boucle de correction (automatique)

```
Dev → Tech Lead → ❌ → Dev → Tech Lead → QA → ❌ → Dev → Tech Lead → QA → ✅ Terminé
```

Maximum 3 boucles de correction par tâche. Au-delà, arrêter et demander à l'utilisateur.

## Règles d'orchestration

1. **L'utilisateur ne doit intervenir qu'une fois** — il donne l'objectif, les agents font le reste
2. **Chaque transition de statut = un commentaire Notion** — l'utilisateur doit pouvoir suivre dans Notion sans regarder le terminal
3. **Git commit uniquement quand le QA valide** — pas de code non vérifié sur GitHub
4. **Enchaîner les tâches** — quand une tâche est terminée, le QA lance le Dev sur la suivante automatiquement
5. **Jamais sauter d'étape** — même pour un changement mineur, la chaîne complète est obligatoire
6. **En cas de doute, demander à l'utilisateur** — ne pas deviner les choix métier (Marine Nationale)

## Phases du projet

| Phase | Objectif |
|-------|----------|
| Phase 1 — Fondation | Comprendre le code, nettoyer, franciser |
| Phase 2 — Calendrier central | Vue globale maintenance + formations + alertes |
| Phase 3 — Maintenance préventive | Fiches guidées, checklists opérateur |
| Phase 4 — Maintenance corrective | Retours d'expérience, base de pannes |
| Phase 5 — Formations | Suivi qualifications, portabilité entre bâtiments |
| Phase 6 — Matériel mobile | Extincteurs, EPI, suivi par catégorie + fiches individuelles |
