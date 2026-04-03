# BordOps

Application Django pour la gestion opérationnelle à bord (maintenance, logistique, formations, threads, notifications, tableaux de bord).

## Stack
- Python 3.12+, Django 5, DRF, HTMX + Bootstrap 5
- PostgreSQL (prod), SQLite (dev), Celery + Redis
- Stockage fichiers local (dev), abstraction via django-storages

## Démarrage rapide (dev, SQLite)
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

Accès: http://127.0.0.1:8000/ (admin: /admin/)

## Docker services (Postgres + Redis)
```bash
# Lancer BDD et Redis
docker compose up -d
# Configurer env pour Postgres
set DB_HOST=localhost
set DB_NAME=matrix
set DB_USER=matrix
set DB_PASSWORD=matrix
set DB_PORT=5432
# Appliquer migrations
python manage.py migrate
```

## Celery
Deux processus sont requis pour les tâches asynchrones et planifiées:
```bash
# Worker
celery -A matrix worker -l info
# Beat (planification)
celery -A matrix beat -l info
```

## Tests
```bash
python manage.py test
```

## Applications principales
- accounts: profils utilisateurs et rôles
- org: bateau, service, secteur, section, configuration
- assets: types, actifs, checklists (standard/personnalisée), documents, lieux
- maintenance: plans, occurrences, exécutions (préventif)
- logistics: tickets correctifs, demandes de pièces, lignes
- training: cours, exigences, sessions, enregistrements
- threads: fils, messages, pièces jointes
- notifications: notifications in-app
- dashboard: endpoints JSON pour Chart.js
- calendar_app: vue calendrier (squelette)

## Flots clés
- QR: page actif → démarrer contrôle visuel → compléter checklist → si NON_CONFORME, ouvrir un ticket correctif (à compléter)
- Correctif + Logistique: transitions de ticket, demandes de pièces (voir endpoints)
- Modèles vs personnalisé: checklists par type + overrides par actif
- Threads + PJ: commentaire/attachment sur ticket/occurrence/etc.

## À compléter ensuite
- RBAC avancé et scoping administrateur
- Notifications e-mail optionnelles
- Flux iCal par utilisateur
- UI HTMX complète pour les actions courantes
- Génération auto de ticket quand NON_CONFORME, escalades
```