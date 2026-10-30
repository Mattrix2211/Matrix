# Tests d'utilisabilité avec des marins — guide d'animation

Objectif : vérifier que la tranche 1 de l'interface (menu, accueil, carte « À faire », calendrier, accès limité de l'équipage B) se comprend sans explication. Le test porte sur l'application, pas sur le marin. **Données exclusivement fictives.** Séances coordonnées par le Product Owner.

## 1. Préparer l'instance (isolée, reproductible, sans risque pour les bases existantes)

> **À n'utiliser que sur un poste local ou un environnement isolé.** L'instance a des mots de passe fictifs (« pass ») et le mode DEBUG actif : ne jamais l'exposer sur un réseau opérationnel ou accessible de l'extérieur. Elle écoute uniquement sur `127.0.0.1`.

```bash
python scripts/preparer_instance_test.py --verifier         # contrôle seul : n'écrit rien
python scripts/preparer_instance_test.py                    # crée instance_test_marins/db.sqlite3
python scripts/preparer_instance_test.py --reinitialiser    # remise à zéro entre deux participants
```

Le script affiche ensuite la commande de lancement, à copier telle quelle :

```bash
MATRIX_SQLITE_PATH=instance_test_marins/db.sqlite3 MATRIX_ENV_FILE=instance_test_marins/aucun.env DJANGO_DEBUG=1 python manage.py runserver 127.0.0.1:8800
```

Garanties (vérifiées par des tests automatiques) :

- La base SQLite de démonstration est choisie **explicitement** (`MATRIX_SQLITE_PATH`) et l'emporte toujours sur une configuration PostgreSQL, y compris celle d'un `.env` : le `.env` du poste est même ignoré (`MATRIX_ENV_FILE` pointe sur un fichier absent), et l'envoi d'e-mails réels est coupé.
- Avant toute écriture, le script interroge la configuration réellement chargée et **refuse de démarrer** si la connexion ne vise pas exactement le fichier attendu en SQLite.
- Seul un fichier `.sqlite3` placé directement dans `instance_test_marins/` est accepté ; la base de développement `db.sqlite3`, les autres dossiers, les liens symboliques et les dossiers sont refusés. `--reinitialiser` ne supprime qu'un fichier de ce dossier créé par le script (fichier voisin `<base>.instance_demo`). Une base créée avant cette version n'a pas ce marqueur : la supprimer à la main avant de relancer.
- Si vous lancez le serveur à la main, gardez les deux variables ci-dessus : sans `MATRIX_SQLITE_PATH`, Django utiliserait la base de développement.

Mot de passe fictif de tous les comptes : « pass ».

| Profil joué | Compte | Particularité |
|---|---|---|
| Marin, nombreuses actions | `equipier_a` | 10 actions dont 5 prioritaires |
| Marin, peu d'actions | `equipier_a2` | une tâche en retard |
| Marin, rien à faire | `equipier_nor` | liste vide (scénario 7) |
| Chef de secteur | `chef_secteur_a` | supervision, équipe |
| Équipage B en accès limité | `chef_secteur_b` | bandeau d'accès limité (le compte reste rattaché à son bâtiment : le présenter comme « équipage B en repos ») |

Matériel : poste 1366×768 (clavier et souris), un téléphone si possible, chronomètre, grille imprimée. Navigateur : celui du bord.

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

Les sept scénarios sont couverts (1 : A, E ; 2 : A, C, E ; 3 : B, C, D ; 4 : A à D ; 5 : tous ; 6 : D ; 7 : B, E). Facultatif : scénario 2 sur téléphone ; parcours clavier seul de la carte « À faire ».

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
