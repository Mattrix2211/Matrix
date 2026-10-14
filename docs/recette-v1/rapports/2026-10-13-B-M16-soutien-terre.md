# Passage B — M16 — Soutien à terre (compte `terre_classe`, agent `marin-complementaire`)

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette`, rejouée avant la mission |
| Navigateur | Chromium headless, 1366×768, serveur MCP `playwright`, session fermée avant |
| Date | 2026-10-13 |
| Exécuté | Mission M16 par `marin-complementaire` (profil copié de `personas-comptes.md` : soutien à terre, société de classification) ; `terre_securite` **non joué** |
| Durée mesurée par l'outil (agent entier, 24 appels d'outils) | 58,8 s |

Compte rendu du marin, tel que reçu (captures `M16-*.png` dans `captures/`).

---

COMPTE RENDU M16 – Tessa (Capitaine de corvette Tessa Terre Classe, affichée « Chef de service », compte terre_classe)

RÉUSSITE : PARTIELLE.
- Réponse à la demande : OUI. J'ai publié mon message dans le fil et il apparaît sous mon nom.
- « Consulter ce qui m'est destiné » : ambigu. Aucune demande n'est adressée à moi nommément. « À traiter » affiche « Rien n'attend votre réponse. » et « Mes signalements » affiche « Aucun signalement en cours ». Les deux demandes du bord sont dans « Dossiers suivis ». Le centre de notifications affiche « Aucune notification / Vous êtes à jour. » Je n'ai donc eu aucun signal m'avertissant de la demande. Je l'ai trouvée parce que je suis allée chercher dans « Demandes bord–terre ».
- « Modifier quelque chose à bord » : j'ai constaté que c'est possible, mais je n'ai rien modifié. Voir « Droits constatés ».

CHEMIN SUIVI
1. Connexion : champs « Utilisateur » et « Mot de passe », bouton « Se connecter ». Arrivée sur « Bonjour Terre Classe / Vue de la flotte ».
   - Bloc « À faire » : 2 lignes « En attente de validation » et 2 « Ticket bloqué : à commenter » avec un lien « Commenter ».
   - Bloc « Mes bâtiments » : Bretagne et Normandie.
2. Menu Activité > « Demandes bord–terre » (/demandes/). Sections : « À traiter » (vide), « Mes signalements » (vide), « Dossiers suivis » avec 2 demandes :
   - « [Recette] Garniture de rechange introuvable pour la pompe incendie » (Signalée par Julien Equipier A3, responsable Jade Chef Section A, état Ouvert)
   - « Fuite persistante sur un graisseur » (Signalée par Karim Equipier A, état En traitement). Je ne l'ai pas ouverte.
3. Clic sur la demande « Garniture… » (/demandes/2/). Sections visibles : « Dossier », « Actions décidées », « Fil de la demande ». Le fil contient le message de suivi automatique et celui de Jade (« Je fais la demande de pièce au magasin, je vous tiens informé. »). Formulaires visibles : « Répondre », « Assigner une action », « Ajouter un interlocuteur », « Confier à un autre responsable ».
4. Saisie de ma réponse dans « Répondre (citez un participant avec @identifiant) », puis « Publier ». Texte : « Bien reçu. Je lance la recherche de la garniture de 40 mm côté terre et je vous confirme un délai. » Le message s'affiche immédiatement dans le fil, à 19:25.
5. Lien « Sur : [Recette] Consigne de la pompe… » : j'ai ouvert /taches/11/ en tapant l'adresse, que j'avais lue dans le lien, au lieu de cliquer. C'est un écart de ma part. La page est identique à celle du lien. Puis retour arrière.
6. Clic sur « Notifications » dans la barre du haut : fenêtre « Aucune notification », lien « Voir tout ».

MESURES
- Environ 12 actions utiles : connexion 3, navigation 3, réponse 2, tâche 1, retour 1, notifications 1, plus des relectures d'écran.
- 5 changements d'écran : accueil, liste des demandes, demande 2, tâche 11, retour sur la demande 2.
- 1 retour en arrière.
- Durée : non mesurée.

HÉSITATIONS ET DÉTOURS
- L'accueil ne mène pas directement à la demande du bord. J'ai deviné qu'il fallait aller dans « Demandes bord–terre ».
- Je me suis demandé pourquoi la demande n'est pas dans « À traiter ».
- Je n'ai pas vérifié si Jade ou Julien ont été prévenus de ma réponse.

TERMES AMBIGUS
- « Dossiers suivis » : je ne sais pas pourquoi ces dossiers m'y sont affichés.
- « Interlocuteurs : aucun » : je ne comprends pas si je suis considérée comme participante.
- « Confier à un autre responsable », « Assigner une action » : on ne sait pas si ces actions engagent le bord.
- « Chef de service » sous mon nom : je suis à terre, sans navire de rattachement.
- « Proposer un RETEX » apparaît sur la demande et sur la tâche. Le terme n'est pas expliqué.

RETOUR DU SYSTÈME
- Publication : bonne confirmation visuelle, puisque mon message apparaît aussitôt dans le fil avec mon nom et l'heure. Aucun message explicite du type « envoyé ».
- Aucune erreur rencontrée.
- Les notifications sont vides, donc le système ne m'a pas signalé la demande.

CORRECTION D'UNE ERREUR
Je n'ai pas vu de bouton pour modifier ou supprimer mon message publié. Je n'ai pas testé plus loin. Je n'ai pas fait d'erreur à corriger.

DROITS CONSTATÉS (à examiner)
1. Sur la demande du bord (/demandes/2/), sans en être responsable ni interlocutrice, j'ai accès à tous ces formulaires :
   - « Assigner une action » (liste de marins du bord, échéance)
   - « Ajouter un interlocuteur »
   - « Confier à un autre responsable » (liste de chefs et commandants)
   Je n'ai pas cliqué sur ces boutons.
2. Sur la tâche du bord « [Recette] Consigne de la pompe… » (/taches/11/), j'ai accès à tous ces formulaires :
   - « Réaffecter ou replanifier » (changer le marin, l'échéance, la priorité, bouton « Modifier »)
   - « Ajouter un interlocuteur au fil »
   - « Joindre » (pièces jointes)
   - « Répondre dans le fil »
   Une personne de classification à terre peut donc réaffecter une tâche du navire et lui fixer une échéance. Je n'ai pas cliqué sur « Modifier ». Je signale que cela me semble dépasser le rôle d'appui à terre.
3. Menu visible pour mon compte :
   - « Configurer le plan du navire » (/assets/plan/)
   - « Paramètres » (Administration)
   - « Quarts et gardes », « Feuille de service », « Rondes », « Absences », « Formations », « Postes du bord »
   - « Prêt à appareiller », « Flotte », « Classes de navire »
   Je n'ai ouvert aucun de ces écrans, donc je ne sais pas si l'accès en modification est réel. Leur simple visibilité me semble large pour une fonction d'appui à terre.
4. L'accueil me montre en « À faire » des lignes « En attente de validation » (séparateur d'eau de cale, extincteurs) et des « Ticket bloqué : à commenter ». Je ne sais pas si ces validations relèvent de moi.
5. Rien n'était bloqué à tort sur ce que j'ai tenté : consulter la demande et y répondre.

AVANTAGE PERÇU FACE AU PAPIER/EXCEL
Le fil de discussion rattaché à la demande, avec le responsable et l'état visibles au même endroit, est plus clair qu'un échange de messages ou de tableaux. En revanche, l'absence de notification et la demande absente de « À traiter » font perdre cet avantage : je dois aller chercher l'information.

VERBATIM (Tessa)
« J'ai pu répondre facilement une fois la demande trouvée, mais personne ne m'a prévenue qu'elle existait. Et je m'étonne de pouvoir réaffecter une tâche du bord depuis la terre. »

CAPTURES : M16-accueil.png, M16-demande2.png, M16-reponse.png, M16-notifications.png. Remarque du marin : M16-reponse.png a été prise avant le rechargement de la page ; le message apparaît dans le snapshot ultérieur, à 19:25.

Aucune boîte de confirmation du navigateur n'a bloqué l'outil.

---

## Évaluation coordinateur

- Réussite attendue (réponse à la demande, documents diffusés consultés) : réponse **Réussie** (message visible dans le fil `/demandes/2/`) ; « documents diffusés » **Non testé** (le marin n'a pas cherché la documentation).
- **P0 potentiel à confirmer (non confirmé par le coordinateur)** : le compte de soutien à terre `terre_classe` voit, sur une tâche du bord (`/taches/11/`), le bloc « Réaffecter ou replanifier » avec le bouton « Modifier » et peut ouvrir « Assigner une action » / « Confier à un autre responsable » sur la demande du bord. Le critère de frontière attendu est « aucune modification de donnée du bord ». Le marin n'a **pas cliqué** : la possibilité réelle d'écrire n'est pas établie (formulaires visibles ≠ écriture autorisée). À confirmer par test technique (`qa-securite`).
- Notification : l'acteur à terre n'est pas prévenu (centre de notifications vide, demande classée « Dossiers suivis », pas « À traiter ») — fonction « circuit bord–terre » à valider avec le PO (défaut ou donnée de recette).
- Frontière « autre classe refusée » (`terre_securite`) : **Non testée**.
- Ergonomie : visibilité de nombreuses entrées de menu d'administration pour un acteur à terre (signalement répété).
