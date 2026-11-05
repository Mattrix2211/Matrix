# Analyse DP-03 — « Sections facultatives selon le bâtiment »

**Objet** : le PO ne veut pas trancher sans comprendre de quelles sections il s'agit et quelles seraient les conséquences. Aucune modification du modèle de données n'est proposée ici. Tout ce qui suit est lu dans Notion et dans le code, ou mesuré sur la base de démonstration.

## 1. De quoi parle-t-on

La hiérarchie embarquée de référence (Notion « Organigramme et rôles » p.01, p.13 ; Cahier §4, §5) est :

`commandant → second → commandants adjoints (COMAEQ, COMOPS, COMANAV, COMAVIA) → services → secteurs → sections → équipiers`

La **section** est le dernier échelon d'organisation, sous le secteur, tenu par un **chef de section** (rôle `CHEF_SECTION`, niveau 2). Exemple de la démonstration : service *Propulsion* → secteur *Moteurs* → section *Moteurs bâbord*. Aucune page Notion lue ne dit que la section est facultative ; la formule du PO (brief du 05/11) est la seule source écrite. Notion dit seulement que la hiérarchie est « configurable par navire » et que les circuits sont « jamais codés en dur ».

## 2. Ce que fait le code aujourd'hui

- `org.Section` appartient obligatoirement à un secteur (`org/models.py:188`) ; **un secteur peut n'avoir aucune section** (rien ne l'interdit).
- `UserProfile.section` est **nullable** (`accounts/models.py:65`) et les formulaires de création et d'édition d'utilisateur ne l'exigent pas.
- Le périmètre d'un marin se calcule de la **plus fine** à la plus large unité renseignée : section, sinon secteur, sinon service, sinon bâtiment (`accounts/models.py:87-96`, `UserProfile.scope`).
- Les circuits de fiches de maintenance prévoient déjà le cas sans section : « chef de secteur → chef de service → commandant adjoint » (`docs/REFERENCE.md` §3). La feuille de service ne retient que le **secteur** du rédacteur pour le visa « chef de secteur » (`secteur_redacteur`).
- **La démonstration ne contient aucun secteur sans section** (5 bâtiments, tous les secteurs ont au moins une section) : le cas n'est donc exercé ni par la recette ni par les parcours de l'audit.

## 3. Mesure : ce que voit un marin selon son rattachement (SQLite, base de démo)

Même profil `EQUIPIER` du bâtiment Bretagne, quatre rattachements (commande `sondes/sections2.py`) :

| Rattachement du compte | Périmètre calculé | Installations | Tickets | Occurrences de maintenance |
|---|---|---|---|---|
| Section renseignée (`equipier_a`) | section | 4 | 4 | 5 |
| Secteur sans section | secteur | 4 | 4 | 5 |
| Service seul | service | 4 | 4 | 5 |
| **Bâtiment seul (ni service, ni secteur, ni section)** | **bâtiment** | **5 sur 7** | **6 sur 7** | **11 sur 11** |

Lecture honnête : sur ces données, section, secteur et service donnent les mêmes volumes (un seul secteur par service concerné, une seule section par secteur), donc la **différence section/secteur n'est pas mesurable ici**. Ce qui est mesuré et net : **oublier le rattachement élargit la vision à tout le bâtiment** (11 occurrences sur 11 au lieu de 5). C'est le même sujet que la décision déjà validée « Rattachement organisationnel obligatoire pour tout compte opérationnel » (Notion, « À faire plus tard »).

## 4. Pourquoi la question est piégeuse

Un marin « sans section » peut vouloir dire deux choses que le système **ne distingue pas** :

1. **La section n'existe pas** dans son secteur (petit bâtiment) : c'est normal, il dépend directement du chef de secteur.
2. **La section existe, mais la fiche du marin n'a pas été complétée** : erreur de saisie, qui élargit sa vision au secteur entier.

## 5. Exemple concret à bord

*Patrouilleur de 45 marins, service « Pont », secteur « Manœuvre », 8 marins, pas de chef de section.*
- Aujourd'hui : on crée le service, le secteur, et on rattache les 8 marins au secteur sans section. Ils voient les données du secteur (voulu). Le chef de secteur attribue les tâches (fonctionne : l'attribution à une unité couvre section, secteur, service). Un matériel du secteur est visible des 8 marins.
- Ce qui ne marche pas bien : rien ne dit à l'écran que « sans section » est un choix ; si un neuvième marin est créé avec le seul bâtiment renseigné, il voit tout le bâtiment sans alerte. Les écrans et libellés qui parlent de « section » restent affichés et vides.

## 6. Options (pour décision du PO, aucune n'est mise en œuvre)

| Option | Principe | Avantages | Inconvénients et risques |
|---|---|---|---|
| **A. Statu quo documenté** | La section reste facultative par construction ; on documente la règle « sans section = périmètre du secteur ». | Aucun développement ; fonctionne déjà. | Confond « n'existe pas » et « oubliée » ; l'oubli élargit la vision ; cas non testé en recette. |
| **B. Règle dérivée de la structure (recommandation de l'audit)** | Si le secteur contient au moins une section active, la section est obligatoire pour un compte opérationnel ; sinon elle est sans objet. Alerte sur les comptes incohérents. | Aucune nouvelle saisie ; cohérent avec « rattachement obligatoire » déjà décidé ; sans paramètre à régler. | Petit développement (validation + alerte) ; à décider avec le chantier du rattachement obligatoire. |
| **C. Réglage explicite par bâtiment** | Un paramètre « ce bâtiment utilise des sections » (oui/non). | Intention claire et visible. | Un réglage de plus à tenir à jour ; peut diverger de la structure réelle. |
| **D. Masquer la section** (option d'interface) | Si le bâtiment n'a aucune section, les libellés « section » disparaissent des écrans. | Interface plus sobre (principe de non-surcharge). | Ne règle pas la question des droits ; doit s'appuyer sur B ou C. |

**Ce que l'audit recommande, comme hypothèse à valider** : B (éventuellement complétée par D), conduite avec le chantier « rattachement obligatoire ». **Question métier à poser au PO** : sur un bâtiment sans chef de section, qui tient le rôle (droits, circuit de visa, désignation du chef de liste) : le chef de secteur directement ? Si oui, c'est déjà le comportement du code pour les fiches ; à confirmer pour les listes de service, les tâches et la feuille de service.

## 6 bis. Ce qui reste à vérifier avant de conclure

Test navigateur d'un bâtiment à secteur sans section (création complète par l'interface : unité, service, secteur, marins), attribution de tâches à un secteur, désignation d'un chef de liste au niveau secteur, visa de la feuille de service par un rédacteur sans section. Non fait à ce jour.
