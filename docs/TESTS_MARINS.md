# Tests d'utilisabilité avec des marins — guide d'animation

Objectif : vérifier que la tranche 1 de l'interface (menu, accueil, carte « À faire », calendrier, accès limité de l'équipage B) se comprend sans explication. Le test porte sur l'application, pas sur le marin. **Données exclusivement fictives.**

## 1. Préparer l'instance (reproductible, isolée)

```bash
python scripts/preparer_instance_test.py            # crée instance_test_marins/db.sqlite3
python scripts/preparer_instance_test.py --reinitialiser   # remise à zéro entre deux participants
MATRIX_SQLITE_PATH=instance_test_marins/db.sqlite3 DJANGO_DEBUG=1 python manage.py runserver 8800
```

La base est séparée de celle de développement (le script refuse d'écraser `db.sqlite3`), sans aucune donnée opérationnelle. Mot de passe des comptes : « pass ». Un compte par profil :

| Profil joué | Compte | Particularité |
|---|---|---|
| Marin, journée chargée | `equipier_a` | 10 actions dont 5 prioritaires |
| Marin, peu d'actions | `equipier_a2` | une tâche en retard |
| Marin, rien à faire | `equipier_nor` | liste vide |
| Chef de secteur | `chef_secteur_a` | supervision, équipe |
| Équipage B à terre | `chef_secteur_b` | accès limité, bandeau (le compte reste rattaché à son bâtiment : le présenter comme « équipage B en repos ») |

Matériel : poste 1366×768 (clavier et souris), un téléphone si possible, chronomètre, grille imprimée. Navigateur : celui du bord. Session de 20 minutes par participant, 3 à 5 participants.

## 2. Consignes de l'animateur

- Lire : « Nous testons l'application, pas vous. Pensez à voix haute. Je ne vous aiderai pas, sauf si vous êtes bloqué plus de deux minutes. »
- **Ne pas guider** : ne pas nommer les boutons, ne pas montrer. Si un participant est bloqué, noter « avec aide » et l'indice donné.
- Ne pas défendre l'interface. Noter les mots exacts utilisés par le marin.
- Arrêter immédiatement si une information réelle (non fictive) apparaît à l'écran.

## 3. Scénarios (dans cet ordre de priorité)

| # | Consigne dite au participant | Compte | Durée max |
|---|---|---|---|
| 1 | « Retrouvez la tâche *Préparer mon dossier de formation incendie*. » | `equipier_a` | 3 min |
| 2 | « Dites-moi ce qui est le plus important à traiter aujourd'hui, et pourquoi. » | `equipier_a` | 3 min |
| 3 | « Trouvez vos prochains quarts, puis vos demandes en cours. » | `equipier_a2` | 3 min |
| 4 | « Allez au calendrier et dites ce que vous avez cette semaine. » | `equipier_a2` | 3 min |
| 5 | « Fermez, puis rouvrez, la partie du menu que vous n'utilisez pas. » | `equipier_a` | 2 min |
| 6 | « Que pouvez-vous faire, et que ne pouvez-vous pas faire, avec ce compte ? » | `chef_secteur_b` | 3 min |
| 7 | « Votre liste est vide : qu'en déduisez-vous ? » | `equipier_nor` | 1 min |

Facultatif : scénario 2 sur téléphone ; parcours clavier seul de la carte « À faire ».

## 4. Grille d'observation (une ligne par scénario et par participant)

| Participant (P1…P5, profil) | Scénario | Réussi seul (O) / avec aide (A) / échec (N) | Temps | Erreurs de clic | Hésitations, mots du marin | Indice donné |
|---|---|---|---|---|---|---|
| | | | | | | |

Questions finales, notées mot pour mot : « Qu'est-ce qui vous a gêné ? » · « Qu'est-ce qui manque ? » · note de clarté de 1 à 5 pour l'accueil, le menu, le calendrier.

## 5. Synthèse anonymisée

- Aucun nom, matricule ni grade dans la synthèse : seulement P1…P5 et le profil joué.
- Tableau scénario × participant (O/A/N et temps médian).
- Cinq constats au plus, classés par gravité, chacun avec le nombre de participants concernés et un verbatim.
- **Seuil de décision** : une correction n'est proposée que pour une difficulté **récurrente (2 participants sur 5 ou plus) et démontrée** par l'observation. Un avis isolé ou une préférence est noté, sans correction. Les retours ne justifient aucune refonte.
- Détruire les grilles papier après saisie de la synthèse.
