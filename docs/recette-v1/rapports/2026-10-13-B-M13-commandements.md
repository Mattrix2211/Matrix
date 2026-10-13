# Passage B — M13 — Commandements (`cdt_a`, `cdt_b`, `second_a`, agent `marin-complementaire`)

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette`, rejouée avant la mission (les trois passages se succèdent **sans** remise à zéro entre eux : cdt_a, cdt_b, second_a) |
| Navigateur | Chromium headless, 1366×768, serveur MCP `playwright` |
| Date | 2026-10-13 |
| Exécuté | 3 exécutions de la mission M13 : Anne (`cdt_a`), Benoît (`cdt_b`), Cécile (`second_a`) |
| Durées mesurées par l'outil (agent entier) | cdt_a 62,6 s (22 appels) ; cdt_b 64,3 s (24 appels) ; second_a 90,2 s (35 appels) |

**Anomalie de procédure du coordinateur** : `browser_close` n'a pas été exécuté entre l'exécution de `cdt_a` et celle de `cdt_b`. Le marin cdt_b a donc trouvé le navigateur connecté sous `cdt_a`, s'est déconnecté (« Déconnexion ») puis s'est connecté en `cdt_b`. L'isolation de session n'est donc pas respectée pour le début de cette exécution ; le journal du serveur montre bien `POST /logout/` puis `POST /accounts/login/`. Le résultat reste exploitable pour les écrans vus après reconnexion. Le navigateur a été fermé avant `second_a` (connecté d'emblée, sans compte précédent).

Comptes rendus des marins, tels que reçus (captures `M13-*.png` dans `captures/` ou `/tmp/matrix-recette/navigateur/`).

---

## 1. Anne — `cdt_a`

Compte rendu M13 — Anne (cdt_a, équipage A, Bretagne)

RÉUSSITE : partielle.
- Consigne à tout l'équipage : publiée (annonce n°4). Je peux suivre qui l'a lue, mais personne n'avait encore lu au moment de mon test (voir ci-dessous).
- Relève : une relève vers l'équipage B était déjà proposée par moi. Je ne peux pas la valider moi-même, la validation revient au commandant de B. Je n'ai donc pas pu la conclure. Ce qui est de mon ressort : la proposition (déjà faite) et son annulation.
- Je n'ai pas pu savoir si « Générer la synthèse de passation » a fonctionné (voir ci-dessous).

CHEMIN (écran par écran)
1. Connexion : champs « Utilisateur » / « Mot de passe », bouton « Se connecter ».
2. Accueil « Bonjour Capitaine de frégate Cdt A » (« À faire », « Ma journée », supervision). Menu « Activité » > « Annonces ».
3. « Annonces » : deux annonces existaient déjà (« Exercice incendie jeudi 14 h » et « [Recette] Consigne : essai des pompes d'incendie vendredi »). Bouton « Publier une annonce ».
4. « Publier une annonce » : j'ai rempli Titre « Consigne : port du casque sur le pont » et un Message. Niveau : « Important ». Public visé : « Tout le bâtiment Bretagne ». Équipage (facultatif) : « Équipage A ». J'ai coché « Accusé de lecture requis (« J'ai pris connaissance ») ». Clic sur « Publier ».
5. Page de l'annonce /annonces/4/ : « Publiée par Anne Cdt A · pour Bretagne · équipage A · version 1 ». Section « Suivi de lecture » : « 0 accusé(s) · 0 lu(s) · 16 non lu(s) », avec la liste nominative des 16 marins, tous « Non lu ». Il y a aussi « Créer une tâche à partir de cette annonce », « Modifier… », « Archiver » et « Versions ».
6. Je suis allée voir « Quarts et gardes » (/quarts/) en cherchant la relève. Rien sur la relève : listes de quarts, « Mes échanges », « Feuille de service ». Détour inutile.
7. « Paramètres » (par le menu Administration), qui s'ouvre sur l'onglet Notifications. Rien sur la relève.
8. Onglet « Utilisateurs » (/parametre/?tab=equipage). Bloc « Effectifs par équipage » : A à bord, 17 marins ; B à terre, 3 marins. Bloc « Relève — Bretagne » : « Relève en attente : l'équipage B à bord, proposée par Anne Cdt A. L'équipage à bord reste inchangé tant que l'autre commandant n'a pas validé. » Boutons « Annuler ma proposition » et « Générer la synthèse de passation ». Rubrique « Synthèses de passation » : « Aucune synthèse : elle est créée automatiquement à chaque relève validée. »
9. J'ai cliqué sur « Générer la synthèse de passation ». La page s'est rechargée à l'identique : pas de synthèse listée, pas de message visible dans mon relevé. Je ne sais pas si l'action a marché. Je n'ai pas cliqué sur « Annuler ma proposition » : ce n'est pas ce qu'on me demande.

MESURES
- Environ 12 actions (connexion, 1 clic menu, 1 clic bouton, remplissage du formulaire en 5 champs, 1 clic Publier, 3 navigations, 2 clics sur les boutons de la relève).
- Environ 8 changements d'écran. Aucun retour en arrière avec le bouton Précédent.
- Durée : non mesurée.

HÉSITATIONS ET DÉTOURS
- La relève ne se trouve pas là où on la cherche. J'ai d'abord pensé aux « Quarts et gardes », puis à « Paramètres ». Elle est cachée dans Paramètres > Utilisateurs, sous « Relève — Bretagne ». Un marin ne la trouverait pas sans aide.
- « Tout l'équipage » n'existe pas comme choix. J'ai dû combiner « Tout le bâtiment Bretagne » avec « Équipage A ». C'est compréhensible mais pas évident. Je ne sais pas ce que donnerait « Tous les équipages » (l'équipage B est à terre).

TERMES INCOMPRIS OU AMBIGUS (verbatim)
- « Public visé » : ambigu avec « Équipage (facultatif) ».
- « Accusé de lecture requis » : le suivi affiche « 0 accusé(s) · 0 lu(s) · 16 non lu(s) ». La différence entre « accusé » et « lu » n'est pas expliquée.
- « Synthèses de passation » : je ne sais pas ce que contient une synthèse.

RETOUR DU SYSTÈME
- Publication : bon retour, car la page de l'annonce s'affiche aussitôt avec le suivi nominatif. Je n'ai pas vu de message de confirmation explicite du type « Annonce publiée ».
- Clic sur « Générer la synthèse de passation » : aucun retour visible, ni succès ni erreur. C'est un défaut de clarté.
- Pas de message d'erreur rencontré.

CORRECTION D'ERREUR
- Possible : le formulaire « Modifier » publie une nouvelle version, l'ancienne reste consultable. « Archiver » est disponible. « Annuler ma proposition » existe pour la relève.

DROITS CONSTATÉS
- Je vois et je peux publier une annonce pour tout le bâtiment ou pour un équipage. Je peux aussi créer une tâche depuis l'annonce.
- Je vois la liste nominative des lecteurs. Cela me paraît normal pour une commandante.
- Pour la relève, je ne peux pas valider ma propre proposition : l'autre commandant doit le faire. C'est cohérent.
- La page « Utilisateurs » m'affiche des « Effectifs par équipage » et une phrase renvoyant à l'administrateur de l'unité pour modifier l'équipage d'un marin, ce que je ne fais pas.
- Rien d'anormal ni de bloqué à tort constaté.

SUIVI DE LA PRISE EN COMPTE
- Je vois qui n'a pas lu (16 non lus, nominatif). Je ne vois aucun bouton de relance, d'alerte ou de rappel aux non-lecteurs. Pour relancer, je devrais passer par une tâche.
- La liste des 16 marins inclut Paul Admin Navire, qui est sans doute un administrateur et pas un marin à relancer.

AVANTAGE PERÇU FACE AU PAPIER/EXCEL
- Réel pour la consigne : un seul formulaire, une liste nominative des lus et non lus mise à jour, des versions conservées. Plus fiable qu'un affichage papier ou un mail.
- Faible pour la relève : l'état est clair, mais l'emplacement est caché et le retour des boutons est absent.

CAPTURES : M13-annonce.png (page de l'annonce n°4 avec le suivi de lecture). Pas de capture de la page de relève.

VERBATIM (en tant qu'Anne) : « J'ai pu passer ma consigne en deux minutes et je vois qui l'a lue, c'est bien. En revanche la relève, je ne l'aurais jamais trouvée dans "Paramètres", et quand j'ai cliqué pour la synthèse, il ne s'est rien passé que je puisse constater. »

---

## 2. Benoît — `cdt_b` (équipage B, à terre)

COMPTE RENDU M13 — Benoît, commandant équipage B (Bretagne), compte cdt_b

RÉUSSITE : NON. Je n'ai pas pu faire passer la consigne. Je n'ai pas non plus trouvé de moyen de faire ma part de la relève entre équipages.

Raison : l'application affiche partout le bandeau « Lecture seule — Équipage B à terre ». Sur l'écran Annonces, je n'ai trouvé aucun bouton pour créer ou publier une annonce. Je n'ai trouvé aucun suivi de qui a pris connaissance. Je n'ai trouvé aucun écran de relève.

CHEMIN SUIVI (libellés exacts)
1. http://127.0.0.1:8000/ : j'étais déjà connecté sous un autre compte, « Capitaine de frégate Anne Cdt A, Commandant ». Ce n'était pas cdt_b. J'ai cliqué sur « Déconnexion ».
2. Écran « Connexion » : champs « Utilisateur » et « Mot de passe », bouton « Se connecter ». Connecté avec cdt_b. Arrivée sur l'accueil « Aujourd'hui », « Bonjour Capitaine de frégate Cdt A ». C'est le même nom affiché que sous le compte précédent.
3. Annonces (/annonces/, saisi par URL alors que le menu « Activité > Annonces » existe) :
   - Bandeau « Lecture seule — Équipage B à terre ».
   - Titre « Annonces », filtre « Niveau » (Tous / Information / Important / Urgent).
   - Une seule annonce : « Important — Exercice incendie jeudi 14 h, 13/10/2026, Bretagne · Anne Cdt A », avec la mention « Accusé à donner ».
   - Aucun bouton « Nouvelle annonce » ou équivalent.
4. Détail de l'annonce (/annonces/1/) : « Publiée par Anne Cdt A · pour Bretagne · à partir du 13/10/2026 · version 1 ». Le texte est « Rassemblement pont principal, tenue de travail. » Un seul bouton : « J'ai pris connaissance ». Je ne l'ai pas cliqué, ce n'est pas ma mission. Je n'ai vu aucune liste ni compteur d'accusés de réception.
5. « Quarts et gardes » (/quarts/) : boutons « Mes échanges », « Feuille de service », « Chefs de liste ». « Aucune liste de quarts pour l'instant » et « Aucune liste de services de garde pour l'instant ». Rien sur la relève entre équipages.
6. « Demandes bord–terre » (/demandes/) : « Rien n'attend votre réponse. » et « Aucun signalement en cours. »
7. « Programme du bâtiment » (/programme/) : un seul événement, « Exercice incendie général 15/10/2026 16:00 ». Rien sur la relève.
8. Recherche « relève » : aucun résultat dans aucune catégorie.

MESURES : environ 12 actions, 8 changements d'écran. Aucun retour arrière. Durée non mesurée. J'ai ouvert plusieurs écrans par URL directe au lieu du menu.

HÉSITATIONS ET DÉTOURS : je ne savais pas où poster une consigne. J'ai pensé aux Annonces, mais elles sont en lecture seule. J'ai ensuite cherché la relève dans Quarts, Demandes bord–terre, Programme et la recherche, sans rien trouver.

TERMES INCOMPRIS OU AMBIGUS
- « Lecture seule — Équipage B à terre » : je n'ai pas compris si c'est un état temporaire ou si cela dépend de ma fonction. Le bandeau n'indique ni la cause ni le moyen de lever le blocage.
- « Accusé à donner » : mention ambiguë. Elle sert au destinataire et n'indique pas au publieur où voir les accusés.
- L'identité affichée « Cdt A » alors que je suis connecté en cdt_b.

RETOUR DU SYSTÈME : le bandeau de lecture seule est clair sur le fait que je ne peux rien modifier. Il n'explique pas quoi faire à la place. Je n'ai reçu aucun message d'erreur, car aucune action n'était proposée. Je n'ai rien pu tester côté confirmation.

CORRECTION D'ERREUR : non testable, je n'ai rien saisi.

DROITS CONSTATÉS
- Bloqué, à tort ou non : publier une annonce à tout l'équipage, et suivre les accusés de réception. C'est cohérent avec « à terre », mais le circuit à suivre pour passer une consigne n'est pas indiqué.
- Je vois « Configurer le plan du navire », « Annuaire » et « Paramètres » dans le menu, ainsi que « Valider » sur des maintenances, alors que je suis en lecture seule. Je n'ai pas vérifié si ces actions sont réellement possibles. Les boutons « Ouvrir » et « Valider » de l'accueil étaient affichés.
- Au départ, la session ouverte était celle d'un autre compte (cdt_a, « Anne Cdt A »). À signaler.

AVANTAGE FACE AU PAPIER/EXCEL : aucun pour cette mission. Sur papier, j'aurais affiché ou diffusé la consigne et fait émarger. Ici, je n'ai rien pu faire. L'accusé de réception côté destinataire existe (« J'ai pris connaissance »), mais je n'ai vu aucun suivi côté commandant.

CAPTURES : M13-annonces.png (écran Annonces, lecture seule).

VERBATIM (Benoît) : « Je suis commandant, je veux passer une consigne à tout l'équipage et voir qui l'a lue. L'application me dit seulement que je suis en lecture seule. Je ne sais pas si c'est normal parce que je suis à terre, ni à qui m'adresser. Pour la relève, je n'ai trouvé aucun écran. »

---

## 3. Cécile — `second_a`

COMPTE RENDU M13 — Cécile (second_a, commandante en second, Bretagne, équipage A)

RÉUSSITE : PARTIELLE.
- Partie 1 (consigne à tout l'équipage + suivi de prise en compte) : OUI. Annonce publiée, avec accusé de lecture requis et suivi nominatif visible.
- Partie 2 (« relève entre équipages, fais ce qui est de ton ressort ») : NON. Je n'ai trouvé aucune fonction « relève » ou « passation entre équipages ». Je n'ai donc rien fait de ce côté, et je ne peux pas dire ce qui relèverait de ma fonction.

CONNEXION : le navigateur n'était connecté à aucun compte. Connexion directe avec second_a / pass. Le profil affiche « Capitaine de corvette Cécile Second A, Commandant en second ».

CHEMIN SUIVI, écran par écran
1. Connexion, champs « Utilisateur » et « Mot de passe », bouton « Se connecter ».
2. Accueil « Bonjour Capitaine de corvette Second A » (Aujourd'hui). Il affiche 3 annonces « accusé requis » dans « À faire », dont 3 consignes déjà publiées par Anne Cdt A. Menu repéré : « Activité > Annonces ».
3. « Annonces » (/annonces/), atteint par saisie d'URL et non par clic menu, bien que le lien « Annonces » existe dans le menu. Bouton « Publier une annonce ».
4. « Publier une annonce » : Titre, Message, Niveau (Information / Important / Urgent), Public visé (Tout le bâtiment Bretagne par défaut, plus services, secteurs, sections), Équipage (facultatif : Tous les équipages par défaut / A / B), Visible à partir du, Visible jusqu'au, case « Accusé de lecture requis (« J'ai pris connaissance ») ».
   - Saisi : titre « Consigne : fermeture des sabords à la tombée de la nuit ».
   - Message : « À partir de ce soir, tous les sabords du pont inférieur sont fermés à la tombée de la nuit. Chef de quart : vérification en ronde. »
   - Niveau « Important », accusé coché. Public « Tout le bâtiment Bretagne » et Équipage « Tous les équipages » laissés par défaut. Clic « Publier ».
5. Page /annonces/5/ : « Publiée par Cécile Second A · pour Bretagne · à partir du 13/10/2026 · version 1 ». Section « Suivi de lecture » : « 0 accusé(s) · 0 lu(s) · 19 non lu(s) », avec la liste nominative des 19 autres personnes (équipages A et B, dont Marc Marin B) « — Non lu ». Autres éléments de la page : lien « Créer une tâche à partir de cette annonce », formulaire de modification (nouvelle version), bouton « Archiver », liste « Versions ».
6. Recherche de la relève : « Quarts et gardes » (/quarts/), qui contient des listes de quarts et de gardes, des liens « Mes échanges », « Feuille de service » et « Chefs de liste », mais aucune relève. J'ai ensuite ouvert « Mes échanges de service » (À traiter / En cours / Historique, tout vide), puis la recherche globale « relève » (0 résultat partout). Puis « Paramètres » (Utilisateurs, Modules, Notifications), « Programme du bâtiment » (un seul exercice), « Feuille de service > Réglages » et « Annuaire » (colonne Équipage A/B, sans action de relève). Rien d'utilisable pour une relève entre équipages.

MESURES : environ 22 actions (clics, saisies, navigations), dont 6 pour la consigne elle-même. Environ 12 changements d'écran. 0 retour arrière explicite. Durée non mesurée (environ 1 min 30 pour la consigne, d'après les horodatages). Environ 8 navigations par URL ou recherche pour chercher la relève.

HÉSITATIONS ET DÉTOURS : la consigne a été rapide et claire. Tout le détour vient de la recherche de la « relève », que je n'ai pas su localiser. Deux de mes tentatives de recherche ont échoué à cause d'une référence d'élément périmée, côté outil et non côté application.

TERMES AMBIGUS / INCOMPRIS (verbatim)
- « Public visé » et « Équipage (facultatif) » : on ne sait pas comment ils se combinent. Je suppose « Tout le bâtiment » + « Tous les équipages » = tout le monde.
- Les 3 annonces existantes ont des portées différentes, et rien ne dit clairement « tout l'équipage ».
- « Aucune liste n'est imposée par l'application : configurez ... propres à Bretagne (CLAUDE.md §6) » : jargon de développeur affiché à l'utilisateur sur Feuille de service > Réglages. Ce n'est pas du vocabulaire de marin.
- « None — Bretagne / Propulsion » et « Machine avant — ... » dans la liste des quarts : « None » est affiché tel quel.
- « Fonction affichée » / « Poste correspondant » : peu clair.

RETOUR DU SYSTÈME
- À la publication, redirection vers la page de l'annonce avec « version 1 », mais aucun message de confirmation explicite du type « Annonce publiée ».
- Le suivi de lecture est très clair (accusés / lus / non lus, par nom).
- Aucune notification d'envoi n'est visible. Je n'ai pas pu vérifier si les destinataires sont prévenus.
- Pas d'erreur rencontrée.

CORRECTION D'UNE ERREUR : possible. La page propose « Publier la nouvelle version », avec ancienne version conservée dans « Versions », et « Archiver ». Je n'ai pas testé ces actions. Il n'y a pas de bouton « Relancer les non-lus » visible.

DROITS CONSTATÉS
- Je peux publier une annonce à tout le bâtiment, y compris à l'équipage B, depuis un compte d'équipage A. C'est cohérent avec la mission.
- La liste « Suivi de lecture » montre les noms de tous les utilisateurs, y compris Paul Admin Navire et les commandants.
- Je n'ai constaté aucun droit manifestement excessif ni blocage à tort.
- « Quarts et gardes » dit « Vous n'êtes désigné(e) chef de liste sur aucun périmètre ». Je ne peux donc pas gérer les listes de quarts. Je ne sais pas si la relève devrait venir de là.
- Menu « Administration » : « Annuaire » (avec export Excel) et « Paramètres » (Utilisateurs, Modules, Notifications) visibles.
- Pour la relève, je ne peux affirmer ni blocage à tort ni absence de fonction. L'interface ne m'a rien proposé.

AVANTAGE PERÇU FACE AU PAPIER/EXCEL : oui pour la consigne. Un seul formulaire, un public ciblable, un accusé de lecture et un suivi nominatif remplacent une feuille d'émargement. C'est mieux que le papier. En revanche, rien ne permet de relancer les non-lus, et le suivi ne prouve pas l'exécution (l'écran le dit lui-même et propose de créer une tâche).

CAPTURES : M13-accueil.png, M13-annonce-publiee.png. Pas de capture pour la partie relève.

VERBATIM (Cécile) : « Pour la consigne, j'ai trouvé tout de suite et je vois qui a lu. Pour la relève entre équipages, je n'ai rien trouvé dans le menu qui porte ce nom. J'ai cherché « relève » partout, sans résultat. Je ne sais pas si ça n'existe pas ou si ça se nomme autrement. »

---

## Évaluation coordinateur

- **Consigne avec accusés suivis** : **Réussi** pour `cdt_a` (annonce 4, 16 non lus nominatifs) et `second_a` (annonce 5, 19 non lus nominatifs) ; **Échoué (attendu)** pour `cdt_b` : écriture refusée sous « Lecture seule — Équipage B à terre » (cohérent avec le critère de frontière, mais le parcours de substitution n'est pas signalé).
- **Relève validée par les autorités des deux équipages** : **Non testée / Échoué** — `cdt_a` a trouvé une relève en attente proposée par lui (Paramètres › Utilisateurs › « Relève — Bretagne »), `cdt_b` (autorité de validation attendue) **n'a trouvé aucun écran de relève** dans ses menus ; la validation côté B n'a donc pas pu être exécutée par un marin. `second_a` n'a rien trouvé non plus (recherche « relève » : 0 résultat). **Fonction difficile à découvrir** (cachée dans Paramètres) pour A ; pour B, **introuvable avec le compte utilisé** (hypothèse : l'écran existe mais n'est pas exposé, ou n'est pas visible sous lecture seule — à confirmer par test technique).
- **Synthèse de passation conforme au paramétrage** : le clic « Générer la synthèse de passation » n'a produit aucun retour visible (ni succès ni erreur) ; la liste « Synthèses de passation » est restée vide : **Impossible à vérifier** par le marin. Point d'arbitrage PO existant (`personas-comptes.md`, écart 1) : la synthèse est-elle voulue ?
- Frontière « Second : vision globale, écritures limitées » : `second_a` a publié une annonce à tout le bâtiment (tous équipages) et voit 19 destinataires nominatifs : **à valider par le PO** (écriture non limitée sur ce périmètre ?). `second_a` n'est pas chef de liste (« aucun périmètre ») : cohérent avec les critères.
- **P0 potentiel à confirmer (non confirmé)** : l'accueil de `cdt_b` a affiché « Bonjour Capitaine de frégate Cdt A » immédiatement après une déconnexion de `cdt_a` et une connexion de `cdt_b`. Le compte `cdt_b` s'appelle bien « Benoît Cdt B » en base (lecture seule de la table des comptes) et les écrans suivants affichaient les droits de B (« Lecture seule — Équipage B à terre », une seule annonce). Hypothèses : cache d'affichage/contenu mis en cache entre deux comptes, ou artefact de session. **À confirmer par test technique** (fuite d'identité entre sessions = P0 si avérée).
- Constats supplémentaires (hypothèses) : « None » affiché dans la liste des quarts (même défaut que M08) ; jargon développeur « CLAUDE.md §6 » affiché à l'utilisateur sur Feuille de service › Réglages (libellé, P2–P3, contraire au principe « zéro jargon ») ; menu d'administration visible pour les profils de commandement (probablement légitime).
