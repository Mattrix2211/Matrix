# Synthèse définitive de l'audit général de Matrix V1.1

**Version auditée** : `1c37f22` (branche `claude/iteration-ux-v11-20261102`), 2026-11-05. **Référence de comparaison** : `main` (`6ef16ad`), non modifiée. Aucun code applicatif n'a été modifié, rien n'a été fusionné ni déployé.

**État** : 20 audits **clôturés avec réserves**, 0 clôturé sans réserve, 0 bloqué (`09_BILAN_DES_AUDITS.md`). « Avec réserves » signifie que l'analyse technique est terminée sur le périmètre décrit ; les éléments non vérifiés sont listés et ne sont pas réputés conformes.

## En résumé

Matrix est un produit **large, très testé et fonctionnel dans ses parcours principaux** : 22 applications, ≈ 48 000 lignes, 3 829 tests verts sur SQLite et sur PostgreSQL, 11 parcours rejoués de bout en bout en navigateur sans erreur, aucune erreur serveur sur 8 468 requêtes de 61 comptes, montée de version `main` → V1.1 sans perte de données. **La V1.1 n'introduit aucune régression de droits ou de données mesurable** et corrige deux défauts de `main`. Les risques sont **préexistants** (37 anomalies sur 42) et concentrés en trois zones : **les droits suivent encore trop le niveau hiérarchique**, **les suppressions détruisent de l'information et élargissent des accès**, **la mise en service sur un vrai bord n'est pas cadrée**.

## 1. Les 20 audits et leur statut justifié

Tous : **clôturé avec réserves**, dans l'organisation en six phases de l'addendum (01 ; 19 ; 02 à 12 ; 13 à 17 ; 20 ; 18). Justification, périmètre prouvé et éléments non vérifiés, audit par audit : `09_BILAN_DES_AUDITS.md`. Rapports : `audits/AUDIT_01.md` à `AUDIT_18.md`, `audits/AUDIT_19_COHERENCE_MARINE.md` et `audits/AUDIT_20_DONNEES_DEMONSTRATION.md` (chacun se termine par une section « Clôture »). Conformité du dossier à l'addendum : `11_CONFORMITE_ADDENDUM.md`.

## 2. Anomalies confirmées et criticité (42 : 2 P0, 7 P1, 16 P2, 17 P3)

