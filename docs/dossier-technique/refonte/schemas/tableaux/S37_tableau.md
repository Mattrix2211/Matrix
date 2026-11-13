<!-- Brouillon généré depuis S37_flux_asynchrones.mmd : à rédiger en phrases ; le schéma est remplacé par ce tableau (plan §4). -->

| Élément | Contenu |
|---|---|
| `BT` | Celery beat : 20 tâches planifiées |
| `M1` | Maintenance : génération des échéances, calcul des retards |
| `M2` | Alertes : retards, échéances proches, stock bas, dérives, formations qui expirent |
| `M3` | Vie du bord : Ma journée, annonces diffusées et rappelées, tâches en retard |
| `M4` | Quarts : activation des listes à l'échéance, divergences de feuilles |
| `M5` | Entretien : sessions expirées, brouillons purgés, relèves appliquées |
| `N` | Notifications dans l'application, puis Web Push pour les alertes critiques |

| De | Condition ou passage | Vers |
|---|---|---|
| Celery beat : 20 tâches planifiées | — | Maintenance : génération des échéances, calcul des retards |
| Alertes : retards, échéances proches, stock bas, dérives, formations qui expirent | — | Notifications dans l'application, puis Web Push pour les alertes critiques |
| Vie du bord : Ma journée, annonces diffusées et rappelées, tâches en retard | — | Notifications dans l'application, puis Web Push pour les alertes critiques |
| Quarts : activation des listes à l'échéance, divergences de feuilles | — | Notifications dans l'application, puis Web Push pour les alertes critiques |
