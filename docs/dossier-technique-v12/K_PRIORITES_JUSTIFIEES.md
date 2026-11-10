# K. Priorités P0 à P3 justifiées

Cette pièce répond à la demande de justification individuelle. **Ma proposition précédente comptait 8 P0 : c'était trop large. Elle est ramenée à 3 P0**, et le classement repose sur quatre catégories qui ne confondent pas risque et fonctionnalité manquante :

- **Risque critique de sécurité ou d'intégrité des données** : perte irréversible ou compromission possible sans autre faute que l'usage normal ou une erreur plausible ;
- **Contournement majeur d'une autorisation** : un acteur obtient un droit qu'il ne devrait pas avoir ;
- **Dysfonctionnement métier important** : un parcours décidé par le PO ne fonctionne pas ou fonctionne mal ;
- **Fonctionnalité absente ou amélioration** : fonction absente, amélioration, documentation, dette.

Règles appliquées : **P0** = risque critique de sécurité ou d'intégrité, réel et mesuré ; **P1** = contournement majeur d'une autorisation, ou prérequis direct d'un P0, ou prérequis de mise en service ; **P2** = dysfonctionnement métier ou amélioration de process ; **P3** = évolution, documentation. **Une fonctionnalité manquante n'est jamais P0.** La mise en service réelle n'est pas autorisée (GO démonstration seulement, N4) : les risques liés à un déploiement réel ne sont donc pas P0 tant qu'aucun déploiement n'est prévu.

## K.1 Les 8 anciens P0, un par un

| Anomalie | Priorité audit | Ma proposition précédente | **Proposition retenue** | Catégorie | Justification |
|---|---|---|---|---|---|
| AUD-009 | P0 | P0 | **P0** | Risque critique de sécurité ou d'intégrité des données | Création possible de 61 comptes à mot de passe connu (dont un superutilisateur) sur une base réelle, et écrasement du profil d'un compte homonyme. Déjà jugé « risque de sécurité sérieux » par le PO (28/10). Conditionné à une exécution par erreur, mais sans aucun garde-fou. |
| AUD-010 | P2 | P0 | **P2** | Risque critique de sécurité ou d'intégrité des données | Durcissement : mot de passe de base par défaut faible. Conditionnel (DB_HOST défini sans DB_PASSWORD), non exploitable dans la configuration livrée. Ma proposition précédente (P0) est retirée. Lot minuscule, à grouper avec un autre lot. |
| AUD-017 | P2 | P0 | **P2** | Risque critique de sécurité ou d'intégrité des données | Une clé secrète d'exemple acceptée en production permettrait de falsifier des sessions, mais seulement si l'exploitant copie `.env.example` sans le modifier. Ma proposition précédente (P0) est retirée ; passe en P0 si une instance exposée est prévue avant correction. |
| AUD-020 | P0 | P0 | **P0** | Risque critique de sécurité ou d'intégrité des données | Suppression immédiate d'une unité : mesurée, elle détruit des listes, annonces et documents et élargit l'accès de marins détachés. Irréversible sans sauvegarde. |
| AUD-021 | P2 | P0 | **P2** | Dysfonctionnement métier important | Erreur 500 à la suppression d'un secteur portant du matériel : aucune donnée n'est perdue (la protection joue). Ma proposition précédente (P0) est retirée ; traité avec le lot de suppression. |
| AUD-028 | P2 | P0 | **P1** | Dysfonctionnement métier important | Reclassée : l'archivage sans effet est le prérequis du correctif d'AUD-020 (interdire la suppression laisse sinon le bord sans moyen de retirer une unité). Défaut fonctionnel, pas un risque de perte en soi. Ma proposition précédente (P0) est ramenée à P1. |
| AUD-031 | P1 | P0 | **P1** | Risque critique de sécurité ou d'intégrité des données | Perte de données irréversible sans sauvegarde testée, mais procédure d'exploitation et non défaut de code ; prérequis de toute mise en service. Ma proposition précédente (P0) est ramenée à l'audit (P1) car la démonstration actuelle n'a pas de données réelles. |
| AUD-034 | P1 | P0 | **P0** | Risque critique de sécurité ou d'intégrité des données | Reclassée : suppression d'un compte en un clic sans confirmation serveur ; mesurée : 6 tâches sur 37 et 3 difficultés sur 4 détruites, auteur effacé de 13 lignes d'audit, 53 créneaux sans titulaire. Perte irréversible de données et de traçabilité, même famille qu'AUD-020. |

