# Tests d'utilisabilité avec des marins — guide d'animation

Objectif : vérifier que la tranche 1 de l'interface (menu, accueil, carte « À faire », calendrier, accès limité de l'équipage B) se comprend sans explication. Le test porte sur l'application, pas sur le marin. **Données exclusivement fictives.** Séances coordonnées par le Product Owner.

## 1. Démarrer la démonstration (procédure courte)

> **Poste local ou isolé uniquement.** Mots de passe fictifs (« pass ») et mode DEBUG actif : ne jamais exposer l'instance sur un réseau opérationnel ou accessible de l'extérieur. Elle n'écoute que sur ce poste (`127.0.0.1`) et ne peut pas être ouverte à d'autres appareils.

Dans un terminal, à la racine du projet, environnement virtuel du projet activé (sous Windows : `venv\Scripts\activate`) :

1. **Première fois** : `python scripts/preparer_instance_test.py`
2. **Lancer** : `python scripts/preparer_instance_test.py --servir`, puis ouvrir `http://127.0.0.1:8800/` dans le navigateur.
3. **Entre deux participants** : arrêter (Ctrl+C), `python scripts/preparer_instance_test.py --reinitialiser`, puis relancer l'étape 2.
4. **Arrêter** : Ctrl+C dans le terminal.

Si le script affiche « Refus : … », ne rien contourner : le message dit quelle condition de sécurité manque. `python scripts/preparer_instance_test.py --verifier` contrôle la configuration sans rien écrire.

Garanties (vérifiées par des tests automatiques) :

