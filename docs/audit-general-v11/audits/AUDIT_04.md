# Audit 04 — Usage quotidien (rapport partiel : navigation et liens)

**Statut : partiel, non terminé.** Cette passe porte sur la fiabilité de la navigation depuis l'accueil « Aujourd'hui », exécutée **sans navigateur** (client de test Django). Les parcours en navigateur réel sont traités à part (§4).

## 1. Balayage de tous les profils

Commande : `manage.py shell < sondes/liens_morts.py` (base de démonstration, 42 comptes actifs, accueil puis liens de chaque page ouverte, deux niveaux).

Résultat : **3 778 requêtes, 0 erreur 500**, et **cinq liens affichés qui mènent à un refus** :

| Lien | Code | Comptes concernés | Page source |
|---|---|---|---|
| `/assets/importer/` (bouton d'import) | 403 | 18 (marins, second, comptes à terre…) | `/assets/` |
| `/logistics/tickets/1a696760-…/` | 404 | `chef_secteur_a` | accueil « À faire » |
| `/maintenance/occurrences/<n>/execute/` | 403 | `equipier_a`, `equipier_a2`, `marin_b`, `equipier_elec_a`, `equipier_incendie_a` (7 occurrences) | `/maintenance/gestion/occurrences/` |
| `/quarts/mouvements/` | 403 | 8 (dont `chefsection`, `chefservice`, comptes à terre) | `/quarts/` |
| `/retex/nouveau/` | 404 | `admin` | `/retex/` |

Un lien proposé que le serveur refuse est un défaut d'ergonomie (confiance, temps perdu), pas une faille : le serveur refuse bien. Registre : AUD-016.

## 2. AUD-008 : le 404 du ticket du chef de secteur — cause établie

Reproduction : `sondes/ticket404.py`, `ticket404b.py`.

1. **Le lien est bien construit et la route existe** : le même lien renvoie 200 pour 12 profils (`admin`, `cdt_a`, `cdt_b`, `second_a`, trois COMA, `chef_secteur_incendie_a`, `equipier_incendie_a`, `admin_navire`, comptes à terre).
2. **Le 404 est volontaire** : la fiche ticket filtre par `perimetre_tickets_q` (`logistics/web_views.py:192-200`) et répond « introuvable » hors périmètre.
3. **Les données fictives en sont l'origine immédiate** : le générateur assigne le ticket d'un extincteur du secteur Sécurité/Pompiers à `chef_secteur_a`, chef du secteur Propulsion/Moteurs (commit `8aefe10`).
4. **Mais le code laisse faire et ne protège pas l'accueil** : (a) l'accueil liste les tickets assignés sans le filtre de périmètre (`dashboard/aujourdhui.py:112-118`) ; (b) l'assignation par un superviseur n'exige pas que l'assigné voie le ticket : `coma_comaeq` et `admin_navire` assignent ce ticket à `equipier_a` ou `chef_secteur_a` (réponse 302, assigné enregistré) alors qu'aucun des deux ne peut l'ouvrir.
5. **Récurrence** : la recette avait déjà constaté ce défaut (ANO-001, « CORRIGÉE ») mais n'a corrigé que le **générateur de données** (`docs/recette/04_REGISTRE_ANOMALIES.csv`). La cause code subsiste.

Verdict : défaut **confirmé**, d'origine mixte (donnée + règle manquante à l'assignation + liste d'accueil non filtrée). Registre : AUD-008 mis à jour.

## 3. « Reprendre » un brouillon (signalement d'anomalie)

Reproduction : `sondes/brouillons.py`, compte `equipier_a`.

| Cas | Lien « Reprendre » | Statut |
|---|---|---|
| Signalement, adresse nominale | `/logistics/anomalies/signaler/` | 200 |
| Signalement, route périmée | repli sur l'adresse nominale | 200 |
| Signalement avec `?asset=` ou `?installation=` inexistant | conservé | 200 |
| Compte rendu d'une occurrence supprimée | `/maintenance/occurrences/99999/execute/` | **404** |
| Compte rendu d'une occurrence hors des droits de l'utilisateur | `/maintenance/occurrences/1/execute/` | **404** |

Conclusion : **le 404 du brouillon de signalement n'a pas pu être reproduit** sur 1c37f22 (le repli `ROUTES_DE_REPRISE` de `matrix/core/brouillons.py:55-67` existe pour ce cas) ; je ne peux pas dire s'il a été corrigé ou si le déclencheur initial est différent : **à confirmer avec le PO** (étapes exactes de l'époque). En revanche, la même famille de défaut est **confirmée** pour les comptes rendus : le brouillon d'un objet disparu ou devenu inaccessible produit une carte « Reprendre » morte, sans bouton pour l'écarter (`matrix/templates/dashboard/aujourdhui.html:75-81`), jusqu'à la purge (30 jours par défaut, `.env.example`). Registre : AUD-016.

## 4. Parcours navigateur

Voir `AUDIT_05.md` (navigateur réel) pour ce qui a été joué ; ce rapport ne couvre pas l'efficacité des parcours (nombre de clics, temps de saisie).

## 5. Non audité

Fin de journée, validations enchaînées, signalement d'anomalie de bout en bout, temps de saisie comparés à Excel, mobilité.
