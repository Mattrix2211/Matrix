# Audit 07 — Calendrier et coordination

**Statut : partiel.** Preuves exécutées (API JSON, base de démonstration `seed_demo`, 12 profils). Navigateur : seule la présence de la page a été vérifiée dans le balayage de navigation ; la vue mois/semaine, le panneau de détail et le glisser-déposer n'ont pas été joués.

## Questions et réponses

| Question | Réponse | Preuve |
|---|---|---|
| Le calendrier est-il central (Cahier §15) ? | **Oui sur le plan structurel** : 7 sources alimentent le même flux (maintenance, formation, quart, service de garde, absence, tâche, programme du bâtiment) | `sondes/calendrier.py` |
| Étanchéité entre bâtiments | **Conforme** : `marin_abe_1` qui demande `ship=Bretagne` ne reçoit que ses 3 événements | idem |
| Flux iCal personnel | 200 pour un connecté, 401 pour un anonyme | idem |
| Déplacement d'un événement par un équipier | refusé (400 avec la charge d'essai ; le droit d'écriture est en dur « chef de section », P05) | idem |
| Vue personnelle ou collective par défaut | **Constat** : le flux API par défaut d'un équipier contient 183 événements dont 173 quarts et services de garde d'autres marins ; l'interface applique peut-être un filtre « mes événements » (non vérifié en navigateur). La décision PO « Mon quotidien : activités du marin d'abord » est validée pour plus tard | idem ; Notion (décision du 28/10) |
| Conflits et dépendances | non audité ; le détecteur partagé de conflits (D-06 A) est une tâche **À faire** | Notion |
| Liens vers les autres modules | détail d'événement par type (`/calendar/detail/<type>/<id>/`) et commentaire contextuel présents ; non rejoué | `calendar_app/urls.py` |

## Écarts et anomalies

- AUD-025 (vue collective par défaut dans l'API) : à confirmer en navigateur avant de qualifier.
- Droits d'édition du calendrier codés en dur (P05).
- Conflits de planning non détectés (D-06 en backlog, volontairement non commencé).

## Non vérifié

Interface FullCalendar (mois, semaine, liste), performance avec un historique réel, fuseaux horaires (relèves datées), impression A4, mobile, dépendances entre événements.
