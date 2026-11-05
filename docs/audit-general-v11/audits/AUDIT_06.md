# Audit 06 — Rôles, permissions et délégations (rapport partiel)

**Statut : partiel, non terminé.** Commit audité : `1c37f22`. Une seule règle a été rejouée en dynamique ; le reste n'est pas audité.

## 1. Ce qui a été vérifié (preuve dynamique)

Méthode : base SQLite temporaire hors dépôt, `migrate` puis `seed_demo`, client de test Django avec connexion forcée, POST `action=creer` sur `/quarts/feuille-service/2/2027-03-01/` (bâtiment « Bretagne », double équipage), transaction annulée après chaque essai.

| Compte | Fonction (dossier de recette) | Résultat | Attendu (EX-026) |
|---|---|---|---|
| `equipier_a` | Matelot sans fonction BSC | 403, aucune feuille créée | Refus |
| `equipier_a2` | Matelot BSC désigné rédacteur (équipage A) | 302, feuille créée | Création |
| `marin_b` | Rédacteur désigné (équipage B) | 302, feuille créée | Création (son équipage) |
| `chef_section_a`, `chef_secteur_a`, `chef_service_a` | Chefs | 403 | Refus (le grade ne suffit pas) |
| `coma_comaeq`, `second_a`, `cdt_a`, `admin_navire` | Commandement et administration | 403 | Refus (lecture et visas seulement) |
| `terre_classe` | Suivi à terre | 403 | Refus |

**Conclusion : V-C pour EX-026 sur 1c37f22**, sur ce scénario et ces données. Ce qui reste non vérifié : la création pour l'équipage de l'autre bord par un rédacteur (`marin_b` sur l'équipage A), l'édition et l'API, les autres actions de la feuille. Sur `main` (`6ef16ad`) la restriction n'existe pas (AUD-001, lecture de code, non rejoué).

## 2. Accès anonyme

Parcours de 227 routes sans paramètre sans être connecté : seules `/accounts/login/`, `/admin/login/`, `/login/` et `/service-worker.js` répondent 200. Les routes avec paramètre n'ont pas été testées.

## 3. Balayage des pages visibles par profil

Pour 10 profils (équipier, chef de section, de secteur, de service, COMAEQ, second, commandant, administrateur d'unité, suivi à terre, administrateur général), chaque lien interne de l'accueil a été ouvert : environ 330 requêtes, **aucune erreur 500**, une seule erreur 404 (AUD-008, lien mort de l'accueil). Ce balayage ne dit rien sur la justesse des données affichées ni sur les droits d'écriture.

## 4. Non audité

Matrice complète rôle × action × périmètre, délégations aux commandants adjoints (décision PO non rendue, cf. `docs/propositions/droits_comaeq.md`), étanchéité par équipage sur les API, séparation entre bâtiments hors démonstration, cache des permissions. La couverture des tests existants (`matrix/tests/test_etancheite_equipage*.py`, `test_securite_*.py`) n'a pas été évaluée.

## 5. Anomalies liées

AUD-001 (corrigé sur 1c37f22, non fusionné), AUD-008.