- La commande `--servir` réutilise exactement l'environnement isolé de la préparation : base SQLite choisie explicitement et vérifiée, `.env` du poste ignoré, e-mails sans envoi réel, tâches en arrière-plan gardées dans le processus (aucun Redis du poste n'est joint, même local), fichiers téléversés rangés dans `instance_test_marins/media`, aucune variable du poste transmise (bases, serveur d'e-mail, Redis, clés), hôtes limités à `localhost` et `127.0.0.1`. Elle écoute sur `127.0.0.1` seulement (l'hôte n'est pas configurable) ; seul le port peut changer (`--port`).
- Avant de démarrer, le script interroge la configuration réellement chargée et **refuse** si la connexion ne vise pas la base attendue, si un envoi réel d'e-mails ou de notifications est possible, si un Redis ou un autre service est configuré pour les tâches, si les hôtes autorisés ne sont pas locaux, ou si la base n'a pas été préparée par lui.
- Seul un fichier `.sqlite3` placé directement dans `instance_test_marins/` est accepté ; la base de développement `db.sqlite3`, les autres dossiers, les liens symboliques et les dossiers sont refusés. `--reinitialiser` ne supprime qu'un fichier créé par le script (fichier voisin `<base>.instance_demo`). Une base créée par une ancienne version n'a pas ce marqueur : la supprimer à la main avant de relancer.
- Ne lancez pas `manage.py runserver` à la main pour la démonstration : seule la commande `--servir` applique toutes ces protections.

**Essais sur PC uniquement.** Cette instance convient aux essais sur le poste local. Elle n'est pas joignable depuis un iPhone ou un autre appareil, et ne doit pas être rendue accessible : les essais sur appareil mobile réel demandent un environnement de validation distinct, isolé et approuvé, avec données fictives (voir `docs/COMPATIBILITE_CHECKLIST.md`). Sans tel environnement, le contrôle mobile est marqué « non effectué ».

Mot de passe fictif de tous les comptes : « pass ».

| Profil joué | Compte | Particularité |
|---|---|---|
| Marin, nombreuses actions | `equipier_a` | 10 actions dont 5 prioritaires |
| Marin, peu d'actions | `equipier_a2` | une tâche en retard |
| Marin, rien à faire | `equipier_nor` | liste vide (scénario 7) |
| Chef de secteur | `chef_secteur_a` | supervision, équipe |
| Équipage B en accès limité | `chef_secteur_b` | bandeau d'accès limité (le compte reste rattaché à son bâtiment : le présenter comme « équipage B en repos ») |

Matériel : poste 1366×768 (clavier et souris), chronomètre, grille imprimée. Navigateur : celui du poste. Le scénario 2 sur téléphone n'est réalisable que dans un environnement mobile approuvé (voir plus haut) ; sinon il est marqué « non effectué ».

## 2. Consignes de l'animateur

- Lire : « Nous testons l'application, pas vous. Pensez à voix haute. Je ne vous aiderai pas, sauf si vous êtes bloqué plus de deux minutes. »
- **Ne pas guider** : ne pas nommer les boutons, ne pas montrer. Si un participant est bloqué, noter « avec aide » et l'indice donné.
- Ne pas défendre l'interface. Noter les mots exacts utilisés par le marin.
- Arrêter immédiatement si une information réelle (non fictive) apparaît à l'écran.

## 3. Scénarios

| # | Consigne dite au participant | Compte | Durée max |
|---|---|---|---|
| 1 | « Retrouvez la tâche *Préparer mon dossier de formation incendie*. » | `equipier_a` | 3 min |
| 2 | « Dites-moi ce qui est le plus important à traiter aujourd'hui, et pourquoi. » | profil joué | 3 min |
| 3 | « Trouvez vos prochains quarts, puis vos demandes en cours. » | profil joué | 3 min |
| 4 | « Allez au calendrier et dites ce que vous avez cette semaine. » | profil joué | 3 min |
| 5 | « Fermez, puis rouvrez, la partie du menu que vous n'utilisez pas. » | profil joué | 2 min |
| 6 | « Que pouvez-vous faire, et que ne pouvez-vous pas faire, avec ce compte ? » | `chef_secteur_b` | 3 min |
| 7 | « Votre liste est vide : qu'en déduisez-vous ? » | `equipier_nor` | 1 min |

## 4. Répartition par profil (séances de 20 à 30 minutes)

Chaque séance : accueil et consigne (3 min) + scénarios (12 à 15 min) + questions finales (5 min).

| Séance (profil) | Scénarios |
|---|---|
| A — Marin, nombreuses actions (`equipier_a`) | 1, 2, 4, 5 |
| B — Marin, peu d'actions (`equipier_a2`, puis `equipier_nor`) | 3, 4, 5, 7 |
| C — Chef de secteur (`chef_secteur_a`) | 2, 3, 4, 5 |
| D — Équipage B en accès limité (`chef_secteur_b`) | 6, 3, 4, 5 |
| E (facultative) — second marin, par exemple un nouvel arrivant | 1, 2, 5, 7 |

Les sept scénarios sont couverts (1 : A, E ; 2 : A, C, E ; 3 : B, C, D ; 4 : A à D ; 5 : tous ; 6 : D ; 7 : B, E). Facultatif : parcours clavier seul de la carte « À faire » ; scénario 2 sur téléphone (seulement en environnement mobile approuvé).

## 5. Grille d'observation (une ligne par scénario et par participant)

| Participant (P1…P5, profil) | Scénario | Réussi seul (O) / avec aide (A) / échec (N) | Temps | Erreurs de clic | Hésitations, mots du marin | Indice donné |
|---|---|---|---|---|---|---|
| | | | | | | |

Questions finales, notées mot pour mot : « Qu'est-ce qui vous a gêné ? » · « Qu'est-ce qui manque ? » · note de clarté de 1 à 5 pour l'accueil, le menu, le calendrier.

## 6. Synthèse anonymisée et règle de décision

- Aucun nom, matricule ni grade dans la synthèse : seulement P1…P5 et le profil joué.
- Tableau scénario × participant (O/A/N et temps médian) ; cinq constats au plus, classés par gravité, avec le nombre de participants concernés et un verbatim.
- **Défaut ordinaire** : une correction n'est proposée que si la difficulté est **récurrente (2 participants sur 5 ou plus) et démontrée** par l'observation. Un avis isolé ou une préférence est noté, sans correction. Les retours ne justifient aucune refonte.
- **Exception — un seul cas suffit** pour :
  - une **erreur grave de compréhension** (par exemple croire pouvoir modifier une donnée en lecture seule, ou prendre une alerte pour une simple information) ;
  - une **action critique introuvable** (une action urgente, une alerte ou un accusé de réception requis non repéré) ;
  - un **problème d'accès** (connexion impossible, page refusée ou menu vide alors qu'il ne devrait pas l'être).
  L'animateur le signale aussitôt au Product Owner ; la correction n'est faite qu'après son accord.
- Détruire les grilles papier après saisie de la synthèse.
