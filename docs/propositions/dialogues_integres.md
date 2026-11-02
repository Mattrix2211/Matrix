# Proposition — système de dialogues intégrés

Statut : **proposition soumise au PO**, rien n'est encore remplacé.

## 1. Inventaire

Le chiffre de 38 relevé lors du premier audit comptait chaque fichier deux fois (deux dossiers de recherche
se recoupaient). L'inventaire réel est de **18 appels `confirm()`**, aucun `alert()` ni `prompt()` natif.
La suppression d'un événement du calendrier utilise déjà une modale Bootstrap : elle sert de référence.

| # | Écran | Action | Réversible ? | Classe |
|---|---|---|---|---|
| 1 | Plan du navire (liste) | Supprimer un pont | Non | Suppression nominative |
| 2 | Plan du navire (pont) | Retirer un matériel du plan | Oui (replacer) | Suppression légère |
| 3 | Fiche installation | Supprimer un document | Non | Suppression nominative |
| 4 | Modèle de ronde | Supprimer un point | Non | Suppression nominative |
| 5 | Programme | Annuler un événement | Difficilement (notifie) | Action sensible |
| 6 | Quarts · réglages | Retirer une désignation de chef de liste | Oui (redésigner) | Retrait de désignation |
| 7 | Quarts · liste | Supprimer un créneau | Non | Suppression nominative |
| 8 | Quarts · liste | Proposer / publier (message fourni par le serveur) | Publier : non (notifie) | Circuit |
| 9 | Quarts · liste | Republier avec corrections | Non (nouvelle version) | Circuit |
| 10 | Organisation · alerte | Valider et appliquer une modification | Non | Circuit |
| 11 | Organisation · alerte | Supprimer un scénario | Non | Suppression nominative |
| 12 | Feuille de service · réglages | Supprimer une rubrique | Non | Suppression nominative |
| 13 | Feuille de service · réglages | Supprimer une fonction | Non | Suppression nominative |
| 14 | Feuille de service | Ouvrir un rectificatif | Non | Circuit |
| 15 | Feuille de service | Resynchroniser la structure du brouillon | Non (écrase la structure) | Action sensible |
| 16 | Feuille de service | Proposer au premier visa | Via renvoi | Circuit léger |
| 17 | Feuille de service | Visa du chef de secteur | Non (visa signé) | Circuit |
| 18 | Feuille de service | Visa du chef de service / visa COMAEQ + publication | Non (visa signé, notifie) | Circuit |

(Les lignes 17 et 18 regroupent trois appels : visa chef de secteur, visa chef de service, visa COMAEQ.)

## 2. Un composant, quatre niveaux d'intensité

Une seule mécanique déclarative, un seul gabarit inclus une fois dans `base.html`, un seul script
`matrix/static/js/dialogues.js`. Le serveur reste seul juge des droits : la confirmation est une aide
d'usage, jamais une protection.

| Niveau | Usage | Rendu | Exemples de l'inventaire |
|---|---|---|---|
| **0 — Aucune confirmation** | Action simple et réversible | Exécution directe + notification discrète (toast) ; l'action se refait en un clic | 2, 6, 16 |
| **1 — Confirmation courte** | Action sensible mais claire | Modale centrée : titre, une phrase de conséquence, bouton principal nommé par le verbe (« Proposer »). Pas de double clic. | 5, 8, 9, 10, 14, 15 |
| **2 — Confirmation nominative** | Suppression définitive | Même modale, objet nommé en gras, bouton rouge « Supprimer », focus initial sur « Annuler » | 1, 3, 4, 7, 11, 12, 13 |
| **3 — Visa / signature** | Acte engageant avec traçabilité | Modale avec rappel de ce qui est signé (qui, quoi, version) et de la suite (notification). Focus sur le bouton principal. | 17, 18 |

Autres besoins de la demande, traités par les briques déjà en place :

- **Formulaire intégré (saisie courte)** : composant `modale` existant, contenu chargé par HTMX. Une erreur
  de validation ré-affiche le formulaire dans la modale, saisie conservée. Premier usage : motif de renvoi
  d'une feuille de service.
- **Notification de réussite** : messages Django déjà rendus en toasts ; ajout d'un évènement
  `HX-Trigger` pour les actions HTMX.
- **Erreur contextualisée** : message sous le champ concerné (`aria-describedby`, `role="alert"`), jamais
  un toast pour une erreur de saisie.
- **Panneau latéral** : composant `panneau_lateral` existant, quand l'utilisateur doit garder la page
  principale sous les yeux (gestion des rédacteurs, discussion, détail d'un évènement).

## 3. Interface de déclaration (niveaux 1 à 3)

```html
<form method="post" data-mx-confirmer="nominative"
      data-mx-titre="Supprimer le pont ?"
      data-mx-objet="{{ pont.name }}"
      data-mx-consequence="Les matériels placés sur ce pont seront retirés du plan."
      data-mx-action="Supprimer">
```

- Le texte est posé en attributs HTML (échappés par Django) : fin des chaînes injectées dans du JavaScript,
  donc plus de risque avec les apostrophes et les guillemets.
- Le script intercepte `submit`, ouvre la modale, puis soumet le formulaire d'origine à la validation.
- Annuler ou Échap : rien n'est soumis, le focus revient sur le déclencheur.

## 4. Accessibilité et mobile

- Modale Bootstrap : focus piégé, Échap, `aria-labelledby` et `aria-describedby` renseignés.
- Focus initial : « Annuler » pour une suppression, bouton principal sinon.
- Touches : Entrée valide seulement si le bouton principal a le focus.
- Moins de 576 px : modale en plein écran, boutons empilés de 44 px minimum.
- Thème sombre : couleurs par variables uniquement. Mouvement réduit respecté.

## 5. Tests prévus

- Test de garde : aucun gabarit ne contient `confirm(`, `alert(`, `prompt(` ni `onsubmit="return`.
- Rendu de chaque déclencheur converti : attributs présents, droits inchangés (le bouton n'apparaît que
  si la vue l'autorise).
- Parcours navigateur (Playwright) : ouvrir, annuler, confirmer, Échap, clavier, mobile 390 px.

## 6. Questions pour le PO

1. Valider les niveaux affectés à chaque ligne, en particulier les trois suppressions de confirmation
   (lignes 2, 6, 16) remplacées par une exécution directe et une notification.
2. Faut-il un motif obligatoire pour l'annulation d'un événement du programme (ligne 5) ?
