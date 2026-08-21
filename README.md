# Matrix

Application Django de gestion opérationnelle pour la Marine Nationale française : maintenance préventive et corrective, matériel mobile, formations, logistique, notifications et tableaux de bord.

## Stack
- Python 3.12+, Django 5, DRF, Bootstrap 5 + HTMX
- SQLite (dev), PostgreSQL (prod), Celery + Redis (tâches planifiées)
- Export : PDF (WeasyPrint — optionnel, dégradation propre si absent), CSV/Excel (openpyxl)
- Notifications Web Push (pywebpush, clé VAPID auto-hébergée, aucun CDN)

## Démarrage rapide (dev, SQLite)
```bash
python -m venv venv
venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate     # macOS/Linux

git submodule update --init --recursive   # design system (logo, charte graphique)
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo     # optionnel : données de démonstration
python manage.py runserver
```

Accès : http://127.0.0.1:8000/ (admin : `/admin/`)

L'export PDF des bilans nécessite les bibliothèques natives GTK (WeasyPrint) — absentes par défaut sous Windows. Sans elles, tout le reste de l'application fonctionne normalement ; seul l'export PDF reste indisponible (CSV/Excel restent disponibles).

## Docker services (Postgres + Redis)
```bash
docker compose up -d
set DB_HOST=localhost
set DB_NAME=matrix
set DB_USER=matrix
set DB_PASSWORD=matrix
set DB_PORT=5432
python manage.py migrate
```

## Celery (optionnel — tâches planifiées : échéances de maintenance, alertes, détection de dérive)
```bash
celery -A matrix worker -l info --pool=solo   # Windows
celery -A matrix beat -l info
```

## Notifications Web Push (optionnel)
```bash
python manage.py generate_vapid_keys
```
Renseigner les variables d'environnement `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_ADMIN_EMAIL` affichées par la commande. Sans clés VAPID configurées, le Web Push est simplement désactivé (aucune erreur). Nécessite HTTPS ou `localhost` côté navigateur.

## Tests
```bash
python manage.py test
```

## Applications principales
- `accounts` — profils utilisateurs, rôles hiérarchiques (`MASTER_ADMIN` → ... → `EQUIPIER`)
- `org` — hiérarchie Navire → Service → Secteur → Section
- `assets` — installations fixes + matériel mobile, checklists, documents, mesures techniques (heures/vibration/isolement), hiérarchie parent/enfant, détection de dérive avant seuil
- `maintenance` — plans préventifs, occurrences, exécutions guidées, signature de validation (mot de passe) sur les transitions critiques
- `logistics` — tickets correctifs, demandes de pièces, stock, retours d'expérience (REX)
- `training` — formations, prérequis (anti-cycle), catégories, arbre de compétences visuel, référents habilités par formation, réservation self-service de sessions
- `threads` — discussions génériques attachées à n'importe quel objet
- `notifications` — alertes in-app (info/warning/danger) + Web Push pour le niveau danger
- `dashboard` — tableau de bord personnel + vue flotte (rôles CHEF_SERVICE et au-dessus)
- `calendar_app` — calendrier central, vue globale + personnelle, export iCal
- `reports` — bilans instantané/période, export PDF/CSV/Excel

## Flots clés
- **Scan QR** : équipement → checklist du jour → si `NON_CONFORME`, création automatique d'un ticket correctif
- **Ticket correctif** : `REPORTED → DIAGNOSED → WAITING_PARTS → IN_REPAIR → TESTING → RETURNED_TO_SERVICE → CLOSED` (mot de passe requis sur `RETURNED_TO_SERVICE` si l'installation est critique ; REX obligatoire à la fermeture)
- **Formations** : prérequis entre formations → validation par un référent habilité (indépendant du rang hiérarchique) → arbre de compétences visuel par secteur/catégorie → réservation de session par le marin
- **Export** : CSV/Excel sur les listes et les bilans (toujours disponible), PDF en plus si WeasyPrint/GTK est installé

## Pistes futures
- HTTPS en production pour activer réellement le Web Push (dégradé proprement en HTTP simple)
- Liste d'attente sur les sessions de formation complètes (v1 : refus simple)
- Verrouillage `select_for_update` sur la capacité de session (fenêtre de course mineure en cas de double clic simultané sur la toute dernière place)
