# P04 — Administration et réorganisation de la structure du bord (DP-13, AUD-019, AUD-020, AUD-021)

**Statut : étude et proposition ; rien n'est implémenté.** Orientation du PO : un bâtiment gère son organisation locale par des **fonctions expressément habilitées**, sans dépendre d'un compte technique central ; priorité à la **modification, au renommage, à l'archivage et à la désactivation** ; aucune suppression physique qui perde l'historique ou élargisse implicitement les accès.

## 1. État mesuré

| Sujet | Constat | Preuve |
|---|---|---|
| Qui peut modifier la structure | **Par l'API** : l'administrateur d'unité (clé de registre `structure_navire_ecriture`, bornée à son unité) crée, renomme, archive et supprime services, secteurs, sections (201, 200, 200, 204). Commandant, chef de service : 403. **Par l'écran « Paramètres »** : seulement le compte de flotte ; aucune action de renommage ni d'archivage | `sondes/api_org.py`, `sondes/structure.py` |
| Archivage | Les champs `archived` existent (bâtiment, service, secteur, section), sont sérialisés et filtrables dans l'administration Django, mais **aucune règle de l'application ne les utilise** : une section archivée reste proposée dans les formulaires, ses marins gardent leur périmètre | `sondes/archive.py` ; recherche de `archived` dans le code (aucun filtre) |
| Suppression | physique ; par l'écran (compte de flotte) et par l'API (administrateur d'unité) ; aucune confirmation côté serveur | `matrix/views.py:641-675` |
| Effet sur les marins | rattachement remis à NULL, périmètre élargi d'un niveau (4 marins de section → secteur) | AUD-020 |
| Effet sur l'historique | suppression **en cascade** des listes de quart et de garde, désignations de chefs de liste, remplacements, annonces, événements du programme, postes, documents, exigences de formation, types de matériel, modèles de fiches et de rondes ; mise à NULL du secteur du rédacteur de feuilles (perte de trace) | `sondes/fk.py`, `sondes/cascade.py` |
| Protection existante | matériel, installations et stocks sont protégés (PROTECT) : une erreur 500 sans message | AUD-021 |

## 2. Ce qui arrive lors d'une réorganisation de secteur (scénarios)

| Scénario | Marins | Équipements | Documents, annonces, listes | Aujourd'hui |
|---|---|---|---|---|
| Renommer | inchangés | inchangés | inchangés | **impossible** à l'écran ; possible par l'API |
| Archiver (désactiver) | doivent être réaffectés ou rester sans accès élargi | restent rattachés, lecture historique | conservés en lecture | **sans effet** (champ ignoré) |
| Fusionner deux secteurs A et B | transfert A→B | transfert des équipements, stocks, fiches | transfert des documents, annonces futures, listes en cours | **pas de fonction** ; la suppression de A détruit ses listes/annonces/documents |
| Scinder un secteur | choix par marin | choix par équipement | choix par document | pas de fonction |
| Changer de service (déplacer le secteur) | inchangés | inchangés, **le service porteur change** donc le COMA compétent change | circuits en cours à re-router | possible par l'API ; effets sur les circuits non audités |
| Changer le commandant adjoint du service | inchangés | inchangés | circuits futurs seulement ; visas passés conservés | existant pour les fonctions COMA |
| Supprimer | rattachement perdu | refus (PROTECT) puis erreur | **destruction en cascade** | à interdire |

## 3. Cible proposée

1. **Fonction « gestion de la structure »** par bâtiment (déjà préfigurée par `structure_navire_ecriture`) : attribuable à une personne désignée (pas seulement à un niveau), avec écran dédié dans « Paramètres » pour toute la hiérarchie : créer, **renommer**, **archiver**, **réactiver**, **déplacer** (secteur vers un autre service), **fusionner**. L'administrateur technique peut recevoir la fonction, mais ses actes sont signés comme tels.
2. **Interdire la suppression physique** d'une unité ayant un historique : la suppression n'est autorisée que pour une unité **jamais utilisée** (aucune dépendance, y compris celles en cascade) ; sinon, archivage.
3. **L'archivage a des effets définis** : plus de nouvelles affectations ni de nouveaux objets dans l'unité ; l'historique garde le nom ; les listes, annonces, documents et fiches restent lisibles ; les marins rattachés **ne gardent pas silencieusement un accès élargi** : ils passent « à compléter » (P01) avec alerte, ou sont transférés par l'assistant.
4. **Assistant de transfert** (obligatoire avant archivage/fusion d'une unité occupée) : choisir la destination des marins, du matériel, des stocks, des documents, des fiches, des postes et des listes ; aperçu chiffré (« 6 marins, 4 installations, 2 listes, 3 documents ») ; exécution atomique ; une ligne de journal par catégorie, avec avant/après.
5. **Aucun nom stocké en texte dans l'historique n'est réécrit** ; le renommage change le libellé courant, les journaux conservent l'identifiant.
6. **Garde-fous** : confirmation explicite avec comptes ; motif ; double regard (proposition → validation) pour les fusions et déplacements de service (principe n°7) ; annulation possible dans un délai.
7. **Messages** : plus aucune exception brute (AUD-021) ; explication en français et renvoi vers l'assistant.

## 4. Options de mise en œuvre

| Option | Contenu | Avantage | Risque |
|---|---|---|---|
| **1 — Garde-fous minimaux** | refuser la suppression dès qu'une dépendance existe (y compris en cascade), message clair, archivage effectif dans les formulaires et périmètres | corrige AUD-020/021 sans écran nouveau | pas de renommage à l'écran |
| **2 — Écran de structure** (recommandée) | option 1 + renommage, archivage, réactivation par un écran habilité | répond à DP-13 | écran à concevoir avec les maquettes |
| **3 — Réorganisation assistée** | option 2 + fusion, scission, déplacement avec assistant et validation | couvre les réorganisations réelles | chantier plus lourd ; à planifier après V1.1 |

## 5. Dépendances

P01 (états de rattachement), P02 (fonction de gestion et désignations), DP-11 (import : même logique de validation des rattachements).
