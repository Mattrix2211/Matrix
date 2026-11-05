# Audit 06 — Rôles, permissions et délégations (rapport partiel, 2ᵉ passe)

**Statut : partiel, non terminé.** Commit audité : `1c37f22`. Méthode et sondes : `sondes/README.md`. Tout ce qui suit a été **exécuté** sur une base SQLite temporaire de démonstration (`migrate` + `seed_demo`), avec le client de test Django, côté **serveur** (les boutons de l'interface ne sont pas la preuve) ; les écritures sont annulées par transaction.

Référentiel métier lu en entier : les 13 sous-pages Notion « Organigramme et rôles » (01 à 13) et le hub (voir `08_LIMITES_ET_PREUVES.md`).

## 1. Porte d'autorisation des écritures de quarts (21 profils × 67 cibles, 1 407 requêtes)

Commande : `manage.py shell < sondes/matrice_droits.py`. Résultat : **aucune erreur 500**. « Franchit » = réponse autre que 403/404 (la porte est passée ; l'effet réel est vérifié au §2).

| Cible / action | Profils qui franchissent la porte |
|---|---|
| Quart en brouillon : ajouter/supprimer créneau, proposer | `chef_secteur_a` (chef de liste), `cdt_a`, `admin_navire`, `admin` |
| Quart ou garde **publié** : ajouter/supprimer créneau, proposer, régler les échanges | `cdt_a`, `admin_navire`, `admin` (le chef de liste est refusé) |
| Publier un quart | `chef_service_a`, `coma_comaeq`, `coma_comanav`, `coma_comops`, `cdt_a`, `admin_navire`, `admin` |
| Publier une garde | `coma_comaeq`, `coma_comanav`, `coma_comops`, `cdt_a`, `admin_navire`, `admin` |
| Activer / reporter une garde | personne (état du jeu de démonstration) |
| Désigner, remplacer, retirer un chef de liste | chefs de service, 3 COMA, `second_a`, `cdt_a`, `admin_navire`, `admin` |
| Rubriques et fonctions de la feuille de service | idem, sauf chef de secteur |
| Déclarer / initialiser un mouvement du bâtiment | `coma_comaeq`, `cdt_a` (pas `second_a`, conforme à « écritures limitées ») |
| Créer une feuille de service | `equipier_a2`, `marin_b` (rédacteurs désignés de leur équipage) |
| Autre bâtiment (Auguste Bénébig) | seuls les profils de ce bâtiment et `admin` : étanchéité entre bâtiments **conforme** |

## 2. Effets réels (pas seulement la porte)

Commandes : `sondes/droits2.py`, `sondes/circuit.py`, `sondes/auto_visa.py`.

| Contrôle | Résultat | Verdict |
|---|---|---|
| Création de feuille par `equipier_a` (matelot sans fonction BSC) | 403, aucune feuille | **Conforme** (EX-026) |
| Création par un rédacteur désigné avec `?equipage=` de l'autre équipage | La feuille créée est toujours celle de **son** équipage (A→A, B→B) | **Conforme**, pas d'échappement inter-équipage |
| Désignation de rédacteurs | L'effet n'existe que pour le COMAEQ titulaire de l'équipage (A) et le commandant de B pour B ; ni `cdt_a`, ni `admin`, ni le second | **Conforme** |
| Visa COMAEQ, correction COMAEQ, renvoi au dernier palier | Seul `coma_comaeq` a un effet | **Conforme** |
| Ouvrir un rectificatif d'une feuille publiée | Seul `equipier_a2` | **Conforme** |
| **Visa « chef de secteur »** (feuille proposée) | Effet réel pour `chef_secteur_a` **mais aussi** `chef_service_a`, `coma_comaeq`, `coma_comanav`, `coma_comops`, `cdt_a`, `admin_navire` | **Écart, voir AUD-014** |
| **Visa « chef de service »** | Effet pour `chef_service_a` **et** les 3 COMA, `cdt_a`, `admin_navire` | **Écart, voir AUD-014** |
| Une seule personne passe les deux visas | `admin_navire` puis `cdt_a`, chacun seul : statut `VISA_SECTEUR → VISA_SERVICE → VISA_COMAEQ`, les deux champs de visa portent la même personne | **Confirmé** (aucun contrôle « personne différente ») |
| Suppression d'un créneau d'un quart **publié** (motif fourni) | Effet pour `cdt_a`, `admin_navire`, `admin` ; refus pour `chef_secteur_a` | **Confirmé, voir AUD-015** |

Lecture : l'étape finale (COMAEQ) reste verrouillée ; les deux paliers intermédiaires ne le sont pas. Le test existant `test_administrateurs_ne_redigent_ni_ne_visent_par_le_seul_role` (`quarts/tests/test_feuille_service_a_terre.py:88`) affirme l'inverse mais ne couvre que la feuille de l'équipage B à terre ; le cas de l'équipage à bord n'est pas testé (voir audit 16).

## 3. Autres constats de droits

- **AUD-001 : résolu sur 1c37f22 pour la création** (§2). Reste non rejoué : édition de l'en-tête et proposition par un non-rédacteur (sur brouillon, seul `equipier_a2` a un effet ; les 15 autres profils sondés sont refusés), API (la feuille n'en a pas : `quarts` n'expose aucune vue DRF), et comportement sur `main` (lecture de code seulement). Je ne le déclare pas « définitivement résolu ».
- `second_a` (commandant en second) ne publie pas de liste (`quarts/models.py` : `NIVEAU_VISION_COMMANDEMENT` exclu), mais peut désigner des chefs de liste et configurer les rubriques de la feuille : cohérent avec « délégation limitée », à confirmer par le PO (décision ouverte dans Notion, tâche « Commandant en second : actions d'écriture »).
- Publication des listes ouverte au **niveau** état-major : COMANAV et COMOPS publient les listes de service alors que la fonction « service courant » est celle du COMAEQ (Notion 06, 13). Déjà identifié par `docs/propositions/droits_comaeq.md` ; confirmé ici par exécution (AUD-014).

## 4. Hors périmètre de cette passe (non audité)

API DRF des autres modules, droits de formation, de stock, de documentation ; délégations ; cache des permissions ; `main`.

## 5. Anomalies liées

AUD-001, AUD-008, AUD-014, AUD-015.