| Crit. | Anomalie | Origine |
|---|---|---|
| **P0** | **AUD-009** comptes de démonstration à mot de passe connu, sans verrou : proposition détaillée `propositions/P06` | préexistant |
| **P0** | **AUD-020** suppression d'unité : marins détachés (accès élargis), listes, annonces, documents détruits en cascade : `propositions/P07` | préexistant |
| P1 | AUD-001 création de feuille de service par tout marin | préexistant sur `main`, **corrigé en V1.1** |
| P1 | AUD-014 visas intermédiaires de la feuille donnés par niveau (COMA, commandant, administrateur d'unité, parfois seuls) | préexistant |
| P1 | AUD-015 modification directe de listes publiées par commandant et administrateurs | préexistant |
| P1 | AUD-019 structure du bord non autonome (écran : compte de flotte ; API : administrateur d'unité) | préexistant |
| P1 | AUD-011 HTTPS : un reverse proxy TLS ne fonctionne pas tel que livré ; aucun serveur d'application déclaré | préexistant |
| P1 | AUD-031 aucune procédure de sauvegarde et de restauration | préexistant |
| P1 | AUD-034 suppression d'un compte : tâches, difficultés et traçabilité détruites | préexistant |
| P2 | AUD-008, 010, 012, 017, 021, 022, 023, 024, 028, 030, 032, 033, 035, 002, 003, 006 | voir registre |
| P3 | AUD-004, 005, 007, 013, 016, 018, 025, 026, 027, 029, 036 à 042 | voir registre |

Registre complet : `04_REGISTRE_ANOMALIES_TRIE.md` (lisible) et `04_REGISTRE_ANOMALIES.csv` (toutes les colonnes, dont l'origine par rapport à `main`).

## 3. Fonctionnalités conformes et limites des preuves

| Domaine | Vérifié conforme (par exécution) | Limite de la preuve |
|---|---|---|
| Feuille de service | rédaction réservée aux rédacteurs désignés, par équipage ; visa COMAEQ strict ; circuit complet en navigateur ; lecture par état | visas intermédiaires élargis (AUD-014) ; impression et relève non rejouées |
| Délégations | remplacement de chef de liste borné (durée, passé, soi-même, bâtiment, motif, chevauchement), non transitif, expiré | seul ce mécanisme existe ; pas de délégation générale |
| Maintenance | confirmation explicite sur installation critique (API et écran) ; refus tracé | circuits de fiches non rejoués ; non-conformité sur installation sans ticket (AUD-023) |
| Stock | quantité = somme des mouvements, refus du stock négatif, motif obligatoire, immuabilité, droits | interface et alertes planifiées |
| Périmètres | aucune fuite entre bâtiments (calendrier, notifications, fils, annonces, recherche, feuilles) ni entre équipages (création, désignation) | cas limites hors des modules échantillonnés |
| Parcours du marin | tâche (démarrer, bloquer, remonter), échange, annonce avec accusé, anomalie en 4 étapes, discussion avec notification, formation, calendrier, thème sombre, mobile, impression | efficacité non mesurée par des marins |
| Données | PostgreSQL et SQLite verts ; migration d'une base peuplée sans perte | sauvegarde, charge |
| Écran « Quarts » | conforme aux deux maquettes approuvées (A, B) et à la charte | autres écrans : pas de maquette de référence |

## 4. Corrections bloquantes

- **Avant la fusion de la V1.1 dans `main`** (décision du PO) : **aucune correction bloquante** n'est introduite par la V1.1 ; la suite est verte sur les deux moteurs, la montée de version est sans perte, aucune permission n'est plus permissive qu'en `main`, et la fusion **corrige** AUD-001 et AUD-026. Recommandation d'audit : fusionner après décision du PO, **sans considérer que cela résout** les anomalies préexistantes ci-dessous.
- **Avant toute mise à disposition sur un environnement accessible ou un vrai bord** : **P0** AUD-009 et AUD-020 ; **P1** AUD-034 (même famille que AUD-020), AUD-011 et AUD-031 (déploiement et résilience), AUD-014 et AUD-015 (droits métier). Détail et ordre : `07_FEUILLE_DE_ROUTE.md`.

## 5. Améliorations pouvant attendre une version ultérieure

P2 et P3 du registre ; portée multi-sections, réorganisation assistée (fusion, scission), délégations générales, import de personnel (à planifier pour la mise en service), régimes de quart nommés et fraction de service, vue collective séparée du calendrier, prêts et retours de matériel, circuits PÉPIN, CRAT, RAV/c, organismes à terre, synchronisation bord–terre.

## 6. Décisions du PO encore nécessaires, avec recommandations

Quatre blocs dans `06_DECISIONS_PO.md` (orientations déjà prises : DP-01, DP-03, DP-09, DP-10, DP-11, DP-12, DP-13, DP-14).

| Bloc | Décisions attendues | Recommandation de l'audit |
|---|---|---|
| A. Organisation, comptes | marin transversal (secteur explicite) ; fonction « gestion de la structure » ; niveau de réorganisation ; départ d'un marin | transversal explicite avec fonction et motif ; fonction désignée ; écran de structure puis réorganisation assistée ; **désactiver** plutôt que supprimer |
| B. Droits fonctionnels | introduction (exclusion ciblée, puis fonction requise, puis délégations) ; intervention d'exception du supérieur ; publication des listes ; trois règles métier | exclusion ciblée tout de suite si autorisée, fonction requise comme cible ; exception motivée si titulaire absent ; publication par le COMAEQ et son suppléant |
| C. Déploiement et sécurité | verrou de démonstration ; autorité de certification ; serveur d'application ; sauvegarde ; limitation des connexions | verrou par couches ; avec les responsables SIC pour le reste |
| D. Périmètre produit | passation, QR, CI hors ligne, tests navigateur, chemin de non-conformité sur installation, alignement des documents | trancher la passation et les QR ; corriger au minimum le message d'AUD-023 |

## 7. Validations externes avant déploiement

1. **Responsables SIC** : architecture HTTPS de référence (`propositions/P03`), autorité de certification et durée des certificats, pare-feu local, journalisation et conservation, limitation des tentatives de connexion, politique de sécurité applicable.
2. **Exploitant** : choix et supervision du serveur d'application, procédure de sauvegarde et de restauration **testée**, reprise après redémarrage de Redis et de Celery.
3. **Expert du bord** : fidélité de la démonstration, régimes de quart réels, efficacité des parcours en situation de service.
4. **Matériel** : essais sous Windows (`.bat`), tablette tactile, lecteur d'écran, poste ancien.
5. **Données** : essai sur une base réelle anonymisée (volumétrie, migration, performances).
6. **Gouvernance** : décisions du PO ci-dessus et mise à jour du cahier des charges (DP-04).

## Les 10 questions initiales (réponses définitives avec réserves)

1. **Matrix correspond-il à l'application imaginée ?** Oui pour la vision ; trois écarts décidés (génération automatique, Rondes, QR) ; autonomie de la structure à compléter.
2. **Fonctionnalités réellement opérationnelles ?** Voir §3 : toutes celles rejouées fonctionnent ; les non rejouées sont listées dans les rapports.
3. **Un bâtiment peut-il installer, configurer et utiliser Matrix seul ?** **Pas encore** : droits et modules oui ; structure et installation de production non autonomes (AUD-019, AUD-011, AUD-031).
4. **Les marins travaillent-ils efficacement ?** Les parcours rejoués sont courts et sans erreur ; l'efficacité réelle exige des marins.
5. **Règles métier et permissions fiables ?** Le serveur refuse correctement et aucune fuite n'a été trouvée ; mais des droits par niveau restent trop larges (AUD-014, 015).
6. **Fondations techniques solides ?** Oui pour la base et la migration ; fragilités de structure du code et de suppression (AUD-020, 029, 034).
7. **Risques de régression ?** Faibles pour la V1.1 contre `main` (aucune régression mesurée) ; élevés pour les corrections à venir (260 appels de périmètre, 35 seuils) ; 13 mutations de droits (18 exécutions) : 12 tuées (dont une par un seul test) et 1 survivante dans 4 modules de test mais tuée par 161 tests de la suite complète : voir `AUDIT_16.md`.
8. **Qu'avons-nous oublié ?** Sauvegarde, mode de service de production, politique de suppression, secteurs sans section, suppléances génériques, supervision des tâches de fond, limitation des connexions.
9. **Corrections à prioriser ?** AUD-009 et AUD-020 (P0), puis AUD-034, 014, 015, 019, 011, 031 (P1).
10. **Prochaine étape raisonnable ?** Trancher les blocs de décisions, autoriser les deux P0 sur la base de `propositions/P06` et `P07`, lancer la validation SIC, puis terminer avec des marins les mesures d'efficacité.

## Pièces du dossier

`00` synthèse ; `01` référentiel ; `02` inventaire ; `03` matrice unique de conformité (exigences, règles métier Marine, couverture de la démonstration) ; `04` registre (CSV et vue triée) ; `05` non-régression ; `06` décisions ; `07` feuille de route ; `08` limites et preuves ; `09` bilan ; `10` comparaison avec `main` ; `11` conformité à l'addendum ; `audits/` (20 rapports dont les deux de l'addendum) ; `propositions/P01` à `P07` ; `sondes/` (scripts rejouables et `rejouer_tout.sh`).
