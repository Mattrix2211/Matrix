# Passage B — M18 — Administrateur de navire (compte `admin_navire`, agent `marin-complementaire`)

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette`, rejouée avant la mission |
| Navigateur | Chromium headless, 1366×768, serveur MCP `playwright`, session fermée avant |
| Date | 2026-10-13 |
| Exécuté | Mission M18 par `marin-complementaire` (profil : administrateur de navire Bretagne) ; consigne de nom fictif pour le nouveau marin |
| Durée mesurée par l'outil (agent entier, 64 appels d'outils) | 143,2 s |

Compte rendu du marin, tel que reçu, à une exception près : le mot de passe provisoire fictif du compte jetable créé est masqué (`[masqué]`). Captures `M18-*.png` dans `captures/`.

---

COMPTE RENDU M18, Paul (admin_navire), administrateur du navire Bretagne

MISSION : « Donne l'accès à un nouveau marin et règle ce qu'un chef peut faire, sans toucher à ce qui concerne un autre bâtiment. »

RÉUSSITE : OUI, avec un écart sur l'identifiant.
- Le marin « Test Recette » est créé (Équipier, Matelot, Bretagne, Équipage A, Service Propulsion). Un mot de passe provisoire est généré.
- Un seuil de rôle est modifié et enregistré.
- Je n'ai rien vu ni touché qui concerne un autre bâtiment.
- Écart : l'identifiant ne se choisit pas. Il est généré automatiquement (test.recette) et non recette_nouveau.
- Je n'ai pas testé la connexion du nouveau compte (hors mission, pas de second compte).

CHEMIN SUIVI (libellés exacts)
1. Connexion : champs « Utilisateur » / « Mot de passe », bouton « Se connecter ». Arrivée sur « Bonjour Admin Navire », profil « Paul Admin Navire, Administrateur d'unité ».
2. Menu latéral, section « Administration », « Annuaire ». Titre « Annuaire — 20 utilisateurs », bouton « Nouvel utilisateur ». Menu de ligne « ⋯ » (Actions sur …) avec Modifier / Réinitialiser le mot de passe / Supprimer.
3. « Nouvel utilisateur » (je suis allé à l'URL /users/nouveau/ au lieu de cliquer le bouton). Groupes « Identité », « Rôle et qualifications », « Rattachement ».
   - Premier essai : Prénom Test, Nom Recette, Rôle Équipier, Grade Matelot, Unité Bretagne, Service Propulsion, sans équipage. Bouton « Créer ». Retour à l'annuaire avec le message « L'équipage est obligatoire sur un bâtiment à double équipage. » Les champs saisis sont perdus et je dois tout ressaisir.
   - Second essai : Équipage « A » ajouté. Message « Utilisateur test.recette créé avec succès. » Annuaire passé à 21 utilisateurs.
4. Annuaire, « ⋯ » sur test.recette, « Réinitialiser le mot de passe ». Boîte de dialogue : « Un mot de passe provisoire sera généré et affiché une seule fois. Le marin devra le remplacer à sa prochaine connexion. » Bouton « Réinitialiser ». Page « Mot de passe provisoire » : « Notez ces mots de passe maintenant : ils ne seront plus jamais affichés… Communiquez-les de vive voix ». Tableau : Test Recette / test.recette / [masqué]. Lien « Retour à l'annuaire ».
5. Menu « Paramètres », puis « Seuils de rôle » (« Seuils de rôle — Bretagne », lien avec ship=2). Tableaux par domaine (Matériel mobile, Installations, Stock, Maintenance, Rondes, Tableau de bord, Discussions, Quarts, Feuille de service, Modules, Comptes, Annonces, Programme, Postes, Documentation, RETEX). Chaque ligne a une liste de rôles, un bouton « Enregistrer » et « Valeur par défaut ».
   - J'ai changé « Créer ou modifier une occurrence ou une exécution de maintenance » de Équipier à Chef de section, puis cliqué « Enregistrer ». Message « Seuil de rôle mis à jour. » La ligne affiche ensuite un bouton « Réinitialiser ».
6. Paramètres, « Utilisateurs » (« Effectifs par équipage » et « Relève — Bretagne »), consulté seulement.

MESURES
- Environ 30 actions (champs, sélections, clics, snapshots non comptés).
- Environ 12 changements d'écran.
- 0 retour arrière navigateur, mais 1 reprise complète du formulaire (équipage oublié) et plusieurs accès par URL directe.
- Durée : non mesurée.

HÉSITATIONS ET DÉTOURS
- Le formulaire de création est refusé pour une règle (équipage obligatoire) que rien n'annonce : le champ « Équipage » n'est pas marqué obligatoire, seul le placeholder « A, B… (double équipage) » le suggère.
- Je n'ai pas tout de suite compris où régler les droits d'un chef. Il faut deviner Paramètres, puis « Seuils de rôle ». Le menu « Utilisateurs et droits » ne contient que « Utilisateurs ».
- Le rôle par défaut du formulaire est « Administrateur d'unité » (le plus fort), ce qui est risqué en cas d'oubli.

TERMES AMBIGUS (verbatim)
- « Seuils de rôle » / « Seuil minimal requis » : on comprend « à partir de quel rôle », mais ce n'est pas dit.
- « Valeur par défaut » : affiché même sur les lignes que je n'ai pas modifiées, donc ambigu. Est-ce la valeur actuelle ou celle d'origine ?
- « Rattachement » (tableau et formulaire) : mélange unité, service, secteur.
- « Administrateur général » : proposé dans les listes de seuils, alors que mon rôle est limité à mon navire.

RETOUR DU SYSTÈME
- Confirmations claires : « créé avec succès », « Seuil de rôle mis à jour ».
- Le mot de passe provisoire est bien expliqué (affiché une fois, changement obligatoire).
- Message d'erreur utile sur le fond, mais perte des champs saisis et message affiché sur une autre page.
- Texte en bas de page : « Chaque modification est historisée (auteur, date, ancienne et nouvelle valeur) ».

CORRECTION D'UNE ERREUR
- Seuil : bouton « Réinitialiser » par ligne, donc OK.
- Utilisateur : « Modifier » et « Supprimer » existent dans le menu « ⋯ » (non testés).
- Le mot de passe provisoire ne peut pas être revu. Il faut le réinitialiser de nouveau s'il est perdu.

DROITS CONSTATÉS
- Je ne vois que Bretagne : annuaire (sélecteur d'unité « Toutes les unités / Bretagne »), formulaire de création (Unité : Bretagne seul), seuils (« Bretagne »). Aucun accès à Normandie, ce qui est correct.
- Le menu me donne « Flotte » et « Vue COMANAV » (Supervision), « Plan du navire » et « Configurer le plan du navire ». Je n'ai pas ouvert ces pages et je ne sais pas si elles débordent sur d'autres bâtiments. À vérifier par l'équipe.
- À signaler : le formulaire propose les rôles Commandant, Commandant en second et État-major. L'administrateur de navire peut donc créer des rôles de haut niveau.
- À signaler : les listes de seuils offrent « Administrateur général », qui ne relève pas de ma fonction.
- Aucune boîte de confirmation du navigateur n'a bloqué l'outil. Les confirmations sont des boîtes internes à l'application.

AVANTAGE FACE AU PAPIER/EXCEL
Oui, sur la traçabilité, la génération du mot de passe provisoire et l'historique des seuils. Le gain est moins net à la création, à cause du rejet pour l'équipage et de l'identifiant imposé.

VERBATIM (en tant que Paul)
« Créer le marin, c'est rapide une fois que j'ai compris qu'il fallait l'équipage. Régler ce qu'un chef peut faire, c'est puissant mais on ne le trouve que si on connaît déjà le mot "seuils de rôle". J'aurais aimé choisir moi-même l'identifiant. »

CAPTURES : M18-formulaire-creation.png, M18-apres-creation.png, M18-annuaire.png, M18-mdp-provisoire.png, M18-seuil-modifie.png (images non relues par le marin).

TRACES LAISSÉES : utilisateur test.recette créé (base jetable) ; seuil Bretagne « Créer ou modifier une occurrence ou une exécution de maintenance » passé de Équipier à Chef de section. Base réinitialisée après la mission.

---

## Évaluation coordinateur

- Réussite attendue (compte créé, droits réglés) : **Réussi** — message « Utilisateur test.recette créé avec succès. », annuaire de 20 à 21 utilisateurs, « Seuil de rôle mis à jour. ». La **connexion du nouveau compte** n'a pas été testée : **Non testée**.
- Frontière « aucun accès aux données de Normandie hors navire administré » : **conforme dans ce qui a été observé** (annuaire, formulaire de création et seuils limités à Bretagne). Les pages « Flotte », « Vue COMANAV », « Plan du navire » n'ont pas été ouvertes : **Non testé**.
- **À confirmer par test technique (hypothèse, signalement de périmètre de droits)** : l'administrateur de navire peut créer un utilisateur avec les rôles Commandant, Commandant en second, État-major, et voit « Administrateur général » dans les listes de seuils ; rôle par défaut du formulaire = « Administrateur d'unité » (risque d'erreur de saisie, P2). Décision métier : l'administration distribuée autorise-t-elle ces rôles ? À arbitrer par le PO.
- Constats : champ « Équipage » obligatoire non signalé et perte des champs saisis après rejet (défaut ergonomique, P2) ; identifiant imposé (P3, choix possible) ; modification de seuil tracée (« historisée ») mais l'entrée d'audit n'a pas été lue par le coordinateur.
