# Démonstration : parcours chef, marin et interlocuteur à terre

Version de démonstration avec données **entièrement fictives**. Elle n'est connectée à aucun système d'information de la Marine et ne constitue pas une solution homologuée.

## Préparer

```bash
python manage.py migrate
python manage.py seed_demo      # relançable sans doublon
python manage.py runserver
```

Tous les comptes ont le mot de passe « pass » (sauf `admin` : « admin »). Connexion sur `/login/`.

| Compte | Rôle fictif | Utilité |
|---|---|---|
| `chef_section_a` (Jade) | Chef de section, équipage A à bord | Attribue, suit, lève les blocages |
| `equipier_a` (Karim) | Équipier, équipage A | Reçoit et exécute une tâche |
| `equipier_a2` (Lina) | Équipier, équipage A | Tâche en retard et tâche bloquée |
| `chef_secteur_b` (Ivan) | Chef de secteur, équipage B à terre | Répond dans le fil, en lecture seule ailleurs |
| `admin` | Administrateur général | Réglages des tâches de la flotte |

## Scénario principal (une dizaine de minutes)

1. **Jade attribue une tâche** : page Tâches, formulaire « Attribuer une tâche » (titre, marin, échéance facultative, priorité).
2. **Karim la voit sans ressaisie** dans « Aujourd'hui » (bloc « À faire » et « Ma journée »), au calendrier le jour de l'échéance et dans ses notifications, avec un lien direct.
3. **Karim la démarre**, puis **signale un blocage** avec un motif obligatoire.
4. **Jade ajoute Ivan au fil** (interlocuteur du même navire, équipage à terre compris). Ivan répond dans le fil : c'est la seule écriture que sa situation de lecture seule autorise.
5. **Jade lève le blocage** une fois la solution donnée.
6. **Karim rend compte** : la tâche passe à « Terminée » et Jade est notifiée.
7. **Jade consulte l'avancement de l'équipe** (haut de la page Tâches) : répartition par statut, charge par marin, retards, blocages à lever et échéances tombant pendant une absence.

## Variantes à montrer

- **Réaffecter ou replanifier** : sur la fiche, le formulaire « Réaffecter ou replanifier » change le marin, l'échéance ou la priorité ; chaque changement est consigné dans le fil et dans le journal d'audit, l'ancien et le nouveau titulaire sont notifiés.
- **Tâche personnelle** : un marin se crée sa propre tâche, privée par défaut ; la case « Visible de mes chefs » la partage.
- **Relances** : une tâche en retard relance le marin et le chef qui l'a attribuée ; un blocage en retard relance les chefs du périmètre. Une relance lue ne supprime pas la suivante.
- **Réglages** : `admin`, Paramètres, onglet « Seuils de rôle » : niveau requis pour attribuer, rythme et destinataires des relances, durée d'affichage des tâches terminées.

## Données fictives créées

Quatre tâches pour la Bretagne : une à jouer en direct (Karim), une en retard (Lina), une bloquée avec fil ouvert à l'équipage B (Lina), une terminée (secteur électricité), plus une tâche personnelle privée de Karim et une permission de Karim le lendemain de l'échéance de sa tâche.

## Limites connues

- Les interlocuteurs d'une tâche sont limités au navire de cette tâche.
- Les réglages des tâches valent pour toute la flotte (pas de surcharge par navire ou secteur).
- Pas de pièces jointes, de checklist, d'attribution à une section entière ni de recherche universelle sur les tâches.
- La barre du haut et le menu latéral ne sont pas adaptés aux téléphones : l'application vise le poste fixe.
