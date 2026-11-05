# MATRIX V1.1 — Préparation de la recette utilisateur : synthèse

Branche `claude/iteration-ux-v11-20261102`, commit `8aefe10`. Aucun merge dans main, aucun déploiement, aucune donnée existante supprimée ni réinitialisée (bases de vérification créées à part).

## 1. Ce qui est prêt
- Création de la base de démonstration reproductible : deux créations indépendantes donnent exactement les mêmes volumes (84 types d'objets comparés) ; `--mettre-a-jour` appliqué deux fois ne crée aucun doublon.
- Aucune incohérence détectée par le contrôle de données : pas de double affectation applicable, pas de créneau inversé, stocks cohérents avec leurs mouvements, historiques cohérents avec les états, liens de notification valides.
- 25 parcours navigateur rejoués avec les profils prévus : 25 sur 25 conformes sur base fraîche (accueil, calendrier, tâches, maintenance, anomalies, logistique, notifications, échanges, activations, conflit, mer/quai, permissions).
- Exploration de tous les liens du menu et des pages pour 21 profils : aucun lien en erreur hors pages réellement inaccessibles par rôle, aucune erreur JavaScript, aucun débordement horizontal à 1366 px.
- Interfaces : accueil, bandeau, menu, quarts et tours (vues A et B), tâches, maintenance, anomalies, circuit de la feuille de service conformes aux références validées.

## 2. Ce qui a été corrigé (détail dans le registre)
ANO-001 liens « Ouvrir » vers « introuvable » pour des tickets et maintenances assignés hors du périmètre de l'assigné (bloquant) ; ANO-002 installations de fiches mal rattachées ; ANO-003 liste à publier introuvable depuis l'entrée pour le COMAEQ ; ANO-004 anomalies sans historique ; ANO-005 cas particuliers manquants (conflit d'activation, tâche bloquée chez equipier_a, ticket chez le chef de secteur).
Chaque correction a un test automatisé. Aucune règle métier ni direction UX modifiée.

## 3. Ce qui reste incomplet
Voir `03_FONCTIONNALITES_INCOMPLETES.md` : feuille de service « vraie feuille » (en attente de votre exemple), silhouettes, archivage des notifications, rappels évalués à la lecture, délégations et organigrammes officiels, passe « périmètre » (D-A).
Points UX ouverts, soumis à votre décision (ANO-007 à ANO-010) : libellé de menu sur deux lignes ; vue « Par jour » très longue (~5 800 px) ; calendrier chargé par les créneaux d'équipe ; bannière brouillon pendant l'assistant d'anomalie.

## 4. Blocages
Aucun bloquant connu. Non vérifié : `lancer_demo.bat` sous Windows (pipeline équivalent exécuté ici), navigateurs autres que Chromium.

## 5. Tests réellement exécutés
| Vérification | Résultat |
|---|---|
| Suite complète SQLite, commit `8aefe10` | 3 829 tests, OK, 20 ignorés (tests propres à PostgreSQL) |
| Suite complète PostgreSQL 16, même commit | 3 829 tests, OK, 0 ignoré |
| Parcours navigateur (25 étapes, profils réels) | 25/25 conformes sur base fraîche |
| Exploration des liens (21 profils) | 0 erreur utile ; 3 « introuvables » trouvés = ANO-001, corrigés |
| Contrôles de données (reproductibilité, doublons, périmètres) | conformes après correction |
Premières exécutions du parcours : 5 étapes en échec dues à mes scripts (assistant en quatre étapes, sélecteurs) et à ANO-003 ; scripts corrigés, parcours rejoué en entier.

## 6. Avis : GO
GO pour démarrer la recette utilisateur, avec les réserves suivantes : la recette peut modifier la base de démonstration (la réinitialiser ne touche que `instance_test_marins`), les points UX ANO-007 à ANO-010 attendent vos décisions, et `lancer_demo.bat` est à confirmer lors de votre premier lancement sous Windows.
Ce n'est pas une déclaration de produit terminé : les écarts restants sont listés et le registre est fait pour être complété par vos constats.
