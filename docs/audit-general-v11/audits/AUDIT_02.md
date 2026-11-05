# Audit 02 — Configurabilité et adaptabilité (rapport partiel)

**Statut : partiel, non terminé.** Question centrale : un bord règle-t-il seul son organisation, ses droits et son fonctionnement, sans développeur ? Méthode : lecture de `matrix/views.py` (Réglages) et de `matrix/core/role_thresholds.py`, essais d'écriture par 5 profils (`sondes/structure.py`, `structure2.py`) et exploration navigateur (`sondes/navigateur/nav8.js`, `nav10.js`).

## 1. Ce qu'un administrateur d'unité peut configurer (vérifié en navigateur)

Onglets accessibles à `admin_navire` dans « Paramètres » : notifications, utilisateurs (désignation de responsables transverses), équipage (relève, fuseau horaire, passation), **modules** (activer/désactiver par bâtiment), **seuils de rôle** (qui peut faire quoi, par bâtiment). Le chef de service n'a que ses notifications. Le menu d'un administrateur d'unité pointe vers `?tab=notifications` ; l'adresse nue `/parametre/` renvoie un refus 403 à ces profils (onglet par défaut réservé au superutilisateur) : sans conséquence pour l'usage normal, mais surprenant.

**Seuils de rôle** : 35 actions du registre (`REGISTRE_ACTIONS`) réglables par bâtiment, avec une version en base pour la cohérence multi-processus (`org.VersionConfiguration`). C'est le point fort du produit sur la configuration des droits. **Mesure** : 71 appels à `niveau_requis_pour` (seuil configurable) contre 55 comparaisons de niveau écrites en dur hors tests (`grep`), concentrées dans `logistics/web_views.py` (14), `dashboard/web_views.py` (8), `calendar_app` (7) ; exemples : toute transition de ticket exige « chef de section » en dur, l'ouverture et la signature d'une session d'appareillage exigent « chef de secteur » en dur. Chaque cas n'est pas nécessairement une règle métier (certains sont des planchers), mais le principe n°6 de `CLAUDE.md` n'est pas tenu partout : **hypothèse à vérifier cas par cas** (AUD-022).

## 2. Ce qu'il ne peut pas configurer (défaut confirmé)

| Opération | Résultat | Preuve |
|---|---|---|
| Créer un service, un secteur, une section | Réservé au **superutilisateur** (compte MASTER_ADMIN) ; 403 pour administrateur d'unité, commandant, second, chef de service | `sondes/structure.py` ; `matrix/views.py:276-325` |
| Renommer un service, un secteur, une section | **Aucune action** dans l'écran | recherche textuelle dans `matrix/views.py` |
| Supprimer un service, secteur ou section | Superutilisateur ; suppression physique immédiate ; marins détachés et périmètre élargi sans alerte (AUD-020) ; erreur 500 si du matériel est rattaché (AUD-021) | idem |
| Créer, éditer, dupliquer un bâtiment | Superutilisateur | `matrix/views.py:546-589` |
| Fonctions, grades, spécialités | Superutilisateur | `matrix/views.py:530-545` |

**Conclusion partielle** : le produit est **configurable en droits et en modules par bâtiment**, mais **la structure organisationnelle du bord n'est pas autonome** (AUD-019) et sa modification est risquée (AUD-020, AUD-021). Le principe « services, secteurs, sections, responsables… adaptables par le bord » (brief, Cahier §4) est **partiellement conforme**.

## 3. Sections facultatives

Voir `AUDIT_DP03_SECTIONS.md`. Compléments : la suppression d'une section détache les marins vers le secteur (AUD-020) ; aucun test ni donnée de démonstration ne couvre un secteur sans section.

## 4. Non audité

Configuration des chefs de liste et rubriques de la feuille de service (essais de droits faits, pas de parcours de configuration complet), types de tâches, catégories, checklists, fiches, régimes de quart (aucune durée de quart en dur trouvée dans `quarts/`, hors affichage), paramètres des annonces et tâches, effet réel d'un changement de seuil sur un autre processus (version de configuration : lecture seule).

## 5. Anomalies liées

AUD-019, AUD-020, AUD-021, AUD-022 (à ouvrir après revue cas par cas).
