# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Matrix** (nom du projet, le package Django s'appelle `bordops`) — application de gestion opérationnelle pour la Marine Nationale. Django 5 + Celery + Redis + SQLite (dev) / PostgreSQL (prod), frontend Django Templates + Bootstrap 5 + HTMX.

**Principes fondamentaux :**
- Interface 100 % en français — tous les labels, messages, boutons, et noms de champs doivent être en français
- Plus rapide et plus simple qu'un tableau Excel : privilégier les workflows courts, les formulaires pré-remplis, les actions en un clic
- Chaque marin dispose d'un espace personnel affichant ses tâches du jour, ses prochaines maintenances assignées et ses formations à venir

**Deux types d'équipements :**
- **Installations** : équipements fixes du navire (propulseurs, pompes, systèmes électriques…), propres à chaque bâtiment, gérés dans l'app `assets` via le modèle `Installation`
- **Matériel mobile** : équipements transverses (extincteurs, EPI, multimètres, élingues…), suivis par catégorie avec une fiche individuelle par article (numéro de série, date de contrôle, péremption)

## Commands

### Setup
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo   # optional demo data
```

### Development
```bash
python manage.py runserver                        # web server → http://127.0.0.1:8000
celery -A bordops worker -l info --pool=solo      # async worker (Windows)
celery -A bordops beat -l info                    # task scheduler
```

### Database
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```

### Tests
```bash
python manage.py test                  # all tests
python manage.py test maintenance      # single app
coverage run --source='.' manage.py test && coverage report
```

### Static files
```bash
python manage.py collectstatic --noinput
```

### Docker (PostgreSQL + Redis)
```bash
docker compose up -d
# then set DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT env vars before runserver
```

## Architecture

### Django apps (10 modules)

| App | Responsibility |
|-----|---------------|
| `accounts` | Users, roles, UserProfile (ship/service/sector/section scope) |
| `org` | Organizational hierarchy: Ship → Service → Sector → Section |
| `assets` | Asset & Installation inventory, checklists, QR code inspection |
| `maintenance` | Preventive maintenance plans, occurrence scheduling, execution |
| `logistics` | Corrective tickets, parts requests, repair workflow |
| `training` | Training courses, sessions, qualification records & expiry |
| `threads` | Generic discussions (ContentType FK, attaches to any model) |
| `notifications` | In-app alerts for overdue maintenance & expiring training |
| `dashboard` | JSON API endpoints for Chart.js charts |
| `calendar_app` | Calendar views & iCal (.ics) export |

### URL structure
- `/api/*` — DRF REST API (one router per app)
- `/` — Template-driven web UI
- `/maintenance/`, `/logistics/`, `/assets/`, `/calendar/`, `/users/` — web sub-routes

### Key workflows

**Preventive maintenance (Celery-driven)**
- `generate_occurrences` runs daily, creates `MaintenanceOccurrence` rows 90 days ahead per `MaintenancePlan`
- `compute_overdue` runs hourly, marks past-due occurrences as OVERDUE
- Status: `PLANNED → ASSIGNED → IN_PROGRESS → WAITING_VALIDATION → DONE`

**QR code inspection → corrective ticket**
1. QR scan → `StartVisualCheckView` creates/finds today's occurrence
2. User fills checklist → `MaintenanceExecution` saved
3. If result is `NON_CONFORME` → post_save signal auto-creates `CorrectiveTicket`

**Corrective ticket**
- Status machine: `REPORTED → DIAGNOSED → WAITING_PARTS → IN_REPAIR → TESTING → RETURNED_TO_SERVICE → CLOSED`
- `PartRequest` + `PartLineItem` tracks parts ordering per ticket
- Full audit trail in `TicketStatusLog`

### Core patterns

- **Base models** (`core/models.py`): `TimeStampedModel` (auto timestamps), `OwnedModel` (created_by/updated_by)
- **UUID PKs** on `Asset`, `Installation`, `CorrectiveTicket`
- **Role hierarchy**: `MASTER_ADMIN → ADMIN_NAVIRE → COMMANDANT → ETAT_MAJOR → CHEF_SERVICE → CHEF_SECTEUR → CHEF_SECTION → EQUIPIER`
- **Data scoping**: `UserProfile` is scoped to one org level; `core/scopes.py` + `core/permissions.py` enforce access
- **JSON fields** for flexible config: `SectorConfig.dashboard_widgets`, `ChecklistTemplate` items, `MaintenanceExecution.results`
- **Generic FK** (ContentType) in `threads.Thread` and `notifications.Notification` for polymorphic relations
- Each app has both `views.py` (DRF API) and `web_views.py` (Django template views)

### Configuration
- `bordops/settings.py` — main settings; DB switches to PostgreSQL when `DB_HOST` env var is set
- `.env.example` — reference for all env vars (`DJANGO_SECRET_KEY`, `DB_*`, `CELERY_BROKER_URL`, `EMAIL_*`)
- `bordops/celery.py` — Celery app; beat schedule defined in `settings.py` (`CELERY_BEAT_SCHEDULE`)
