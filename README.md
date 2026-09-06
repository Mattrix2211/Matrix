# Matrix

Plateforme numérique opérationnelle quotidienne pour la Marine Nationale française — maintenance préventive et corrective, matériel mobile, formations, logistique, notifications, tableaux de bord, et bientôt quarts/services à quai/échanges. La maintenance (GMAO) est un module de Matrix, pas sa finalité : l'objectif est que chaque marin ouvre Matrix tous les jours, pas seulement quand il touche à un équipement.

**Vision et feuille de route complètes : voir [`VISION_MATRIX_2_0.md`](VISION_MATRIX_2_0.md)** — à lire avant toute décision d'architecture ou de nouveau module. `CLAUDE.md` reste la référence du quotidien pour Claude Code.

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
Un fichier `.env` (copié depuis `.env.example`) doit exister à la racine **avant** de lancer
Docker : `POSTGRES_PASSWORD` n'a plus de valeur par défaut, le démarrage du conteneur `db`
échoue explicitement si elle n'est pas définie (pas de mot de passe trivial en prod par oubli).
Les ports de `db` (5432) et `redis` (6379) ne sont exposés que sur `127.0.0.1` de la machine
hôte (pas sur le réseau) : suffisant pour ce workflow, où Django/Celery tournent hors conteneur
et s'y connectent via `localhost`.
```bash
docker compose up -d
set DB_HOST=localhost
set DB_NAME=matrix
set DB_USER=matrix
set DB_PASSWORD=matrix
set DB_PORT=5432
python manage.py migrate
```

## Celery (requis pour les alertes automatiques : échéances de maintenance, stock bas, retards, détection de dérive)
Les alertes automatiques ne sont **pas** envoyées par le serveur Django lui-même : elles sont
produites par des tâches planifiées (Celery Beat) exécutées en tâche de fond par un worker
Celery. **Sans worker + Beat qui tournent, aucune notification automatique n'apparaît**, même
si la donnée qui la déclenche (ex : relevé technique en dérive) est bien visible sur la fiche
correspondante. Ce n'est pas un bug : c'est le fonctionnement normal si ces deux processus ne
sont pas lancés.

Redis (le broker utilisé par Celery) doit également tourner (`docker compose up -d`, voir
ci-dessus).

Deux processus **séparés**, à laisser ouverts en plus du serveur Django (`python manage.py
runserver`) :
```bash
celery -A matrix worker -l info --pool=solo   # Windows (obligatoire en dev pour recevoir les alertes)
celery -A matrix beat -l info                  # planifie l'exécution périodique des tâches ci-dessus
```

En pratique, pour tester une alerte sans attendre la prochaine échéance planifiée (Celery Beat
exécute ces tâches à un rythme quotidien ou horaire selon le cas), on peut aussi déclencher la
tâche manuellement en shell Django (`python manage.py shell`) :
```python
from notifications.tasks import detect_installation_drift
detect_installation_drift()   # crée immédiatement les Notification concernées, sans attendre Beat
```

`start.bat` lance déjà worker + Beat automatiquement en arrière-plan (voir `celery.log` /
`celery-beat.log` à la racine en cas de doute), mais uniquement si Redis est démarré au préalable
(`docker compose up -d`) : sans Redis disponible, Celery démarre mais ne peut pas se connecter,
et échoue silencieusement en arrière-plan (aucune alerte ne remonte, sans message d'erreur visible
côté application).

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
- `dashboard` — tableau de bord personnel + vue flotte scopée au périmètre du chef connecté (rôles CHEF_SECTION et au-dessus : section, secteur, navire ou flotte entière selon le rôle)
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
