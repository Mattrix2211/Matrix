# L06 — Proposition : initialisation des premières autorités métier d'un bâtiment

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** **Proposition soumise au PO. Rien n'est implémenté** (AC-01 : « si la procédure nécessite une nouvelle décision de sécurité, soumettre une proposition avant de l'implémenter »).

## 1. Problème

Depuis L06, l'administrateur technique ne désigne aucune autorité métier (ARB-01 règle 4, AC-02). Lors de l'installation d'un bâtiment, il n'existe encore aucun commandant : personne ne peut désigner le premier commandant, ni les adjoints. Aujourd'hui seul l'administrateur général (compte superutilisateur) le peut, par l'API ou l'administration Django : c'est un **chemin implicite, non tracé comme tel, ouvert en permanence**.

## 2. Options

| Option | Principe | Avantages | Risques |
|---|---|---|---|
| **A — commande d'installation (recommandée)** | Commande de gestion exécutée **sur le serveur** par l'exploitant (`manage.py initialiser_autorites_batiment`) : désigne le commandant et, si précisé, les adjoints d'un bâtiment, une seule fois. | Aucun accès web ; aucune auto-attribution possible depuis l'application ; verrouillée par construction après usage ; tracée. | Suppose un accès système de l'exploitant ; commande à documenter dans la procédure d'installation. |
| B — statu quo explicité | L'administrateur général désigne les premières autorités par l'administration Django. | Aucun développement. | Chemin permanent, sans verrou ni trace dédiée, qui confond installation et exploitation. |
| C — assistant web | Page réservée à l'administrateur général, jeton d'installation à usage unique. | Ergonomique. | Surface web supplémentaire sensible ; plus de code à sécuriser. |

## 3. Garde-fous proposés pour l'option A

1. **Usage unique par bâtiment** : refus dès qu'un commandant actif existe sur le bâtiment.
2. **Comptes distincts de l'opérateur** : la commande désigne des comptes existants ; elle ne crée pas d'administrateur et n'attribue jamais d'autorité à un compte portant les droits techniques, sauf option explicite `--accepter-cumul` (cumul volontaire, tracé en clair).
3. **Mot de passe provisoire** : le commandant désigné change son mot de passe à sa première connexion (mécanisme existant) ; aucun mot de passe n'est affiché ni journalisé.
4. **Trace** : une entrée du journal d'audit par désignation (bâtiment, compte, rôle, identité système de l'opérateur, date), consultable ; aucune suppression.
5. **Pas de contournement permanent** : la commande ne sert ni à changer un commandant en place, ni à désigner un second, ni à modifier un compte existant d'une autorité ; ces actes restent aux autorités du bâtiment (AC-02) ou à l'administrateur général.
6. **Environnement** : refusée si la configuration de production est invalide (L05) ; jamais déclenchée par une requête web.

## 4. Questions au PO

1. Retenez-vous l'option A avec ces garde-fous ?
2. L'initialisation peut-elle désigner un compte qui porte aussi les droits techniques (`--accepter-cumul`), ou doit-elle l'interdire absolument ?
3. **Désignation du commandant en second** : elle n'apparaît pas dans le tableau AC-02 ; aujourd'hui elle revenait à l'administrateur d'unité. Proposition : le commandant désigne son second ; l'administrateur général reste l'ultime recours. À confirmer.
4. **Administrateur général (superutilisateur Django)** : il cumule aujourd'hui tous les droits (techniques et métier) sur toute la flotte. L06 ne le modifie pas (hors périmètre). Faut-il instruire une séparation du même ordre pour ce compte ?
5. **Réinitialisation d'un mot de passe** : L06 réserve à l'administrateur général la réinitialisation du mot de passe d'une autorité au-dessus de chef de section ou d'un autre administrateur technique (sinon reprise de compte, donc auto-attribution indirecte). Qui doit réinitialiser le mot de passe d'un chef de service ou d'un commandant dans l'exploitation courante ?
