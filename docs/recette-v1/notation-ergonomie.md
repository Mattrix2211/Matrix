# Méthode de notation de la praticité

Chaque mission reçoit une note par critère, de **0 à 4** (0 = bloquant, 2 = acceptable avec friction, 4 = naturel). Un critère non observable reçoit « n/o », jamais une valeur par défaut. Les notes d'agents simulés sont des **indications**, pas des mesures d'usage réel.

| # | Critère | 4 = | 0 = |
|---|---|---|---|
| 1 | Réussite réelle | Mission réussie seul | Impossible |
| 2 | Temps | ≤ référence papier/Excel déclarée par le Product Owner (à défaut : relatif entre personas) | Abandon |
| 3 | Actions et changements d'écran | Minimal, sans détour | Nombreux allers-retours |
| 4 | Hésitations | Aucune | Perte d'orientation |
| 5 | Compréhension des termes | Vocabulaire du persona | Termes incompris |
| 6 | Visibilité de l'action principale | Immédiate | Introuvable |
| 7 | Messages de confirmation | Dit ce qui s'est passé et la suite | Silence ou ambigu |
| 8 | Correction d'erreur | Annuler/modifier simple, tracé | Impossible |
| 9 | Conservation du contexte | Retour au même endroit, valeurs gardées | Ressaisie |
| 10 | Intérêt opérationnel | Gain net sur papier/Excel | Plus lourd |

**Score de mission** = moyenne des critères observés. **Alertes** : critère 1 = 0 sur une mission P1, ou critère 6 ≤ 1, ou toute fuite de droit = remontée immédiate à l'observateur.

## Grille des principes UX (benchmark ClickUp, Asana, eBrigade, Mattermost)

Notée par l'observateur et `qa-ergonomie`, 0 à 4 par principe, avec une preuve par note : action avant statistiques · navigation stable · dévoilement progressif · discussion attachée à l'objet · saisie une fois / réutilisée partout · peu de ressaisies · cohérence visuelle stricte · états et responsabilités compréhensibles · dense mais calme. On adapte les bonnes pratiques au design system existant : on ne cherche pas à ressembler à ces outils.

## Partie « expert » (qa-ergonomie)

1366×768 sans débordement horizontal, focus visible, contrastes, impression A4, mode sombre, poids/temps de page sur poste modeste, aucune ressource externe : chaque point **Réussi / Échoué / Non testé / Impossible à vérifier**, avec preuve.
