"""Vues du calendrier central — module de réexport.

Fichier découpé par sous-domaine fonctionnel (tâche Notion « [ARCH] Découper
calendar_app/views.py (932 lignes) par sous-domaine »), suivant le même
principe que quarts/web_views.py, dashboard/web_views.py, assets/web_views.py
et training/web_views.py :
- calendar_app/evenements_sources.py — sources d'événements communes (filtres,
  périmètre, créneaux de quart/garde, absences, rondes, événements
  personnels, agrégation d'une journée pour « Ma journée »)
- calendar_app/index_views.py — vue HTML du calendrier (CalendarView)
- calendar_app/api_views.py — API JSON FullCalendar (calendar_events)
- calendar_app/deplacement_views.py — déplacement par glisser-déposer
  (calendar_event_move)
- calendar_app/evenements_personnels_views.py — événements personnels libres

Les noms sont réimportés ici pour que urls.py et les imports existants
(`from calendar_app.views import calendar_events`, `evenements_utilisateur_jour`)
continuent de fonctionner, sans changement de comportement."""
from .evenements_sources import evenements_utilisateur_jour  # noqa: F401
from .index_views import CalendarView  # noqa: F401
from .api_views import calendar_events  # noqa: F401
from .deplacement_views import calendar_event_move  # noqa: F401
from .evenements_personnels_views import personal_event_delete, personal_event_save  # noqa: F401
