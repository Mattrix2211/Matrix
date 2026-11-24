# Parcours de recette utilisateur V1.1 (Windows et iPhone)

Principe : jouer une semaine de vie d'un bâtiment, avec plusieurs profils, sur la **démonstration fictive** (comptes et données inventés, base séparée de la base de développement). Rien n'est à saisir de réel. Les résultats se notent dans la grille de fin de document.

## 1. Préparer la démonstration isolée

**Sur le poste Windows (une seule machine, adresse locale uniquement)**

1. Une seule fois : `setup.bat` (crée l'environnement Python et installe les dépendances).
2. Lancer : double-clic sur `lancer_demo.bat`. La base absente est créée avec les données fictives ; une base présente est mise à jour sans rien supprimer.
3. Ouvrir `http://127.0.0.1:8800/` dans Edge ou Chrome.
4. Mots de passe générés (aléatoires, jamais affichés au lancement) : `python scripts\preparer_instance_test.py --identifiants`. Ne les recopiez dans aucun document partagé.
5. Repartir de données neuves entre deux séances : `python scripts\preparer_instance_test.py --reinitialiser` (n'efface que la base de démonstration).
6. Arrêt : Ctrl+C dans la fenêtre du serveur.

Contrôle d'isolation avant de commencer : `python scripts\preparer_instance_test.py --verifier` (confirme que la base visée est bien celle de démonstration). Les commandes de génération de données refusent de s'exécuter sur une autre base.

**Sur iPhone : point à décider (non fourni en l'état)**

La démonstration n'écoute que sur `127.0.0.1` : l'iPhone ne peut pas l'atteindre. Trois voies, de la plus simple à la plus réaliste :

| Voie | Principe | Limite |
|---|---|---|
| A. Simulation sur le poste | Mode appareil du navigateur (largeur iPhone) | Ne remplace pas Safari iOS : rendu, clavier, zones tactiles et défilement à vérifier sur un vrai appareil |
| B. Réseau local temporaire | Serveur lié à l'adresse du poste sur le Wi-Fi privé, l'adresse ajoutée à `DJANGO_ALLOWED_HOSTS`, pare-feu Windows en profil privé, arrêt après la séance | Nécessite une configuration à la main hors dépôt ou une petite évolution du script ; exposition limitée à votre réseau, données fictives seulement ; jamais depuis Internet |
| C. Rien sur iPhone | Recette poste Windows seule, iPhone en recette ultérieure | iPhone et Safari restent « non vérifiés » |

Recommandation : A pour la séance, B pour la vérification Safari si vous l'autorisez (je ne l'ai pas préparée). Safari, Firefox, iPhone et lecteur d'écran n'ont **pas** été exécutés à ce jour ; ils ne doivent pas être déclarés conformes avant votre passage.

## 2. Comptes à utiliser

Les identifiants sont ceux de `docs/recette/01_COMPTES.md` ; les mots de passe viennent de la commande ci-dessus. Utilisez un profil de navigateur distinct par compte (ou une fenêtre privée) pour passer de l'un à l'autre rapidement.

| Rôle | Compte | Sert à |
|---|---|---|
| Matelot | `equipier_a` | Journée du marin |
| Matelot BSC | `equipier_a2` | Rédaction de la feuille de service |
| Chef de section | `chef_section_a` | Visibilité d'une section |
| Chef de secteur et de liste | `chef_secteur_a` | Valider un échange, activer une liste |
| Chef de service | `chef_service_a` | Désigner les chefs de liste, valider les absences |
| COMAEQ | `coma_comaeq` | Publier, viser |
| Commandants adjoints | `coma_comanav`, `coma_comops` | Écriture bornée à leurs services |
| Commandant / second | `cdt_a`, `second_a` | Mouvements, supervision |
| Équipage B | `marin_b`, `chef_secteur_b` | Séparation des équipages |
| Administrateur | `admin_navire` | Archivage, suppression, configuration |
| Auguste Bénébig (quai) | `cdt_abe`, `chef_liste_abe`, `historique_abe` | Activation anticipée, désignation à qualifier |
| Jacques Chevallier (mer) | `cdt_jch`, `comaeq_jch`, `chef_liste_jch` | Activation seulement après accostage |

## 3. Scénarios (chacun : situation, actions, résultat attendu)

**S1 — Prendre son service (matelot, 10 min).** Connexion `equipier_a`. Lire l'accueil : « À faire », « Ma journée », prochains tours, alerte prioritaire. Ouvrir les menus, utiliser la recherche (un marin, un matériel, une fiche). Attendu : tout est lisible sans formation, aucune page vide ou en erreur, la recherche ne montre que ce que je peux voir. *iPhone : menu latéral, recherche, lisibilité.*

**S2 — Une machine tombe en panne (maintenance et tickets, 15 min).** Matelot : ouvrir la fiche « Contrôle et graissage du treuil » (EPI, étapes, points de contrôle), la réaliser, signaler une anomalie par l'assistant en quatre étapes (observer la bannière de brouillon à l'étape 4 : ANO-010). Chef de secteur : suivre le ticket correctif, le replanifier depuis le calendrier. Attendu : le ticket arrive au bon responsable, le suivi est lisible, l'historique est conservé.

**S3 — Un échange de garde (tours de service et échanges, 15 min).** `equipier_a` accepte l'échange en attente (statut « en attente du chef de liste »). `chef_secteur_a` le valide ; ensuite `coma_comaeq` : peut-il aussi le valider ? Noter qui peut décider et qui est notifié (c'est l'arbitrage n° 4). Tenter un échange qui recouvre un quart futur : avertissement lisible. Attendu : les tours sont permutés, les deux marins notifiés.

**S4 — Publier une liste (feuilles de service, 20 min).** `equipier_a2` (BSC) rédige et propose la feuille de service ; `equipier_a` essaie de créer une feuille (refus attendu, 403) ; `coma_comaeq` vise et publie à titre prévisionnel ; `chef_secteur_a` active une liste, dont celle en conflit (refus « Activation bloquée », rien n'est modifié). Attendu : seuls les rédacteurs désignés écrivent, chaque étape est tracée.

**S5 — Mer et quai (15 min).** Bénébig (quai) : `chef_liste_abe` active une liste en avance (confirmation demandée), liste en retard : alerte et report motivé ; `historique_abe` n'a aucun droit tant que sa désignation n'est pas qualifiée, `cdt_abe` la qualifie. Chevallier (mer) : activation refusée à la mer, accostage par `comaeq_jch`, puis activation. Attendu : le mode mer ou quai se comprend d'un coup d'œil, les notifications du mode courant passent devant (arbitrage n° 7).

**S6 — Le calendrier et mes notifications (10 min).** `equipier_a` : calendrier du mois, mes événements retrouvés facilement ? (ANO-009), vue « Par jour » des quarts (ANO-008), panneau de notifications, « Tout marquer comme lu », icônes et regroupements par mode. Attendu : je retrouve vite ce qui me concerne.

**S7 — Qui voit quoi (droits, 20 min).** Comparer `equipier_a`, `chef_section_a`, `chef_secteur_a`, `coma_comanav`, `marin_b`, `cdt_abe` : ouvrir la même page (accueil, quarts, passation, maintenance) et noter ce que chacun voit. À regarder : la passation du chef de section (voit-il tout le bâtiment ? arbitrage n° 2), un adjoint qui déplace une occurrence d'un autre service dans le calendrier (arbitrage n° 6), l'équipage B en lecture seule, un autre bâtiment invisible. Attendu : aucun accès à ce qui ne vous concerne pas ; noter chaque doute plutôt que de le résoudre.

**S8 — Archiver et supprimer une unité (administrateur, 15 min, sur base jetable).** `admin_navire` : archiver un service qui porte encore des marins (refus avec explication), archiver puis réactiver un service vide, tenter de supprimer un bâtiment ou un service référencé (refus, rien n'est perdu), supprimer un service vide, tester la sélection groupée en administration (refus de toute la sélection, le message de succès est trompeur : le noter). Attendu : aucune donnée de marin n'est perdue ; les refus sont compréhensibles.

**S9 — Modules et anciens écrans (5 min).** Vérifier que les Rondes n'apparaissent plus (arbitrage n° 9) et qu'un module désactivé disparaît du menu (arbitrage n° 3).

## 3 bis. Parcours à ajouter au fur et à mesure des lots (décisions du 24/11/2026)

Ces scénarios ne sont **pas jouables avant la livraison du lot indiqué** ; aucun n'a été exécuté. Détail et critères : `docs/PLAN_LOTS_REPRISE.md`.

| Scénario | Lot | À vérifier |
|---|---|---|
| S10 — Administrateur sans autorité métier | L06 | L'administrateur ne peut ni valider un échange, ni publier une liste, ni se donner une fonction ; cumul avec une vraie fonction possible |
| S11 — Passation par échelon | L30 | Chef de section, de secteur, de service, adjoint, second et commandant lisent chacun leur périmètre ; équipage à terre consulte son périmètre ; partage ciblé |
| S12 — Délégation et suppléance | L08, L33 | Délégation limitée dans le temps, le module et les actions ; expiration et révocation ; suppléant du COMAEQ |
| S13 — Échange de garde complet | L10 | Demande, acceptation, contrôles, instruction par le chef de liste, validation COMAEQ ou délégué ; aucun effet avant validation |
| S14 — Module désactivé | L34 | Menu, recherche, accueil, calendrier, API, notifications fermés ; données intactes à la réactivation ; dépendances |
| S15 — Notifications à quai et à la mer | L35 | Table de classement, feuilles de service communes, jamais repliées : urgences, sécurité, actions, échéances, prochain quart, transition |
| S16 — Quarts et tours : vues personnelles | L24-Q | Vue personnelle par défaut au premier usage, préférence mémorisée, bascule collective soumise aux habilitations ; poste et iPhone |

## 4. Grille de résultat

Pour chaque scénario : ✅ conforme / ⚠️ gêne (décrire) / ❌ bloquant (décrire), environnement (Windows + navigateur, iPhone + Safari, simulation), profil utilisé, capture si utile. Un défaut observé n'est corrigé qu'après qualification ; toute remarque de droit ou de visibilité renvoie au sujet d'arbitrage correspondant.

## 5. Ce que cette recette ne remplace pas

Elle n'autorise ni fusion ni déploiement avec des données réelles. Les points de sécurité ouverts (A1 à A4, A14/NE-06, A25) et l'exploitation (sauvegarde, supervision, conservation) restent à traiter avant tout usage opérationnel.
