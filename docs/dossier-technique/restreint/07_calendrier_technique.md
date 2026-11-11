# Chapitre 7 (technique) — Calendrier : mécanismes

> **Diffusion restreinte.** Complète `diffusable/07_calendrier.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** l'agrégation des sources, les règles de visibilité et de déplacement, l'API JSON, le flux iCal et les points d'entrée.

---

## 7T.1 Architecture

Le paquet `calendar_app` a **un seul modèle** (`PersonalEvent`, `calendar_app/models.py:7` : événement personnel, visible de son propriétaire seul). Le reste est de la **lecture agrégée**, découpée par sous-domaine (`views.py` ne fait que réexporter) :

| Module | Rôle |
|---|---|
| `sources.py` | Les **9 sources** (`SOURCES`, `calendar_app/sources.py:9`) : clé, libellé, icône, couleurs (teintes assombries pour respecter le contraste WCAG AA) ; alimente légende, filtre par type et API |
| `evenements_sources.py` | Requêtes communes : `occurrences_visibles` (`calendar_app/evenements_sources.py:241`), `tickets_visibles` (`calendar_app/evenements_sources.py:248`), `sessions_visibles` (`calendar_app/evenements_sources.py:70`), `marins_visibles` (`calendar_app/evenements_sources.py:61`), `evenements_utilisateur_jour` (`calendar_app/evenements_sources.py:180`), `evenements_equipe` (`calendar_app/evenements_sources.py:270`) ; partagé par la vue HTML, l'API JSON et le digest « Ma journée » |
| `index_views.py` | `CalendarView` (`calendar_app/index_views.py:36`) : vues `day`, `week`, `month`, filtres organisationnels |
| `api_views.py` | Source d'événements JSON pour FullCalendar (`/calendar/events/`) |
| `detail_views.py` | Panneau de détail (fragment HTMX) ; `detail_commentaire` (`calendar_app/detail_views.py:105`) : réponse dans le fil, créé à la première réponse |
| `deplacement_views.py` | `calendar_event_move` (`calendar_app/deplacement_views.py:41`) : glisser-déposer |
| `evenements_personnels_views.py` | `personal_event_save` (`calendar_app/evenements_personnels_views.py:24`), `personal_event_delete` (`calendar_app/evenements_personnels_views.py:93`, propriétaire seul) |
| `ical_views.py` | `user_ical_feed` (`calendar_app/ical_views.py:13`) |

## 7T.2 Visibilité

- **Maintenance et tickets** : bornés par `build_scope_q` sur le matériel mobile **ou** l'installation fixe, plus les objets assignés à l'utilisateur.
- **Sessions de formation** : par **affectation personnelle** (`attendees`, `reservations`, `instructor`) ; le filtre par périmètre a été abandonné car la formation est une fiche globale partagée (portabilité des qualifications).
- **Vue d'équipe** : `marins_visibles` = soi-même plus l'équipe de qui peut superviser (`peut_superviser`, seuil `tache_attribution`) et l'équipage de l'appelant ; `evenements_equipe` : tâches (retards en évidence), absences, quarts et gardes.
- **Filtres** : `filtres_organisation_coherents` invalide un enfant incompatible avec son parent ; `filtre_identifiant_invalide` renvoie une 400 en français si un identifiant n'est pas numérique ; le filtre `equipe` n'est admis que par l'API.
- Le module activable ne se voit pas ici : une source dont le module est désactivé disparaît côté web (chapitre 4).

## 7T.3 Déplacement par glisser-déposer

`calendar_event_move` (POST `/calendar/events/move/`, authentification obligatoire) accepte quatre types :

| Type | Droit | Trace |
|---|---|---|
| `ticket` | `niveau_ecriture` ≥ chef de section **et** ticket dans le périmètre (sinon 404) **et** `niveau_ecriture_sur` ≥ chef de section (état-major borné à ses services) | `calendar_move_ticket` |
| `maintenance` | Assigné, ou occurrence dans le périmètre puis `niveau_ecriture_sur` ≥ chef de section | `calendar_move_occurrence` **seulement** quand un chef replanifie celle d'un tiers |
| `training` | `niveau_ecriture` ≥ chef de section **et** affectation personnelle à la session | `calendar_move_training_session` |
| `personal` | Propriétaire | aucune |

Un objet hors périmètre répond **404** (comme s'il n'existait pas) ; un droit insuffisant sur un objet visible, **403**. Les quarts, gardes, tâches et absences ne sont **pas déplaçables** depuis le calendrier.

## 7T.4 Flux iCal

`user_ical_feed` répond **401** sans session. Contenu : occurrences de maintenance **assignées** (matériel mobile et installations), sessions de formation (inscrit, présent ou formateur), créneaux de quart sur listes **publiées**, créneaux de garde en vigueur ou prévisionnels, absences, événements personnels (bibliothèque `icalendar`). **Ni tâches, ni programme.** Aucun jeton : l'authentification est celle de la session.

## 7T.5 Routes

`/calendar/` (vues), `/calendar/events/`, `/calendar/events/move/`, `/calendar/personnel/enregistrer/`, `/calendar/personnel/<id>/supprimer/`, `/calendar/detail/<type>/<id>/` (+ `…/commentaire/`), `/calendar/detail/tache/<id>/demarrer/`, `/calendar/ical/my/` (`calendar_app/urls.py`).

## 7T.6 Tests

`calendar_app/tests/` (124 fonctions de test), dont les contrôles de périmètre et de déplacement.

## 7T.7 Limites et éléments non vérifiés

- ⚪ Le flux iCal est lié à la session : un client d'agenda externe qui ne conserve pas la session ne peut pas s'abonner sans mécanisme complémentaire (non étudié).
- ⚪ Le détail HTMX du panneau (fil, démarrage d'une tâche) n'a pas été rejoué dans un navigateur.
- 🔵 Calendrier intégrateur et échéances : non développés.

---

**Sources (état B).** Références en ligne ; `couverture/etat_B/INVENTAIRE.md` (le paquet importe 9 paquets).