Proposition précédente par ailleurs relevée à tort, également ramenée à l'audit : AUD-035 (P1→P2), AUD-044 (P1→P2), AUD-016 (P2→P3), AUD-037 (P2→P3), AUD-046 (P2→P3), AUD-045 et AUD-047 (P1→P2).

## K.2 Reclassements par rapport à l'audit (5)

| Anomalie | Audit | Proposé | Catégorie | Justification |
|---|---|---|---|---|
| AUD-006 | P2 | **P3** | Fonctionnalité absente ou amélioration | Reclassée : le PO a décidé (pas de module autonome, préserver l'existant). Reste l'alignement documentaire. |
| AUD-028 | P2 | **P1** | Dysfonctionnement métier important | Reclassée : l'archivage sans effet est le prérequis du correctif d'AUD-020 (interdire la suppression laisse sinon le bord sans moyen de retirer une unité). Défaut fonctionnel, pas un risque de perte en soi. Ma proposition précédente (P0) est ramenée à P1. |
| AUD-034 | P1 | **P0** | Risque critique de sécurité ou d'intégrité des données | Reclassée : suppression d'un compte en un clic sans confirmation serveur ; mesurée : 6 tâches sur 37 et 3 difficultés sur 4 détruites, auteur effacé de 13 lignes d'audit, 53 créneaux sans titulaire. Perte irréversible de données et de traçabilité, même famille qu'AUD-020. |
| AUD-045 | P3 | **P2** | Dysfonctionnement métier important | Reclassée : le circuit est maintenant décidé et le code laisse valider tout habilité, ce qui publie un RETEX hors circuit. |
| AUD-047 | P3 | **P2** | Dysfonctionnement métier important | Reclassée : un appareillage peut être signé avec des points non vérifiés ; Matrix ne délivre pas l'autorisation d'appareiller, donc pas P1. Passe en P1 quand la question de l'autorité qui définit les contrôles obligatoires sera réglée. |

Les 42 autres anomalies gardent la priorité de l'audit.

## K.3 Tableau complet des 47 anomalies

| Anomalie | Intitulé | Initiale (audit) | Proposée | Catégorie | Justification |
|---|---|---|---|---|---|
| AUD-001 | Création de feuille de service ouverte à tout marin du bâtiment (sur `main`). | P1 | **P1** | Contournement majeur d'une autorisation | Un matelot pouvait créer une feuille de service. Corrigé en V1.1 ; reste P1 tant que la V1.1 n'est pas fusionnée (DP-01). |
| AUD-002 | Aucune intégration continue (pas de `.github`). | P2 | **P2** | Fonctionnalité absente ou amélioration | Absence d'intégration continue : amélioration de process, pas un défaut en service. |
| AUD-003 | Parcours navigateur cités comme preuve absents du dépôt. | P2 | **P2** | Fonctionnalité absente ou amélioration | Preuves navigateur non rejouables : amélioration de process. |
| AUD-004 | Sources de vérité non alignées (baseline Notion du 10/10 sur `dfd6a3c`, `main` à `6ef16ad`, V1.1 à `1c37f22`). | P3 | **P3** | Fonctionnalité absente ou amélioration | Documentation Notion non alignée. |
| AUD-005 | `CLAUDE.md` présente `RoleLevel` / `RolePermission` comme points d'extension. | P3 | **P3** | Fonctionnalité absente ou amélioration | Formulation de CLAUDE.md. |
| AUD-006 | Décisions contradictoires sur la synthèse de passation. | P2 | **P3** | Fonctionnalité absente ou amélioration | Reclassée : le PO a décidé (pas de module autonome, préserver l'existant). Reste l'alignement documentaire. |
| AUD-007 | Résidu de Rondes : `rondes/models.py` et migrations sans test. | P3 | **P3** | Fonctionnalité absente ou amélioration | Résidu volontairement conservé (données et migrations). |
| AUD-008 | Carte « À faire » : bouton « Ouvrir » vers une page introuvable (ticket assigné à un chef). | P2 | **P2** | Dysfonctionnement métier important | Bouton « Ouvrir » vers une page introuvable ; aucune perte de donnée. |
| AUD-009 | Commandes `seed_demo*` : comptes à mots de passe connus, sans garde-fou. | P0 | **P0** | Risque critique de sécurité ou d'intégrité des données | Création possible de 61 comptes à mot de passe connu (dont un superutilisateur) sur une base réelle, et écrasement du profil d'un compte homonyme. Déjà jugé « risque de sécurité sérieux » par le PO (28/10). Conditionné à une exécution par erreur, mais sans aucun garde-fou. |
| AUD-010 | Mot de passe PostgreSQL par défaut faible (`matrix`). | P2 | **P2** | Risque critique de sécurité ou d'intégrité des données | Durcissement : mot de passe de base par défaut faible. Conditionnel (DB_HOST défini sans DB_PASSWORD), non exploitable dans la configuration livrée. Ma proposition précédente (P0) est retirée. Lot minuscule, à grouper avec un autre lot. |
| AUD-011 | HTTPS : reverse proxy TLS non supporté tel que livré ; serveur d'application non déclaré. | P1 | **P1** | Risque critique de sécurité ou d'intégrité des données | Déploiement derrière un proxy TLS non supporté tel que livré. Bloquant pour une mise en service, pas pour la démonstration actuelle. À valider avec les SIC. |
| AUD-012 | Pas d'import en masse du personnel. | P2 | **P2** | Fonctionnalité absente ou amélioration | Import en masse : besoin confirmé, fonction absente. |
| AUD-013 | Rapport de bilan : 1,2 à 1,3 s en médiane. | P3 | **P3** | Fonctionnalité absente ou amélioration | Mesure sans défaut établi. |
| AUD-014 | Visas intermédiaires de la feuille de service attribués par niveau hiérarchique. | P1 | **P1** | Contournement majeur d'une autorisation | Visas intermédiaires obtenus par le niveau hiérarchique et non par la fonction. |
| AUD-015 | Modification directe de listes publiées par commandant et administrateurs. | P1 | **P1** | Contournement majeur d'une autorisation | Un commandant ou un administrateur modifie directement une liste publiée, hors circuit. |
| AUD-016 | Liens ou boutons affichés à des profils sans droit. | P3 | **P3** | Fonctionnalité absente ou amélioration | Lien affiché sans droit : refus côté serveur, donc gêne seulement. |
| AUD-017 | Clé secrète d'exemple (`change-me`) acceptée en production. | P2 | **P2** | Risque critique de sécurité ou d'intégrité des données | Une clé secrète d'exemple acceptée en production permettrait de falsifier des sessions, mais seulement si l'exploitant copie `.env.example` sans le modifier. Ma proposition précédente (P0) est retirée ; passe en P0 si une instance exposée est prévue avant correction. |
| AUD-018 | Même titre d'onglet `Matrix` partout. | P3 | **P3** | Fonctionnalité absente ou amélioration | Titre d'onglet. |
| AUD-019 | Structure du bord non modifiable de façon autonome (écran réservé flotte, API admin d'unité). | P1 | **P1** | Dysfonctionnement métier important | Un bord ne peut pas gérer sa structure seul. Bloquant pour la mise en service autonome. |
| AUD-020 | Suppression de section, secteur, service : marins détachés, cascade destructrice. | P0 | **P0** | Risque critique de sécurité ou d'intégrité des données | Suppression immédiate d'une unité : mesurée, elle détruit des listes, annonces et documents et élargit l'accès de marins détachés. Irréversible sans sauvegarde. |
| AUD-021 | Erreur 500 (ProtectedError) à la suppression d'un secteur/service portant du matériel. | P2 | **P2** | Dysfonctionnement métier important | Erreur 500 à la suppression d'un secteur portant du matériel : aucune donnée n'est perdue (la protection joue). Ma proposition précédente (P0) est retirée ; traité avec le lot de suppression. |
| AUD-022 | 55 comparaisons de niveau en dur contre 71 appels à des seuils configurables. | P2 | **P2** | Contournement majeur d'une autorisation | Hypothèse d'audit non établie ; à confirmer cas par cas. |
| AUD-023 | Maintenance non conforme sur installation : ni ticket ni alerte ; message trompeur. | P2 | **P2** | Dysfonctionnement métier important | Message trompeur sur un ticket jamais créé. |
| AUD-024 | Noms réels de bâtiments dans la démonstration. | P2 | **P2** | Fonctionnalité absente ou amélioration | Noms réels de bâtiments dans la démonstration (demande du PO, 28/10). |
| AUD-025 | Flux calendrier par défaut contenant les quarts d'autres marins. | P3 | **P3** | Dysfonctionnement métier important | Hypothèse de fuite de vue calendrier, non vérifiée. |
| AUD-026 | 404 à la reprise d'un brouillon de signalement d'anomalie. | P3 | **P3** | Dysfonctionnement métier important | Corrigé en V1.1. |
| AUD-027 | Reprise d'un brouillon de compte rendu dont l'occurrence a disparu : page introuvable. | P3 | **P3** | Dysfonctionnement métier important | Brouillon mort ; aucun risque de données. |
| AUD-028 | L'archivage d'un bâtiment, service, secteur, section n'a aucun effet. | P2 | **P1** | Dysfonctionnement métier important | Reclassée : l'archivage sans effet est le prérequis du correctif d'AUD-020 (interdire la suppression laisse sinon le bord sans moyen de retirer une unité). Défaut fonctionnel, pas un risque de perte en soi. Ma proposition précédente (P0) est ramenée à P1. |
| AUD-029 | Fonctions de complexité excessive (jusqu'à 101). | P3 | **P3** | Fonctionnalité absente ou amélioration | Dette de structure du code. |
| AUD-030 | Modules documentation, RETEX, postes, programme peu testés. | P2 | **P2** | Fonctionnalité absente ou amélioration | Hypothèse de lacune de tests. |
| AUD-031 | Aucune procédure de sauvegarde et de restauration. | P1 | **P1** | Risque critique de sécurité ou d'intégrité des données | Perte de données irréversible sans sauvegarde testée, mais procédure d'exploitation et non défaut de code ; prérequis de toute mise en service. Ma proposition précédente (P0) est ramenée à l'audit (P1) car la démonstration actuelle n'a pas de données réelles. |
| AUD-032 | Sans Redis/Celery, aucune alerte automatique ni signalement. | P2 | **P2** | Dysfonctionnement métier important | Supervision de Celery. |
| AUD-033 | Double envoi de « ajouter un créneau » : deux créneaux identiques. | P2 | **P2** | Dysfonctionnement métier important | Doublon de créneau, sans perte. |
| AUD-034 | Suppression physique de compte : tâches, difficultés, traçabilité détruites. | P1 | **P0** | Risque critique de sécurité ou d'intégrité des données | Reclassée : suppression d'un compte en un clic sans confirmation serveur ; mesurée : 6 tâches sur 37 et 3 difficultés sur 4 détruites, auteur effacé de 13 lignes d'audit, 53 créneaux sans titulaire. Perte irréversible de données et de traçabilité, même famille qu'AUD-020. |
| AUD-035 | Aucune limitation des tentatives de connexion. | P2 | **P2** | Risque critique de sécurité ou d'intégrité des données | Durcissement d'authentification à valider avec les SIC. Ma proposition précédente (P1) est ramenée à l'audit. |
| AUD-036 | Démonstration sans de nombreux états et cas limites. | P3 | **P3** | Fonctionnalité absente ou amélioration | Démonstration incomplète. |
| AUD-037 | Installation : service ET secteur obligatoires. | P3 | **P3** | Fonctionnalité absente ou amélioration | Décision manquante ; pas de défaut. |
| AUD-038 | Notifications à deux états seulement ; pas d'archivage. | P3 | **P3** | Fonctionnalité absente ou amélioration | Archivage des notifications. |
| AUD-039 | Rappels évalués à la lecture des pages, sans tâche planifiée. | P3 | **P3** | Dysfonctionnement métier important | Rappels évalués à la lecture. |
| AUD-040 | Prêts, retours, inventaires de matériel absents. | P3 | **P3** | Fonctionnalité absente ou amélioration | Report volontaire. |
| AUD-041 | Niveaux d'annonce « Information / Important / Urgent » au lieu de « Critique ». | P3 | **P3** | Fonctionnalité absente ou amélioration | Vocabulaire. |
| AUD-042 | Deux écarts d'interface des quarts, décision UX ouverte. | P3 | **P3** | Fonctionnalité absente ou amélioration | Décision UX ouverte. |
| AUD-043 | Ticket correctif : sauts de statut libres, état du matériel inchangé. | P2 | **P2** | Dysfonctionnement métier important | Déroulé du ticket non contraignant. Ma proposition précédente est inchangée. |
| AUD-044 | Réaffectation d'une installation sans circuit, notification, trace ni contrôle de filiation. | P2 | **P2** | Dysfonctionnement métier important | Réaffectation sans circuit ni trace. Je n'ai pas vérifié qui peut aujourd'hui réaffecter ; si l'accès est large, le reclasser en P1. Ma proposition précédente (P1) est ramenée à l'audit. |
| AUD-045 | RETEX : « COMA référent » = simple tri ; tout habilité valide. | P3 | **P2** | Dysfonctionnement métier important | Reclassée : le circuit est maintenant décidé et le code laisse valider tout habilité, ce qui publie un RETEX hors circuit. |
| AUD-046 | Composition-type d'une fraction à quai absente ; poste en texte libre. | P3 | **P3** | Fonctionnalité absente ou amélioration | GO du PO requis ; ma proposition précédente (P2) est ramenée à l'audit. |
| AUD-047 | Prêt à appareiller signé avec points non vérifiés. | P3 | **P2** | Dysfonctionnement métier important | Reclassée : un appareillage peut être signé avec des points non vérifiés ; Matrix ne délivre pas l'autorisation d'appareiller, donc pas P1. Passe en P1 quand la question de l'autorité qui définit les contrôles obligatoires sera réglée. |

## K.4 Répartition

| Priorité | Nombre | Anomalies |
|---|---|---|
| P0 | 3 | 009, 020, 034 |
| P1 | 7 | 001, 011, 014, 015, 019, 028, 031 |
| P2 | 18 | 002, 003, 008, 010, 012, 017, 021, 022, 023, 024, 030, 032, 033, 035, 043, 044, 045, 047 |
| P3 | 19 | 004, 005, 006, 007, 013, 016, 018, 025, 026, 027, 029, 036, 037, 038, 039, 040, 041, 042, 046 |

## K.5 Fonctionnalités décidées et absentes du code (hors audit)

Priorités à trois niveaux, validation de tâche, coordinateur, « Non réalisée », périodicités nommées, durée actualisée, remarques d'outillage, intervention distincte de l'anomalie, mutation, transfert de matériel, suppléance générale : **catégorie « fonctionnalité absente », jamais P0**. Elles sont ordonnancées par le plan de développement (`M_PLAN_DEVELOPPEMENT.md`) selon leurs dépendances, pas selon une criticité de sécurité.
