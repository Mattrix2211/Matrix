# Points à confirmer (B1 à B8)

### B1 — Suppléance du COMAEQ

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-SUP-01` : la suppléance est **explicitement désignée, activée par une autorité compétente, temporaire, limitée à une fonction et à un périmètre, et tracée** ; `DEC-SUP-02`, `DEC-SUP-04`, `DEC-SUP-05`, `DEC-SUP-07` |
| **Fonctionnement actuel vérifié** | Aucun mécanisme général. Seuls secours codés : le commandant de l'équipage peut viser la feuille de service et désigner les rédacteurs quand le poste COMAEQ est **vacant** (`quarts/models.py:2210`) ; remplacement temporaire d'un chef de liste des services à quai (`quarts/remplacement.py:27`) |
| **Règle cible** | Le principe est décidé. **La procédure exacte de désignation du suppléant du COMAEQ est à confirmer** (lot L08) |
| **Profils concernés** | COMAEQ ; commandants |
| **Statut** | à confirmer par le PO |

### B2 — Commandant en second

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Notion « 13 — Décisions » : vision globale ; écritures limitées aux **responsabilités attribuées** ; il ne tient pas ses droits automatiquement de son grade |
| **Fonctionnement actuel vérifié** | Écriture héritée du grade retirée (API) mais seuil comparé au grade dans plusieurs vues web (A4) |
| **Règle cible** | Les responsabilités doivent être **explicites et attribuées dans un cadre autorisé** ; qui les attribue, par quel mécanisme et dans quelles limites est **à confirmer** |
| **Profils concernés** | commandant en second |
| **Statut** | à confirmer par le PO |

### B3 — Échanges et quarts à la mer

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-FDS-07` : « échanges de tours » sans préciser le périmètre ; `DEC-FDS-13` |
| **Fonctionnement actuel vérifié** | Échanges limités aux **services à quai** d'une même liste (`quarts/echanges.py:1`) |
| **Règle cible** | **Ne pas généraliser** aux quarts à la mer sans validation métier : à confirmer |
| **Profils concernés** | chefs de liste ; COMAEQ |
| **Statut** | à confirmer par le PO |

### B4 — Accostage et appareillage

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Aucune décision du registre des 125 ; les propositions `mer_quai_*` (état B) décrivent la règle comme validée |
| **Fonctionnement actuel vérifié** | Déclaration par le **titulaire COMAEQ** ou le **commandant de l'équipage à bord** (`fonction_habilitee`, `quarts/mouvements.py:27`) ; correction par annulation motivée |
| **Règle cible** | Le fonctionnement actuel est documenté ; **l'autorité cible est à confirmer** |
| **Profils concernés** | COMAEQ ; commandants |
| **Statut** | à confirmer par le PO |

### B5 — Chef de liste des quarts

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Notion « 13 » : le chef de liste crée et publie les listes de service et de gardes (**décision antérieure**, remplacée par `DEC-FDS-14` pour la publication) ; `D11` (mer/quai) : chef de liste des quarts **distinct** du chef de liste des services à quai |
| **Fonctionnement actuel vérifié** | Désignation par supervision ou par un niveau chef de service dont le périmètre couvre celui visé (`quarts/listes_views.py:163`) |
| **Règle cible** | Qui désigne : **à confirmer** |
| **Profils concernés** | chefs de liste ; chefs de service |
| **Statut** | à confirmer par le PO |

### B6 — « Fin de journée » d'une tâche

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-BLQ-05` (état « Non réalisée — À reprogrammer ») |
| **Fonctionnement actuel vérifié** | Aucune notion de fin de journée |
| **Règle cible** | Heure par bâtiment (`IM-09`) : **à confirmer** |
| **Profils concernés** | marins ; chefs de section |
| **Statut** | à confirmer par le PO |

### B7 — Ordre des grades

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-COL-02` |
| **Fonctionnement actuel vérifié** | Le grade est un texte sans rang |
| **Règle cible** | Valeurs à saisir par le PO : **à confirmer** (`IM-02`) |
| **Profils concernés** | PO |
| **Statut** | à confirmer par le PO |

### B8 — Conservation

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Aucune décision |
| **Fonctionnement actuel vérifié** | Notifications, journaux et estimations non purgés |
| **Règle cible** | Durées **à confirmer** (`IM-10`) |
| **Profils concernés** | exploitants ; PO |
| **Statut** | à confirmer par le PO |

