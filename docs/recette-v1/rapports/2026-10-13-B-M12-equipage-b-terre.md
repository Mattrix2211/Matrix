# Passage B — M12 — Chef de secteur équipage B à terre (compte `chef_secteur_b`, agent `marin-complementaire`)

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette`, rejouée avant la mission |
| Navigateur | Chromium headless, 1366×768, serveur MCP `playwright`, session fermée avant |
| Date | 2026-10-13 |
| Exécuté | Mission M12 par `marin-complementaire` (profil : chef de secteur Moteurs équipage B, à terre, copié de `personas-comptes.md`) |
| Durée mesurée par l'outil (agent entier, 31 appels d'outils) | 82,4 s |

Compte rendu du marin, tel que reçu (captures `M12-*.png` dans `captures/` ou `/tmp/matrix-recette/navigateur/`).

---

COMPTE RENDU M12 – Ivan, chef de secteur Moteurs, équipage B à terre (compte chef_secteur_b)

RÉUSSITE : OUI, avec réserves.
- J'ai retrouvé le sujet et répondu. Deux fils m'attendaient, et la mission ne dit pas lequel est « le sujet ». J'ai répondu aux deux.
- Le reste du secteur n'a pas pu être traité : toute action de gestion est bloquée par la lecture seule, ce qui est cohérent avec la période à terre.

CHEMIN (écran par écran)
1. Connexion : champs « Utilisateur » et « Mot de passe », bouton « Se connecter ».
2. Accueil « Aujourd'hui » : bandeau « Lecture seule — Équipage B à terre » et titre « Bonjour Second-maître Chef Secteur B ». Pastille de 5 notifications non lues. Blocs « À faire », « Supervision » (tout à 0 « Conforme »), « Retards de l'équipe » (aucun) et « Validations en attente » (rien).
3. Clic sur la cloche : panneau « Notifications » avec 5 entrées. Deux m'ajoutent à un dossier :
   - « Jade Chef Section A vous a ajouté à « Fuite persistante sur un graisseur » » (/demandes/1/).
   - « Jade Chef Section A vous a ajouté au fil de la tâche « Remplacer le filtre du circuit d'huile » » (/taches/2/).
4. Demande bord–terre « Fuite persistante sur un graisseur » (/demandes/1/) :
   - Contenu : statut « En traitement », responsable Jade Chef Section A, « Interlocuteurs : Ivan Chef Secteur B ».
   - Mon message précédent : « Un joint équivalent est disponible au magasin de l'équipage B, je vous l'envoie. »
   - J'ai tapé mon avis dans « Répondre (citez un participant avec @identifiant) » puis cliqué sur « Publier ».
   - Mon message est apparu dans le fil, horodaté 19:02.
5. Tâche « Remplacer le filtre du circuit d'huile » (/taches/2/) : statut « Bloquée », motif « Filtre de rechange introuvable en magasin ». J'ai répondu dans « Répondre dans le fil » puis « Publier ». Je n'ai pas relu le fil après ce second envoi, donc je ne l'ai pas vérifié visuellement.
6. Page « Tâches » (/taches/) :
   - Section « Mes tâches » : « Aucune tâche à réaliser ».
   - Section « Suivi d'équipe et fils où je suis interlocuteur » : deux lignes, dont « [Recette] Relever les niveaux d'huile des lignes d'arbre » (Marc Marin B, 12/10, « En retard », « À faire »).
7. Tâche 10 : seul le fil de discussion est utilisable. Je n'ai trouvé ni bouton de réassignation, ni bouton de modification, ni bouton de création de tâche.
8. « Maintenance » (Gestion de la maintenance, Occurrences) : deux occurrences « Planifiée », non assignées (« — »). Les boutons « M'assigner », « Imprimer » et « Exécuter » sont affichés.
9. Clic sur « M'assigner » : page 403 « Accès refusé – Lecture seule : votre équipage est à terre, cette action est réservée à l'équipage à bord. » avec le lien « Retour à Aujourd'hui ».

MESURES
- Environ 10 actions de saisie ou de clic utiles.
- 8 écrans visités, environ 3 de plus que le minimum pour répondre.
- 0 retour en arrière, 3 accès directs par URL. Les adresses /demandes/1/ et /taches/2/ viennent des liens du panneau de notifications, mais je les ai saisies directement. Les pages /taches/10/ et /maintenance/gestion/occurrences/ ne figuraient dans aucun lien que j'avais suivi : /taches/10/ est listé sur /taches/, et la page Maintenance est dans le menu.
- Durée : non mesurée (environ 1 minute 30 d'après les horodatages).

HÉSITATIONS ET DÉTOURS
- Deux sujets possibles, donc deux réponses. Rien n'indique lequel est « l'avis demandé ». Dans les deux fils mon propre message figurait déjà, ce qui m'a laissé croire que j'avais déjà répondu.
- J'ai répété le même propos dans les deux fils, et rien ne me prévenait du doublon.
- Pour « le reste du secteur », je ne savais pas quoi faire en lecture seule.

TERMES AMBIGUS (verbatim)
- « Interlocuteurs » : je comprends « personnes à qui l'on parle », sans en être sûr.
- « Lecture seule » : le bandeau ne dit pas que les réponses dans les fils restent possibles.
- « Suivi » (type d'entrée dans le fil) : compris, mais le mot est vague.
- « Actions décidées » : « Aucune action pour l'instant », sans indication de la façon d'en décider une.

RETOUR DU SYSTÈME
- Après « Publier », le message apparaît dans le fil avec l'heure, mais je n'ai vu aucun message de confirmation explicite.
- Le refus 403 est clair et compréhensible : il donne la raison (équipage à terre) et un lien de retour.
- Les boutons restent affichés alors qu'ils sont inutilisables : « M'assigner », « Exécuter ». Je clique, puis je reçois un refus. Ils devraient être grisés ou masqués.
- Incohérence : le bloc « Avancement de l'équipe » indique « Bloquées 0 », alors que le tableau juste en dessous liste la tâche « Remplacer le filtre du circuit d'huile » en « Bloquée ». Ce même bloc affiche « Charge par marin : Marc Marin B ».
- Le tableau de bord d'accueil affiche « 0 retard » et « Aucun retard / Toutes les maintenances de votre périmètre sont à jour », alors que la page « Tâches » signale une tâche en retard. Les deux ne comptent pas la même chose (maintenances contre tâches), mais l'accueil donne une impression trompeuse de tout va bien.

PEUT-ON CORRIGER UNE ERREUR ?
Je n'ai trouvé aucun moyen de modifier ou supprimer un message publié, ni aucun bouton pour cela. Ce point est à vérifier côté équipe : si mon doublon est une erreur, je ne peux pas le retirer.

DROITS CONSTATÉS
- Possible et cohérent : lire les dossiers où je suis interlocuteur, répondre dans les fils (demandes bord–terre et tâches), même à terre.
- Bloqué à juste titre : « M'assigner » (403 « Lecture seule »).
- À signaler : la réponse en fil est autorisée en lecture seule. C'est probablement voulu (le dialogue est une fonction métier), mais le bandeau ne le dit pas.
- Je n'ai pas testé « Exécuter ». Je n'ai pas testé non plus les menus « Paramètres » (Administration), « Quarts et gardes », « Formations » ni « Absences », donc je ne peux rien dire de leurs droits.
- La liste des tâches de l'équipage B s'affiche en consultation, ce qui est normal pour un chef de secteur.

AVANTAGE PERÇU FACE AU PAPIER OU EXCEL
Oui : la notification m'a mené en un clic au dossier, et le fil garde tout l'historique (qui a signalé quoi, statut, mon message précédent). Par e-mail ou sur papier, je n'aurais pas ce contexte. Le point faible est de ne pas savoir quel fil est « la question ».

VERBATIM D'IVAN
« Les notifications m'ont tout de suite orienté. En revanche, quand on me dit de m'occuper du reste de mon secteur et que tout est grisé, je voudrais que ce soit écrit dès le départ, et qu'on n'affiche pas des boutons sur lesquels je ne peux pas cliquer. »

CAPTURES : M12-accueil.png, M12-notifications.png, M12-reponse-demande.png, M12-assigner-403.png

---

## Évaluation coordinateur

- Réussite attendue (réponse dans le fil ouvert à l'équipage B) : **Réussi** — message visible dans le fil de la demande (compte rendu). La seconde réponse (tâche) n'a pas été relue : **Exécuté, non prouvé**.
- Frontière (autres écritures refusées, bandeau « Lecture seule ») : bandeau « Lecture seule — Équipage B à terre » **observé** ; « M'assigner » refusé en 403 avec message clair : **conforme**. « Exécuter » et les autres écritures (création de tâche, absences, quarts…) : **Non testés**.
- Constats à classer : boutons d'écriture affichés mais refusés (incohérence/ergonomie, P2) ; compteur « Bloquées 0 » contradictoire avec le tableau (défaut technique ou périmètre de calcul, P2, **hypothèse**) ; accueil « 0 retard » alors que des tâches sont en retard (périmètre maintenance seul, libellé trompeur, P3) ; bandeau « Lecture seule » ne précise pas que le fil reste ouvert (libellé, P3) ; aucun moyen de retirer son propre message (fonction absente, à arbitrer).
