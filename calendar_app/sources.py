"""Sources du calendrier : libellé, icône et couleurs de chaque type d'événement, à un seul endroit.

Alimente les couleurs de l'API FullCalendar, la légende et le filtre par type de la page."""
from collections import namedtuple

Source = namedtuple("Source", "cle libelle icone fond bordure texte")

# Teintes assombries : un texte blanc sur #20c997/#d63384 ne respecte pas le contraste WCAG AA (< 4,5:1).
SOURCES = (
    Source("maintenance", "Maintenance", "maintenance", "#0d6efd", "#0a58ca", "#fff"),
    Source("ticket", "Ticket", "ticket", "#b8500a", "#964008", "#fff"),
    Source("training", "Formation", "formation", "#198754", "#146c43", "#fff"),
    Source("quart", "Quart", "quart", "#0b7285", "#095c6b", "#fff"),
    Source("service_garde", "Garde", "garde", "#a61e4d", "#84173d", "#fff"),
    Source("ronde", "Ronde", "ronde", "#5f3dc4", "#4c2fa0", "#fff"),
    Source("tache", "Tâche", "tache", "#2b6a3f", "#1f4f2e", "#fff"),
    Source("absence", "Absence", "absence", "#7c4a03", "#5c3702", "#fff"),
    Source("programme", "Programme du bâtiment", "calendrier", "#0d4f8b", "#0a3d6d", "#fff"),
    Source("personal", "Personnel", "personnel", "#6f42c1", "#59339d", "#fff"),
)

COULEUR_PAR_TYPE = {s.cle: {"backgroundColor": s.fond, "borderColor": s.bordure, "textColor": s.texte} for s in SOURCES}
CONCEPT_ICONE_PAR_TYPE = {s.cle: s.icone for s in SOURCES}
