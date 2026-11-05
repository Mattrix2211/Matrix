# Synthèse exécutive de l'audit général de Matrix V1.1

**Version auditée** : commit `1c37f22` (branche `claude/iteration-ux-v11-20261102`), le 2026-11-05. `main` (`6ef16ad`) n'est pas touchée ; elle est 117 commits derrière. **État de l'audit : 1 audit clos avec réserves, 19 partiels** (`09_BILAN_DES_AUDITS.md`). Ce n'est donc pas un diagnostic final : c'est le diagnostic vérifiable à ce stade, avec ses limites.

## En une page

Matrix est un produit **large et sérieusement testé** (22 applications, ≈ 48 000 lignes, 3 829 tests verts sur SQLite **et** PostgreSQL 16, aucune erreur serveur sur 8 468 requêtes de 61 comptes). Les circuits qui comptent le plus pour le bord (feuille de service, confirmation sur maintenance critique, stock, étanchéité entre bâtiments et entre équipages) **fonctionnent comme prévu**. Les fragilités sont ailleurs : **les droits suivent encore trop le niveau hiérarchique**, **l'organisation du bord est modifiable mais mal protégée**, et **la mise en service sur un vrai bord n'est pas cadrée**.

## Les 10 questions

1. **Matrix correspond-il toujours à l'application imaginée au départ ?** Oui pour la vision (plateforme quotidienne, calendrier central, configuration, traçabilité, sans Internet). Trois écarts sont voulus et documentés (génération automatique des tours abandonnée, Rondes retirées, QR hors V1 mais route encore active). L'administration distribuée est partiellement tenue (structure non autonome). Réponse provisoire : le backlog n'est pas relu ligne à ligne.
2. **Quelles fonctionnalités sont réellement opérationnelles ?** Rejouées avec succès : accueil, circuit complet de la feuille de service (5 acteurs, du brouillon à la publication, en navigateur), droits de rédaction, visa COMAEQ, désignations par équipage, confirmation des maintenances critiques, stock et inventaire, notifications et annonces par périmètre, calendrier à 7 sources, validation de qualification par référent, PostgreSQL. Non rejouées : échanges de service, fiches de maintenance et catalogue, documentation, RETEX, import, mobile (hors affichage), impression.
3. **Un bâtiment peut-il installer, configurer et utiliser Matrix seul ?** **Pas encore.** Il règle ses droits et ses modules, mais la structure (services, secteurs, sections) se modifie par un compte de flotte ou par une API ; aucune procédure d'installation en production (HTTPS derrière un proxy ne fonctionne pas tel que livré, aucun serveur d'application déclaré, aucune sauvegarde écrite) ; pas d'import du personnel (besoin confirmé, à planifier).
4. **Les marins peuvent-ils travailler efficacement au quotidien ?** L'accueil, les menus et les quarts sont lisibles et proches des maquettes approuvées ; plusieurs liens mènent à un refus (démonstration complète : 5 familles). L'efficacité (temps de saisie, nombre de clics) n'est **pas mesurée**.
5. **Les règles métier et les permissions sont-elles fiables ?** Le **serveur** refuse correctement (aucune faille d'accès entre bâtiments ou équipages trouvée). Mais certaines règles sont **trop larges par construction** : l'administrateur d'unité, le commandant et les COMA peuvent donner des visas intermédiaires, parfois seuls, et modifier directement des listes publiées (AUD-014, AUD-015).
6. **Les fondations techniques sont-elles solides ?** Oui pour la base (PostgreSQL et SQLite verts, verrous, historique immuable du stock) ; fragilités : 8 fonctions de complexité extrême, 86 imports inutiles, suppression physique en cascade, archivage sans effet, aucun test navigateur ni intégration continue.
7. **Quels risques de régression subsistent ?** Élevés dès qu'on touche aux seuils, au périmètre ou aux unités : 260 appels de périmètre dans 48 fichiers et 35 actions de seuil (`05_MATRICE_NON_REGRESSION.md`).
8. **Qu'avons-nous oublié ?** Une procédure de sauvegarde, un mode de service de production, un test de réorganisation, la couverture des secteurs sans section et des marins transversaux, des suppléances, la supervision des tâches de fond.
9. **Quelles corrections prioriser ?** P0 : verrou de la démonstration (AUD-009), plus de suppression physique d'unités avec historique (AUD-020). P1 : droits par fonction, écran de structure, HTTPS de référence, sauvegarde, sort de `main`. Détail : `07_FEUILLE_DE_ROUTE.md`.
10. **Quelle est la prochaine étape raisonnable ?** (1) trancher les quatre blocs de décisions (`06_DECISIONS_PO.md`) ; (2) autoriser les deux corrections P0 ; (3) faire valider l'architecture HTTPS par les responsables SIC ; (4) terminer les parcours navigateur restants avec un marin utilisateur.

## Ce qui fonctionne réellement, ce qui est incomplet, ce qui régresse

- **Fonctionne** : voir question 2. **Incomplet** : prêts/retours de matériel, régimes de quart nommés, vue collective séparée du calendrier, import du personnel, réorganisation assistée. **Ne respecte pas l'expression de besoin** : autonomie de la structure (AUD-019), droits par fonction (AUD-014, 015). **A régressé** : aucune régression prouvée par comparaison de versions (l'audit ne compare pas deux commits) ; la V1.1 **corrige** AUD-001 par rapport à `main`.
- **Difficile à utiliser** : liens refusés (AUD-016), cartes « Reprendre » mortes (AUD-027), titres d'onglet identiques (AUD-018). **Nécessite encore un développeur** : toute réorganisation par l'écran (compte de flotte), l'installation en production, l'import du personnel.
- **Peut attendre après V1.1** : voir la dernière section de la feuille de route.

## Anomalies bloquantes et corrections recommandées (32 anomalies : 2 P0, 6 P1, 14 P2, 10 P3)

| Crit. | Anomalie | Correction recommandée |
|---|---|---|
| **P0** | AUD-009 — comptes de démonstration à mot de passe connu, sans garde-fou | verrou par couches (`AUDIT_15.md` §2) |
| **P0** | AUD-020 — suppression d'unité : marins détachés (accès élargis) et cascade sur listes, annonces, documents | interdire la suppression avec historique ; assistant de transfert (P04) |
| P1 | AUD-014, AUD-015 — visas et modifications de listes publiées par niveau | matrice fonctionnelle (P02) |
| P1 | AUD-019 — structure non autonome | écran habilité (P04) |
| P1 | AUD-011 — HTTPS derrière proxy non opérationnel, pas de serveur d'application | installation de référence (P03) |
| P1 | AUD-031 — pas de sauvegarde écrite | procédure testée |
| P1 | AUD-001 — corrigé sur la V1.1, pas sur `main` | à décider quand le PO autorisera la fusion |

Registre complet trié : `04_REGISTRE_ANOMALIES_TRIE.md` ; version détaillée : `04_REGISTRE_ANOMALIES.csv`.

## Décisions encore nécessaires

Quatre blocs (`06_DECISIONS_PO.md`) : A organisation et rattachements ; B droits fonctionnels ; C déploiement et sécurité ; D périmètre produit.

## Pièces du dossier

`01` référentiel (48 exigences) ; `02` inventaire ; `03` matrice de conformité (48 lignes) ; `04` registre ; `05` non-régression ; `06` décisions ; `07` feuille de route ; `08` limites et preuves ; `09` bilan ; `audits/AUDIT_01` à `AUDIT_20` ; `propositions/P01` à `P05` ; `sondes/` (scripts rejouables).
