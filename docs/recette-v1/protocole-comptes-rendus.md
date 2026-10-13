# Format commun des comptes rendus et des preuves

Un fichier par exécution dans `rapports/`, nommé `AAAA-MM-JJ-<id>.md`. En-tête obligatoire : SHA testé, base utilisée (SQLite ou PostgreSQL), commande de préparation, navigateur et résolution (marins), date.

## Partie « technique » (équipe A)

| Champ | Contenu |
|---|---|
| Id | `SEC-nn`, `INT-nn`, `ERG-nn` |
| Ligne de couverture | Référence à `couverture.md` |
| Statut | Prévu · Exécuté · Réussi · Échoué · Non testé · Impossible à vérifier |
| Preuve | Commande exacte et sortie utile, ou requête (compte, méthode, URL, code HTTP), ou capture |
| Constat | Observé / attendu, fichier:ligne si une règle est en cause |
| Priorité | P0 à P3 (défauts seulement) |

## Partie « marin » (équipe B)

| Champ | Contenu |
|---|---|
| Mission, persona, compte | Id et compte réellement utilisé |
| Réussite | Oui / partielle / non, et raison |
| Chemin suivi | Écran par écran, dans l'ordre, avec libellés exacts rencontrés |
| Mesures | Durée, nombre d'actions, nombre de changements d'écran, retours en arrière |
| Hésitations et détours | Où et pourquoi |
| Termes | Libellés incompris ou ambigus, verbatim |
| Retour système | Confirmations claires ? Message d'erreur utile ? |
| Correction | Peut-il défaire une erreur ? |
| Droits constatés | Ce qui était visible/possible et qui ne le devrait pas (signaler tout de suite), ou bloqué à tort |
| Avantage perçu | Face au papier / Excel, en tant que ce personnage |
| Preuves | Captures horodatées nommées `<mission>-<étape>.png` |

## Partie « observateur »

Tableau : observation · marins concernés · catégorie (bug, permission/périmètre, parcours complexe, fonction difficile à découvrir, libellé incompréhensible, incohérence, fonction manquante, simple préférence) · impact · preuves · priorité proposée · statut (hypothèse à confirmer / confirmé par test technique).

## Règles de preuve

- Une durée mesurée sans horodatage d'outil n'est pas une mesure : écrire « non mesurée ».
- « Réussi » exige une preuve jointe. Sans elle : « Exécuté, non prouvé ».
- Les résultats d'agents simulés ne valent ni homologation SSI ni validation par de vrais marins.
