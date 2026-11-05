# P05 — Revue des droits codés en dur (DP-14, AUD-022)

**Méthode et limite.** Recensement par recherche textuelle des comparaisons de niveau de rôle (`>=`, `<`, `==` contre `RoleLevel.*`) hors tests et migrations : **55 sites** dans 22 fichiers, à comparer aux 71 appels du registre configurable `niveau_requis_pour`. Le contexte a été lu pour une trentaine de sites représentatifs (tous les fichiers cités ont au moins un site lu) ; les autres sont classés par analogie avec leur voisinage : **le classement est une proposition, pas une preuve ligne à ligne**. Rien n'est modifié.

Trois classes : **P** plancher de sécurité (reste un niveau, non négociable), **M** règle métier à rendre configurable ou fonctionnelle (P02), **A** affichage (doit suivre exactement la règle serveur ; risque de divergence si le seuil change).

| Fichier (sites) | Règle codée | Classe | Raison et recommandation |
|---|---|---|---|
| `logistics/web_views.py` (14) | tout acte sur un ticket (changer l'état, assigner, pièces, vues de périmètre) exige « chef de section » | **M** | règle d'exploitation propre au bord ; créer une clé de registre (par exemple `ticket_gestion`) ; conserver l'exception « assigné au ticket » déjà présente ailleurs |
| `logistics/anomalie_views.py` (2) | qualifier ou traiter une anomalie : chef de section | **M** | même clé que ci-dessus ou clé dédiée |
| `dashboard/web_views.py` (8) | ouvrir et signer une session « prêt à appareiller » : chef de secteur ; périmètre du tableau selon le niveau (service, secteur) | **M** pour l'ouverture et la signature (tâche Notion « Prêt à appareiller — droits » déjà au backlog) ; **A/P** pour le calcul du périmètre affiché | ne pas figer avant la décision métier déjà ouverte |
| `calendar_app/*` (7) | déplacer un événement, voir les occurrences non assignées : chef de section | **M** pour le déplacement (modifie la planification) ; **A** pour `editable` | `editable` du calendrier doit refléter exactement la règle serveur |
| `assets/*` (5) | création/édition de matériel, démarrage d'un contrôle : chef de section ou chef de service | **A** pour `asset_views.py:113` (le commentaire indique que le vrai contrôle passe par le registre `asset_ecriture_simple`) ; **M** pour `scan_views.py:37` et `asset_extras.py:28` s'ils portent un contrôle réel | vérifier qu'aucun chemin n'ignore le seuil réglé par le bord |
| `assets/fiche_validation.py:97`, `assets/proposition_article.py:186` | un utilisateur de niveau état-major ou plus est traité comme commandant adjoint | **M (à traiter avec P02)** | c'est la résolution du COMA par niveau, contraire à la règle Notion « résoudre le COMA du service » |
| `quarts/models.py:1529` | le visa « chef de secteur » est sauté si le proposant est chef de secteur ou plus | **M (circuit)** | règle de circuit à rendre explicite et configurable ; touche P02 |
| `quarts/alertes.py:40` | l'organisation d'alerte : compte de flotte ou même bâtiment | **P** | plancher de périmètre entre bâtiments |
| `absences/web_views.py:46` | « chef » = chef de section ou plus (validation des absences) | **M** | dépend de la décision sur les absences (qui valide) |
| `postes/services.py` (2), `training/models.py` (2) | voir les titulaires d'un poste ; qualification d'un chef de section | **M** | à rattacher aux clés `poste_gestion` et au référentiel de formation |
| `reports/*` (2) | bilans réservés à partir de chef de section | **M** | clé dédiée (lecture de pilotage) |
| `matrix/core/permissions.py:62` | chef de section ou assigné | **M/P** | plancher d'écriture « chef de section ou assigné », cohérent avec le reste ; à documenter |
| `accounts/web_views.py` (3) | gestion des comptes (changements de rôle, bâtiment, service, secteur en masse) : commandant | **P avec réserve** | plancher de sécurité (qui modifie les rôles) ; à rapprocher de la clé `mot_de_passe_reinitialisation` du registre ; ne doit pas devenir un droit de l'administrateur technique par défaut (P02) |
| `matrix/styleguide.py:389`, `matrix/core/roles.py:60` | outil de style réservé à l'administrateur ; test du compte de flotte | **P** | outil interne et compte de flotte |
| `dashboard`/`reports` templatetags (3) | masquage de liens | **A** | à aligner sur le serveur ; cause de plusieurs liens morts (AUD-016) |

## Bilan

| Classe | Sites (ordre de grandeur) | Suite proposée |
|---|---|---|
| **P** plancher | ≈ 8 | documenter dans le code et dans `docs/REFERENCE.md` comme « planchers non configurables » |
| **M** règle métier | ≈ 32 | regrouper en 6 à 8 nouvelles clés de registre ou en fonctions (P02) ; décision PO nécessaire pour trois d'entre elles (prêt à appareiller, absences, bilans) |
| **A** affichage | ≈ 15 | faire dériver le masquage de l'unique règle serveur (une fonction `peut_*` par action), ce qui supprime la classe de défauts AUD-016 |

**Constat important** : le principe n°6 de `CLAUDE.md` est tenu pour les 35 actions du registre mais pas pour les actes sur les tickets, les anomalies et le calendrier, qui ne sont donc pas réglables par un bord sans modifier le code.
