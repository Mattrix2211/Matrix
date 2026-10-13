# Passage B — M10 — Chef de liste (compte `chef_secteur_a`, agent `marin-complementaire`)

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette`, rejouée avant la mission |
| Navigateur | Chromium headless, 1366×768, serveur MCP `playwright`, session fermée avant |
| Date | 2026-10-13 |
| Exécuté | Mission M10 par `marin-complementaire` (profil : SM Hélène Roussel, chef de secteur Moteurs et chef de liste, copié de `personas-comptes.md`, sans accès à la page Notion) |
| Durée mesurée par l'outil (agent entier, 39 appels d'outils) | 115,2 s |

Compte rendu du marin, tel que reçu (captures `M10-*.png` dans `/tmp/matrix-recette/navigateur/`, non versionné).

---

COMPTE RENDU MARIN. Mission M10, SM Hélène Roussel, chef de secteur Moteurs, compte chef_secteur_a.

RÉUSSITE : PARTIELLE, proche de « non » pour la fin de la mission.
- Je n'ai pas pu faire contrôler la liste ni la rendre visible. Cause : les deux boutons qui ouvrent une confirmation du navigateur (« Proposer la publication » et « Supprimer le créneau ») sont restés bloqués. La boîte « Proposer cette liste pour publication ? » ne pouvait être ni acceptée ni refusée avec mes outils. C'est une limite de mon outil de navigation, pas forcément un défaut de Matrix. Je ne peux donc pas dire si la proposition de publication fonctionne.
- Je n'ai pas non plus pu traiter l'échange de quart (voir plus bas).

CHEMIN SUIVI
1. Connexion : champs « Utilisateur » et « Mot de passe », bouton « Se connecter ». L'écran d'accueil est « Bonjour Second-maître Chef Secteur A » (« Mon quotidien »).
2. Menu Activité > « Quarts et gardes » (/quarts/). L'écran « Quarts et services de garde » propose « Mes échanges », « Feuille de service » et « Créer une liste ». Sous « Mes listes de quarts », la liste « Quarts machine — semaine prochaine » (Machine avant, 19/10 au 25/10/2026) était déjà là, en BROUILLON. Je ne l'avais pas créée, mais elle est affichée « Créé par Hélène Chef Secteur A le 13/10/2026 à 18:57 ».
3. Ouverture de la liste (ouverte par URL /quarts/quart/1/ et non par clic). Elle porte le titre, le badge BROUILLON, le bouton « Proposer la publication », les compteurs « Créneaux 6 » et « Non affectés 1 À surveiller », et les onglets « Planning », « Historique » et « Paramètres ».
4. Menu Activité > « Absences » (ouvert par URL). Rubrique « Absences de mon équipe » :
   - Julien Equipier A3 : Permission du 16/10 au 16/10, validée.
   - Karim Equipier A : Permission du 14/10 au 15/10, validée.
   - Lina Equipier A2 : Permission du 12/10 au 14/10, validée.
   - Aucune absence ne tombe sur le 19 au 25/10, donc rien à contourner. Les lignes validées ont pourtant encore un bouton « Valider », ce qui est ambigu.
5. Retour sur la liste, bouton « Créneau ». Un panneau « Nouveau créneau » s'ouvre avec les champs Poste, Début, « Fin (facultatif — 4 h par défaut) », « Marin affecté (facultatif) » et Note, puis « Ajouter le créneau ». J'ai ajouté Machine avant, mercredi 21/10 00:00-04:00, Julien Equipier A3. Le compteur est passé à 7 créneaux. Aucun message de confirmation visible, seulement la mise à jour du planning.
6. Tentative d'affecter le créneau « Non affecté » du 20/10 20:00 : clic, puis double-clic sur « Non affecté ». Rien ne s'ouvre, je n'ai trouvé aucun moyen de choisir un marin pour un créneau existant. Il faudrait le supprimer et le recréer.
7. Clic sur la corbeille « Supprimer le créneau Machine avant » : la boîte de confirmation du navigateur « Supprimer ce créneau ? » est restée bloquée. Je n'ai pas supprimé, j'ai ouvert un nouvel onglet.
8. Clic sur « Proposer la publication » : même blocage avec « Proposer cette liste pour publication ? ».
9. Onglet « Paramètres » de la liste : seul réglage, « Durée par défaut d'un créneau : 4 h, appliquée quand la fin d'un créneau n'est pas saisie ».
10. « Mes échanges » (/quarts/echanges/) : « À traiter : Rien à traiter pour l'instant. », « En cours : Aucune demande en cours. », « Historique : Aucun échange terminé. » Aucune demande d'échange de quart de marin n'est visible, donc je n'ai pas pu simuler l'étape finale. Je n'ai pas cherché à faire la demande depuis un autre compte, ce que mon profil ne permet pas.

MESURES : environ 22 actions, environ 9 changements d'écran, 1 retour arrière. Plusieurs écrans ont été ouverts par URL après lecture du menu, ce qui n'est pas le comportement d'une vraie utilisatrice. Durée non mesurée.

HÉSITATIONS ET DÉTOURS
- Affecter un créneau déjà créé : aucun contrôle trouvé.
- Planning très incomplet pour une semaine de quarts : seulement 7 créneaux sur 3 jours. Jeudi, vendredi, samedi et dimanche sont vides. Je n'ai pas vu de moyen de générer ou de dupliquer des créneaux (modèle, semaine type). Chaque créneau se saisit à la main, ce qui est lent.
- Je n'ai pas trouvé où voir les qualifications requises par poste. Je n'ai pas ouvert « Postes du bord » ni « Formations », donc mon contrôle des qualifications n'est pas fait. Le formulaire de créneau ne montre aucun avertissement de qualification ni d'absence.

TERMES AMBIGUS
- « Non affectés … À surveiller » (carte de synthèse).
- « Proposer la publication » : qui valide ensuite ? Aucune indication.
- Bouton « Valider » encore présent sur des absences déjà « Validée ».
- « Poste » (Machine avant) est du texte libre. Je ne sais pas s'il correspond à un « Poste du bord ».
- Le badge BROUILLON n'explique pas qui voit quoi tant que la liste n'est pas publiée.

RETOUR DU SYSTÈME
- Pas de message de confirmation visible après « Ajouter le créneau », seulement le compteur qui passe à 7.
- Les confirmations « Supprimer ce créneau ? » et « Proposer cette liste pour publication ? » sont claires dans leur libellé.
- Aucun message d'erreur rencontré.

CORRECTION D'ERREUR : la suppression d'un créneau est possible après confirmation, mais je ne l'ai pas validée. Je n'ai trouvé aucun moyen de modifier un créneau existant (marin, horaire). L'onglet « Historique » existe, je ne l'ai pas ouvert.

DROITS CONSTATÉS
- Je peux créer et modifier le planning de mon secteur (Machine avant, Propulsion / Moteurs) : normal pour un chef de liste.
- Je vois aussi dans « Listes publiées de mon périmètre » le planning Propulsion et la garde de nuit Propulsion, et j'ai les menus Maintenance, Flotte, Prêt à appareiller et Paramètres (Administration). C'est large pour un chef de secteur, à confirmer. Je n'ai pas essayé ces écrans.
- Le sélecteur de marins du créneau propose Hélène Chef Secteur A, Jade Chef Section A, Karim Equipier A, Lina Equipier A2 et Julien Equipier A3 : le secteur seulement, pas d'autre équipage.
- Je ne sais pas si je pouvais publier moi-même la liste : le bouton dit « Proposer », pas « Publier ».

AVANTAGE PERÇU FACE AU PAPIER/EXCEL : une vue par jour avec les affectations et le compteur de créneaux non affectés est plus lisible qu'un tableau. Mais saisir les créneaux un par un est plus lent qu'Excel, on ne peut pas modifier un créneau, et rien ne m'aide à tenir compte des absences ou des qualifications à l'écran.

VERBATIM (en tant qu'Hélène) : « La liste était déjà là en brouillon, mais je ne peux pas affecter le créneau vide du mardi soir, et je ne vois nulle part si Julien a la qualification pour ce poste. Je n'ai aucun retour pour savoir si c'est contrôlé, ni par qui. Je ne sais pas si ma liste est partie. »

CAPTURES : M10-liste-brouillon.png, M10-affectation.png, M10-dblclick.png.

ÉTAT LAISSÉ : le brouillon contient 7 créneaux, dont 1 ajouté par moi (mercredi 21/10 00:00-04:00, Julien Equipier A3). Il n'est pas proposé à la publication.

---

## Évaluation coordinateur

- **Limite de l'outillage de campagne (pas un défaut avéré de Matrix)** : l'agent `marin-complementaire` (comme les autres `marin-*`) n'a pas l'outil `browser_handle_dialog`. Les deux actions protégées par une boîte `confirm()` du navigateur (« Proposer la publication », « Supprimer le créneau ») n'ont pas pu être menées à terme. Conséquence : **« proposer, contrôler, publier » : Non testé / Impossible à vérifier avec les outils disponibles**. Ce même blocage peut affecter toute autre mission comportant une confirmation navigateur. Action proposée pour une contre-passe : ajouter `mcp__playwright__browser_handle_dialog` aux outils des marins (décision hors périmètre de ce passage).
- **Échange de quart** : aucune demande d'échange n'existait dans le jeu de données de la mission (« Mes échanges » vide) ; le scénario « un marin te demande d'échanger » n'est donc **pas jouable** avec les données actuelles de `seed_recette` : **Non testé**.
- Réussite attendue (liste créée **manuellement**, contrôlée, publiée par un chef de liste habilité ; échange géré) : création manuelle **prouvée** (créneau ajouté, compteur 7) ; contrôle, publication, échange **Non testés**. Statut : **Échoué en partie / Non testé pour la publication et l'échange**.
- Frontière « aucune génération automatique de tours » : **conforme** (le marin ne trouve aucun moyen de générer ; il le signale comme absence). Publication réservée à la fonction chef de liste : **Non testée** (bouton « Proposer »).
- Constats à classer (hypothèses) : impossible de modifier/affecter un créneau existant (fonction manquante ou non découverte, P1–P2 pour le parcours « quarts » si confirmé) ; aucun avertissement d'absence/qualification lors de la saisie d'un créneau (cohérent avec M08 : pas d'alerte de conflit) ; aucun message de confirmation après ajout de créneau ; « Valider » affiché sur des absences déjà validées (incohérence, P3) ; menu d'administration visible (signalement répété).
