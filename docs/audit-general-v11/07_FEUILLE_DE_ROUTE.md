# Feuille de route priorisée des corrections (propositions, aucune n'est lancée)

Priorité fondée sur l'impact, pas sur la facilité (définitions du PO) : **P0** bloquant (sécurité, intégrité, perte d'information, processus essentiel impossible) ; **P1** critique métier (permissions incorrectes, fonction obligatoire non conforme, parcours essentiel défaillant) ; **P2** amélioration importante ; **P3** évolution. Aucun développement n'est lancé sans l'accord du PO ; chaque ligne renvoie à une anomalie (`04_REGISTRE_ANOMALIES_TRIE.md`) et à une proposition.

## P0 — à traiter avant toute mise à disposition sur un environnement accessible

| Ordre | Travail | Anomalie | Proposition | Pourquoi |
|---|---|---|---|---|
| 1 | Verrou des commandes de démonstration (refus par défaut, variable explicite, marqueur de base, test) | AUD-009 | `audits/AUDIT_15.md` §2 | comptes à mot de passe connu : risque de sécurité sérieux (déjà identifié par le PO) |
| 2 | Plus de suppression physique d'une unité ayant un historique ; message clair à la place de l'erreur 500 | AUD-020, AUD-021 | `propositions/P04` option 1 | perte silencieuse de listes, annonces, documents ; élargissement des accès |

## P1 — critique métier

| Ordre | Travail | Anomalie | Proposition |
|---|---|---|---|
| 3 | Exclure l'administrateur technique des visas, publications et validations métier (garde-fou immédiat, option A) | AUD-014, AUD-015 | `propositions/P02` §7 |
| 4 | Droits par fonction pour les actes de visa et de publication (option B) avec suppléances et intervention d'exception | AUD-014, AUD-015, AUD-022 | `propositions/P02`, `P05` |
| 5 | Écran de structure habilité : renommer, archiver, réactiver ; archivage effectif | AUD-019, AUD-028 | `propositions/P04` option 2 |
| 6 | Installation de référence derrière reverse proxy TLS (réglages pilotables, serveur d'application, installation testée) | AUD-011 | `propositions/P03` |
| 7 | Procédure de sauvegarde et de restauration testée | AUD-031 | à rédiger |
| 8 | Décider du sort de `main` (la V1.1 corrige AUD-001) quand le PO l'autorisera | AUD-001 | `06_DECISIONS_PO.md` (DP-01 : `main` intacte) |

## P2 — amélioration importante

États de rattachement et validation des périmètres (P01) ; masquage des liens dérivé de la règle serveur (AUD-008, AUD-016) ; mot de passe PostgreSQL obligatoire (AUD-010) ; clé secrète d'exemple refusée (AUD-017) ; chemin de non-conformité sur installation (AUD-023) ; noms de bâtiments fictifs (AUD-024) ; tâches planifiées supervisées (AUD-032) ; import de personnel (DP-11, AUD-012, **fonctionnalité de mise en service à planifier**) ; CI hors ligne et tests navigateur versionnés (AUD-002, AUD-003) ; tests des modules secondaires (AUD-030) ; passation à trancher (AUD-006).

## P3 — évolution ou hygiène

Titres d'onglet distincts (AUD-018) ; reprise de brouillon morte (AUD-027) ; vue personnelle par défaut du calendrier (AUD-025, hypothèse) ; PDF du bilan en tâche de fond si besoin (AUD-013) ; découpage des vues géantes et nettoyage (AUD-029) ; alignement des documents (AUD-004, AUD-005) ; résidu Rondes (AUD-007).

## À reporter après V1.1 (évolutions, décisions déjà validées ou cadrées)

Réorganisation assistée (fusion, scission, déplacement ; `P04` option 3) ; portée multi-sections (`P01` T2) ; délégations bornées générales (`P02` option C) ; régimes de quart nommés, « hommes morts », « de musique », composition-type de la fraction de service (cadrage Notion, pas de GO) ; vue collective du calendrier séparée ; prêts, retours et inventaires de matériel ; organismes à terre et circuits PÉPIN, CRAT, RAV/c ; adjudant de compagnie et OSS ; synchronisation bord–terre (Phase 7).

## Ordre d'exécution recommandé

1 et 2 en parallèle ; puis 3 ; 6 et 7 en parallèle de 4 et 5 (indépendants, dépendent des responsables SIC) ; 4 avant 5 (la fonction de gestion de la structure s'appuie sur les désignations). Chaque correction ajoute son test à la suite et rejoue les sondes de `05_MATRICE_NON_REGRESSION.md` sur SQLite et PostgreSQL.
