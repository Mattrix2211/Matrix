# M. Plan de développement par lots

**Proposition à valider. Aucun lot n'est lancé.** Elle remplace l'ordonnancement de `D_PLAN_CORRECTION.md` (conservé pour mémoire, mais ses priorités sont corrigées par `K_PRIORITES_JUSTIFIEES.md`).

Principes : risques critiques d'abord, puis autorisations et circuits métier, puis ergonomie ; chaque lot est assez petit pour être testé, relu et validé seul ; aucun lot ne mélange sécurité et fonctionnalité nouvelle ; toute migration est annoncée ; un lot qui crée une migration, touche aux rôles ou dépasse 50 lignes suit la chaîne « grosse tâche » du dépôt (`@dev` puis `@relecteur`, 3 refus maximum). Les noms de fichiers sont ceux de `1c37f22` ; les mentions « à confirmer » sont à lever à l'ouverture du lot, par lecture du code, avant d'écrire une ligne.

Base de développement proposée : une branche issue de `1c37f22` (étape 0 du plan D). Chaque lot s'ouvre par un état initial des tests du module touché.

## Vue d'ensemble

| Phase | Lots | Objet |
|---|---|---|
| A. Risques critiques | L01 à L05 | Verrou de démonstration, archivage, suppression sûre, désactivation des comptes, configuration de production |
| B. Autorisations | L06 à L13, L21 | Administrateur technique, rattachement, suppléance, visas, échanges, RETEX, structure, transfert, sécurité d'accès |
| C. Circuits des tâches | L14 à L18 | Priorités, validation, coordinateur, bloquée/non réalisée, qualifications |
| D. Maintenance, appareillage, feuille de service | L19, L20, L22, L23, L26, L27 | Périodicité, durée, anomalies, appareillage, outillage, feuille |
| E. Ergonomie, mutation, dette | L24, L25, L28 | UX, mutation, documentation |

```
L01 ─┐
L05 ─┤ (indépendants)
L02 ─► L03 ─► L04 ─► L07 ─────────► L25 (attend l'architecture bord–terre)
L06 ─► L08 ─► L09 (attend C-1)
        ├──► L10
        ├──► L11
        └──► L23 (attend C-2)
L03 ─► L12 ; L06 ─► L13
L14, L15, L16, L17, L18 (peu liés entre eux) ─► L20 (via L17)
```

---

# Phase A — Risques critiques

## L01 — Verrou des commandes de démonstration — **premier lot recommandé**

| | |
|---|---|
| **Anomalies** | AUD-009 (P0) ; AUD-024 (noms fictifs) en lot séparé facultatif L01b |
| **Décisions appliquées** | DEC-PRE-06 ; tâche Notion « Priorité sécurité » (PO, 28/10) : refus hors DEBUG, mentions README et DEMO.md |
| **Fichiers / modules** | `matrix/core/management/commands/seed_demo.py`, `seed_demo_dense.py`, `seed_demo_mer_quai.py`, `seed_demo_metier.py` ; nouveau `matrix/core/instance_demo.py` ; `matrix/core/checks.py` ; `scripts/preparer_instance_test.py` ; `lancer_demo.bat` ; `README.md`, `docs/DEMO.md` ; les 21 fichiers de test qui appellent `seed_demo*` |
| **Dépendances** | Aucune |
| **Migrations** | Une table d'une ligne (marqueur d'instance de démonstration), additive, sans donnée modifiée (P06). Alternative sans table à étudier à la revue |
| **Risques de régression** | 21 fichiers de test appellent `seed_demo*` sous DEBUG : le garde doit reconnaître le contexte de test ; `lancer_demo.bat` et le script de recette à mettre à jour dans le même changement ; instances de démonstration existantes sans marqueur (commande explicite pour les marquer) |
| **Tests** | T-SEC-01 à 04 ; les 10 tests de P06 §5 : refus hors DEBUG, refus sans `MATRIX_INSTANCE_DEMO=1`, refus sur PostgreSQL, refus si un compte non fictif existe (sans rien créer), succès sur base vide avec écriture du marqueur, contrôle système en erreur si marqueur et production, aucune modification d'un compte homonyme, `verifier_instance` en lecture seule, script de recette de bout en bout, suites SQLite et PostgreSQL vertes |
| **Critères d'acceptation** | Aucune des 4 commandes ne s'exécute hors des conditions explicites ; une collision de nom arrête la commande sans modifier de profil ; le démarrage en production est refusé si le marqueur existe ; le chemin officiel de démonstration fonctionne ; le README ne présente que ce chemin ; relecture indépendante ; suite complète verte sur les deux moteurs |
| **Taille** | Grosse (migration) |

**Deux confirmations à donner avant lancement (valeurs par défaut proposées) :**
1. **Mots de passe.** La note Notion du 28/10 demande des « mots de passe non prévisibles ou saisis » ; P06 conserve `pass` derrière le garde et rend aléatoire seulement le compte de flotte. *Proposition* : garder P06 (un mot de passe unique et connu est acceptable sur une instance de démonstration verrouillée, afin que la démonstration reste rejouable), sauf si vous voulez des mots de passe saisis pour tous les comptes.
2. **Marqueur en base.** Acceptez-vous une migration additive d'une ligne ? *Proposition* : oui, c'est la seule façon d'empêcher qu'une base de démonstration devienne une base de production sans qu'on s'en aperçoive.

## L02 — Archivage effectif

| | |
|---|---|
| **Anomalies** | AUD-028 (P1, prérequis de L03) |
| **Décisions** | DEC-DRT-05 ; DP-13 (archiver, désactiver, renommer plutôt que supprimer) |
| **Fichiers / modules** | `org/models.py` (champs `archived`), `org/serializers.py`, `matrix/core/scopes.py` (`marins_du_perimetre`, `resoudre_affectation_dans_perimetre`), sélecteurs et formulaires d'affectation (`matrix/views.py`, `accounts/web_views.py`) ; liste exacte à confirmer par recherche des usages de `Section`, `Sector`, `Service` dans les sélecteurs |
| **Dépendances** | Aucune |
| **Migrations** | Aucune (les champs existent) |
| **Risques** | 260 appels de périmètre dans 48 fichiers : un filtre ajouté au mauvais endroit masque des données ; le mettre dans les sélecteurs communs, avec un test par module |
| **Tests** | T-ORG-02 ; tests 5, 6 et 11 de P07 §5 |
| **Critères d'acceptation** | Une unité archivée n'est plus proposée à la création ni à l'édition ; ses listes, annonces et documents restent lisibles ; archivage et réactivation idempotents ; archiver une unité occupée est refusé tant que ses marins n'ont pas de destination |
| **Taille** | Grosse (touche aux périmètres) |

## L03 — Suppression sûre des unités

| | |
|---|---|
| **Anomalies** | AUD-020 (P0), AUD-021 |
| **Décisions** | DEC-DRT-05 ; DP-13 ; P07 |
| **Fichiers / modules** | nouveau `org/structure_services.py` (`dependances`, `peut_supprimer`, `supprimer`) ; `matrix/views.py:641-675` ; `org/views.py` (`destroy` → 409) ; `org/admin.py` ; relations `on_delete` vers section, secteur, service, bâtiment portées par l'historique (listes, annonces, documents, fiches, désignations) et par `UserProfile` |
| **Dépendances** | L02 |
| **Migrations** | Oui : passage en `PROTECT` (aucune donnée modifiée, schéma neutre sur la plupart des moteurs). **Sauvegarde obligatoire avant déploiement** (AUD-031) |
| **Risques** | 9 appels de tests aux actions de suppression et 42 fichiers de test qui suppriment : à réécrire en gardant l'intention, jamais à supprimer pour obtenir du vert ; nettoyage de démonstration qui supprime aujourd'hui en cascade ; contrat de l'API (204 → 409) |
| **Tests** | T-ORG-01, T-ORG-03 ; tests 1 à 4, 7, 9, 10, 12 de P07 §5 (dont un parcours automatique des relations vers `Section`, `Sector`, `Service`, `Ship` pour interdire toute cascade vers l'historique) |
| **Critères d'acceptation** | Aucune suppression d'unité utilisée ; message en français listant les dépendances ; unité vide et jamais utilisée supprimable avec journal ; aucun marin ne change de périmètre après un refus ; plus d'erreur 500 |
| **Taille** | Grosse |

## L04 — Comptes : désactiver au lieu de supprimer

| | |
|---|---|
| **Anomalies** | AUD-034 (P0) |
| **Décisions** | DEC-MUT-06, DEC-MUT-07, DEC-DRT-05 ; Notion (02/10) : l'historique reste la propriété de l'ancien bâtiment |
| **Fichiers / modules** | `accounts/web_views.py` (`bulk_delete_users` :349-357 et suppression unitaire :~460) ; `accounts/models.py` (`AuditLog.actor`) ; `taches/models.py` (`Tache.assigne`, aujourd'hui non nul et en cascade) ; annuaire et écrans d'assignation à adapter pour masquer les comptes désactivés |
| **Dépendances** | L03 (réutilise `dependances`) |
| **Migrations** | Oui : `Tache.assigne` rendu nullable (état « non affectée à un responsable »), conservation du nom de l'auteur dans le journal d'audit |
| **Risques** | Écrans supposant qu'un compte supprimé disparaît ; affichage et statistiques des tâches non affectées ; compte désactivé encore présent dans des listes de service |
| **Tests** | T-CPT-01, 02, 03, 09 ; test 8 de P07 §5 |
| **Critères d'acceptation** | Un compte avec historique ne se supprime plus : il se désactive (réversible, tracé) ; ses tâches ouvertes sont réattribuées ou apparaissent « non affectées à un responsable » chez le chef de secteur ; l'auteur reste lisible dans l'audit ; un compte créé par erreur, sans aucun historique, reste supprimable |
| **Taille** | Grosse |

## L05 — Configuration de production minimale

| | |
|---|---|
| **Anomalies** | AUD-010, AUD-017 (P2, regroupées parce que minuscules) |
| **Décisions** | RT-04 |
| **Fichiers / modules** | `matrix/settings.py:53` et `:186`, `.env.example`, tests de configuration |
| **Dépendances / migrations** | Aucune / aucune |
| **Risques** | Un déploiement existant mal configuré cesserait de démarrer : c'est voulu, avec message clair |
| **Tests** | T-SEC-05, T-SEC-06 |
| **Critères d'acceptation** | Production refusée avec la clé d'exemple ou sans `DB_PASSWORD` dès que `DB_HOST` est défini ; le mode développement est inchangé |
| **Taille** | Petite |

---

# Phase B — Autorisations et circuits

## L06 — Exclusion de l'administrateur technique des actes métier

| | |
|---|---|
| **Anomalies** | AUD-014, AUD-015 (P1) — option A |
| **Décisions** | DEC-DRT-02, NOT-02 |
| **Fichiers / modules** | `quarts/models.py` (seuils `NIVEAU_SUPERVISION_GLOBALE_LISTE` :147, `…_FEUILLE_SERVICE` :1015 et leurs usages :270, :1974), `quarts/listes_views.py`, `quarts/feuille_service_views.py`, `matrix/core/role_thresholds.py` |
| **Dépendances / migrations** | Aucune / aucune |
| **Risques** | Un administrateur qui est aussi titulaire d'une fonction doit garder les droits de cette fonction ; tests qui encodent le comportement actuel |
| **Tests** | T-DRT-01, T-FDS-11, T-DRT-04 (non plus permissif qu'en V1.1) |
| **Critères d'acceptation** | Sans la fonction correspondante, MASTER_ADMIN et ADMIN_NAVIRE ne visent, ne publient ni ne modifient une liste publiée ; ils désignent les titulaires sans viser à leur place ; la matrice de droits n'est nulle part plus permissive |
| **Taille** | Grosse (droits) |

## L07 — Rattachement incomplet et validation des rôles

| | |
|---|---|
| **Anomalies** | — (décision DEC-DRT-06) ; dette « accounts » de Notion (rôle hors matrice, 500 sans rôle) |
| **Décisions** | DEC-DRT-06 ; Notion (28/10) : aucun accès implicite du seul fait du grade ou du rattachement |
| **Fichiers / modules** | `accounts/models.py` (périmètre déduit, :75-96), `accounts/web_views.py` (`create_user`, `edit_user`, `bulk_update_role`), `matrix/core/scopes.py`, gabarit d'accueil neutre |
| **Dépendances** | L03, L04 (l'archivage place des comptes à « compléter ») |
| **Migrations** | Probable (autorisation explicite et tracée) — à confirmer d'après P01 |
| **Risques** | Comptes existants sans unité ; 260 appels de périmètre ; démonstration |
| **Tests** | T-CPT-04, T-CPT-05, T-ORG-05 |
| **Critères d'acceptation** | Un compte à rattachement incomplet n'accède à aucune donnée opérationnelle sans autorisation explicite et tracée ; un rôle hors matrice est refusé comme à la création ; accueil neutre expliquant la démarche |
| **Taille** | Grosse |

## L08 — Suppléance explicite

| | |
|---|---|
| **Anomalies** | — (DEC-SUP) ; réduit AUD-014 |
| **Décisions** | DEC-SUP-01 à 07 ; DEC-FDS-02 ; PT-SUP-01 |
| **Fichiers / modules** | `quarts/models.py` (`RemplacementChefDeListe` :2350, à étendre), `matrix/core/commandants_adjoints.py` ; objet de suppléance (emplacement à décider à l'ouverture) ; `notifications` ; `AuditLog` |
| **Dépendances** | L06 |
| **Migrations** | Oui |
| **Risques** | Unicité du responsable actif par périmètre ; exception « COMAEQ vacant → commandant » (N3) à ne pas casser ; double équipage |
| **Tests** | T-SUP-01 à 07, T-FDS-04 |
| **Critères d'acceptation** | Suppléance explicite, temporaire (durée obligatoire, plafond configurable), limitée à une fonction et un périmètre, activée par une autorité compétente, tracée ; un seul responsable actif ; actes attribués à leur auteur ; récapitulatif au retour du titulaire |
| **Taille** | Grosse |

## L09 — Visas par fonction et listes publiées (découpé en 3)

| | |
|---|---|
| **Anomalies** | AUD-014, 015, 022, 033 |
| **Décisions** | DEC-DRT-01, DEC-FDS-02, DEC-FDS-05 ; C-1 (à arbitrer) |
| **Sous-lots** | **L09a** visas de la feuille par fonction (COMAEQ, suppléant, commandant d'équipage si poste vacant) ; **L09b** listes de quarts/gardes : proposer → valider → publier, fermeture des voies directes (tâches Notion D-05 A à D) — **attend C-1** ; **L09c** garde contre le double envoi d'un créneau (AUD-033, avec D-06) |
| **Fichiers / modules** | `quarts/models.py`, `quarts/listes_views.py`, `quarts/feuille_service_views.py`, `quarts/conflits.py` (Notion D-06 A) |
| **Dépendances** | L06, L08 ; C-1 pour L09b |
| **Migrations** | Oui pour L09b (propositions de modification) |
| **Risques** | Le plus gros risque de régression du plan : seuils de niveau utilisés par plusieurs modules ; mutation de droits (l'audit en a rejoué 13) |
| **Tests** | T-FDS-03, 04, 05, T-DRT-04 |
| **Critères d'acceptation** | Plus aucun visa ou publication obtenu par le seul niveau ; la version publiée reste active jusqu'à validation de la nouvelle |
| **Taille** | Grosse × 3 |

## L10 — Échanges de tours décidés par le COMAEQ

| | |
|---|---|
| **Anomalies** | — (DEC-FDS-07, DEC-FDS-13) |
| **Décisions** | S3 : décision finale du COMAEQ ou de son suppléant habilité ; le BSC ou le chef de liste instruit |
| **Fichiers / modules** | `quarts/echanges.py` (`peut_valider_echange` :205, `valider_echange` :342, `echanges_a_valider`), `quarts/echanges_views.py`, gabarits des échanges, notifications |
| **Dépendances** | L08 (suppléant habilité) |
| **Migrations** | Possible (étape d'instruction) — à confirmer |
| **Risques** | Le chef de liste ne voit aujourd'hui aucune demande (constat de recette, N7 28/10) : à corriger dans ce lot ; l'échange n'existe que sur les gardes, pas sur les quarts (hors lot) |
| **Tests** | T-FDS-07, T-FDS-12 |
| **Critères d'acceptation** | Le chef de liste ou le BSC instruit mais ne valide pas seul ; la décision finale est tracée et attribuée au COMAEQ ou au suppléant habilité ; historique des échanges conservé |
| **Taille** | Grosse |

## L11 — Circuit RETEX

| | |
|---|---|
| **Anomalies** | AUD-045 (P2) |
| **Décisions** | DEC-RTX-01 à 04 |
| **Fichiers / modules** | `retex/services.py` (`peut_valider` :46, `valideurs` :54, `valider` :133, `refuser`), `retex/models.py`, `retex/web_views.py`, notifications |
| **Dépendances** | L08 pour les suppléances |
| **Migrations** | Oui (étapes et versions) |
| **Risques** | Module très peu testé (5 tests) : écrire d'abord les tests du comportement actuel ; secteur sans section ; RETEX déjà publiés |
| **Tests** | T-RTX-01 à 05 |
| **Critères d'acceptation** | Auteur → chef de section si présent → chef de secteur → chef de service ; correction motivée = nouvelle version et revalidations ; on sait qui a proposé, modifié, validé, rejeté ; un habilité hors circuit ne valide pas |
| **Taille** | Grosse |

## L12 — Structure du bord par une fonction habilitée

| | |
|---|---|
| **Anomalies** | AUD-019 (P1), AUD-037 |
| **Décisions** | DEC-ORG-02, DP-13 ; F-10 (propositions T1, fonction attribuée) |
| **Fichiers / modules** | `matrix/views.py:268-290`, `org/views.py`, gabarits de réglages |
| **Dépendances** | L02, L03 |
| **Migrations** | Possible |
| **Risques** | Marin transversal et élargissement d'accès (P01) |
| **Tests** | T-ORG-04 à 07 |
| **Critères d'acceptation** | Renommer, archiver, réactiver sans supprimer, par la fonction désignée ; secteur sans section pleinement opérant |
| **Taille** | Grosse |

## L13 — Transfert de matériel

| | |
|---|---|
| **Anomalies** | AUD-044 (P2) |
| **Décisions** | DEC-MAT-01 à 04 |
| **Fichiers / modules** | `assets/` (modèles d'installation, vues) ; demande de transfert ; tâches et `logistics` liées |
| **Dépendances** | L06 ; **premier pas** : relire qui peut aujourd'hui réaffecter (non vérifié) |
| **Migrations** | Oui |
| **Risques** | Filiation service/secteur/section ; tâches ouvertes à réattribuer ; historique à conserver |
| **Tests** | T-MAT-01 à 05 |
| **Critères d'acceptation** | Intra-service : chef de service ; inter-services : les deux chefs de service puis application par l'administrateur habilité ; trace avant/après ; tâches qui suivent |
| **Taille** | Grosse |

## L21 — Sécurité d'accès (avec les SIC)

| | |
|---|---|
| **Anomalies** | AUD-035 (P2), AUD-011 (P1) |
| **Décisions** | DEC-PRE-06 ; P03 |
| **Fichiers / modules** | `accounts` (authentification), `matrix/settings.py` (`SECURE_PROXY_SSL_HEADER`, redirection) |
| **Dépendances** | Experts SIC pour la partie HTTPS ; la limitation des connexions peut partir sans eux |
| **Migrations** | Possible (compteur d'échecs) |
| **Risques** | Verrouiller un compte légitime ; boucle de redirection derrière un proxy |
| **Tests** | T-SEC-07 |
| **Critères d'acceptation** | Délai croissant configurable et journalisé ; HTTPS derrière proxy validé par les SIC |
| **Taille** | Grosse |

---

# Phase C — Circuits des tâches

Tous ces lots touchent `taches/models.py`, `taches/services.py`, `taches/web_views.py` et les gabarits de tâche. À faire **un par un**, chacun avec sa migration.

## L14 — Trois niveaux de priorité

| | |
|---|---|
| **Décisions** | DEC-TAC-04, 05, 06 |
| **Fichiers** | `taches/models.py:38-42`, `services.py`, gabarits, notifications |
| **Dépendances / migrations** | Aucune / oui (origine de la priorité) |
| **Risques** | Tris et filtres existants ; indicateurs d'accueil |
| **Tests** | T-TAC-01, 02, 04 |
| **Acceptation** | Normale, haute, urgente ; une priorité du chef de secteur ne peut pas être abaissée par le chef de section ; changement tracé et notifié |

## L15 — Validation facultative et statut « À valider »

| | |
|---|---|
| **Décisions** | DEC-CLO-01 à 05 |
| **Fichiers** | `taches/models.py` (champ + statut), `services.py`, `web_views.py`, gabarits ; garder les visas techniques en dehors |
| **Dépendances / migrations** | Aucune / oui |
| **Risques** | Statuts comptés dans les indicateurs ; ne pas confondre avec les visas techniques |
| **Tests** | T-TAC-05 à 08 |
| **Acceptation** | Case « Validation du responsable requise » ; sans elle, l'équipier termine directement ; avec elle, « À valider », approbation ou correction motivée ; le chef de secteur valide sans suppléance |

## L16 — Tâche collective : coordinateur et rang des grades

| | |
|---|---|
| **Décisions** | DEC-COL-02 à 05 ; PT-ORG-01 |
| **Fichiers** | `accounts/models.py` (`GradeChoice` : rang configurable), `taches/models.py` (coordinateur) |
| **Dépendances / migrations** | **IM-02 : l'ordre des grades est fourni par le PO** / oui |
| **Risques** | Ne jamais coder l'ordre en dur ; grades en texte libre à rapprocher du référentiel |
| **Tests** | T-TAC-09 à 11 |
| **Acceptation** | Coordinateur proposé = grade le plus élevé ; égalité → le chef choisit ; le chef peut désigner un autre ; le coordinateur ne remplace pas un visa technique |

## L17 — Tâche bloquée et « Non réalisée — À reprogrammer »

| | |
|---|---|
| **Décisions** | DEC-BLQ-01 à 05 ; PT-TAC-01 ; IM-09 |
| **Fichiers** | `taches/services.py:438-478`, réglage de bâtiment (fin de journée), tâche Celery supervisée, notifications |
| **Dépendances / migrations** | AUD-032 (supervision) / oui |
| **Risques** | Celery non garanti : prévoir l'évaluation à la lecture en secours |
| **Tests** | T-TAC-12 à 14 |
| **Acceptation** | Une tâche non terminée en fin de journée passe à un état explicite, jamais reportée en silence ; le chef débloque et reprogramme sans anomalie obligatoire |

## L18 — Qualifications : information et exigences réglementaires

| | |
|---|---|
| **Décisions** | DEC-QUA-01 à 04 ; J T-3 |
| **Fichiers** | `taches/` (affichage informatif), `training/` (lecture), circuits de visa (`assets/fiche_validation.py`), fonctions de service |
| **Dépendances / migrations** | Contenu des exigences fourni par le bord / possible |
| **Risques** | Ne jamais bloquer une tâche ordinaire ; ne bloquer que sur une exigence explicitement configurée |
| **Tests** | T-TAC-15, T-QUA-01, T-SUP-07 |
| **Acceptation** | Tâches : aucun blocage ; visas, fonctions de service, signatures officielles : refus explicite si l'exigence configurée n'est pas satisfaite |

---

# Phase D — Maintenance, appareillage, feuille de service

## L19 — Périodicités nommées et échéance

Décisions DEC-PER-01 à 04 ; fichiers `assets/models.py:96-128, 603-617`, `maintenance/` ; dépendances IM-14 ; migration probable (case « calendrier fixe ») ; tests T-MNT-01 à 05 ; acceptation : hebdomadaire à quinquennale ; échéance depuis la réalisation effective sauf calendrier fixe ; retards conservés.

## L20 — Durée estimée actualisée (option B)

Décisions DEC-DUR-01 à 07, PT-DUR-01 à 07 (**propositions techniques, non validées**) ; fichiers `assets/models.py:130, 606`, `taches/` (mesure du travail effectif), `maintenance/` ; dépendances L17 (périodes bloquées) et L19 ; migration oui (historique des estimations) ; risques : valeurs aberrantes, tâches collectives ; tests T-DUR-01 à 07 ; acceptation : durée initiale et historique conservés, médiane robuste, charge en heures-personnes séparée du temps écoulé, correction manuelle du chef de secteur prioritaire, consignes jamais modifiées. **Les paramètres sont à vérifier sur données réelles avant toute généralisation.**

## L22 — Anomalies, interventions et ticket correctif

Anomalies AUD-043, AUD-023 ; décisions DEC-ANO-01 à 05 ; fichiers `logistics/models.py` (`Anomalie` :317, `CorrectiveTicket` :23), `logistics/views.py:49-105`, `maintenance/_execute_done.html` ; dépendances IM-04, IM-15 (cartographier avant de coder) ; migration possible ; risques : liens tâche/anomalie/matériel ; tests T-ANO-01 à 04 ; acceptation : statuts inconnus rejetés, message de non-conformité corrigé et alerte au chef de secteur, clôture d'intervention indépendante de l'anomalie.

## L23 — Préparation à l'appareillage

Anomalie AUD-047 ; décisions DEC-APP-01 à 13, PT-APP-01 ; fichiers `dashboard/models.py` (`SessionAppareillage` :18), `dashboard/web_views` (ouvrir, détail, signer), `assets/` (fiches de référence) ; **attend C-2** ; migration oui ; risques : préparations en cours, signatures existantes, versions des références ; tests T-APP-01 à 09 ; acceptation : contrôles issus des fiches applicables, circuit section ou secteur → service → COMANAV, contrôles obligatoires traités avant validation, réserves explicites et tracées, contrôles critiques non contournables, actualisation par version de référence, jamais d'autorisation d'appareiller affichée. Découpage proposé : L23a contrôles issus des fiches et versions ; L23b circuit et signatures ; L23c réserves et contrôles critiques.

## L26 — Remarques d'outillage et d'instruction

Décisions DEC-OUT-01 à 05 ; nouveau modèle de remarque rattaché à la fiche (`assets/`) ; visibilité chef de secteur ; migration oui ; aucun effet automatique sur la fiche ; tests T-MNT-06 à 08.

## L27 — Feuille de service : réimpression et fraction à quai

Décisions DEC-FDS-06, 08, 09 ; fichiers `quarts/` (versions de feuille, `FonctionFeuilleService`), gabarits d'impression ; dépendance F-13 (GO du PO) pour la fraction ; tests T-FDS-06, 08, 09 ; acceptation : alerte de réimpression après nouvelle version, signalement (jamais blocage) des postes vacants.

---

# Phase E — Ergonomie, mutation, dette

## L24 — Ergonomie (plusieurs petits lots)

Décisions DEC-UX-01 à 11 ; anomalies AUD-008, 016, 018, 027, 038, 041 ; sous-lots indépendants : liens et boutons morts, titres d'onglet, libellé « Mes tours de services » (S1), niveau « Critique » (F-08), archivage des notifications lues, épinglage du menu, recherche de personnes, vue personnelle du calendrier (AUD-025). Garde-fous : ne pas dégrader recherche et menu (jugés satisfaisants, N5) ; recette visuelle du PO sur captures ; aucune migration sauf préférence d'épinglage par compte.

## L25 — Mutation de personnel — **reporté**

Décisions DEC-MUT-01 à 05 ; Notion (02/10) : formations et qualifications suivent le marin, l'historique d'activité reste à l'ancien bâtiment, les compteurs d'équité ne suivent pas. **Dépend de l'architecture bord–terre** (réservée aux SIC) et de L04, L07. Lot détaillé à écrire une fois l'architecture connue.

## L28 — Dette documentaire et CI

AUD-002, 003, 004, 005, 006, 029, 030, 036 ; script local obligatoire (CI hors Internet), tests navigateur versionnés, correction de CLAUDE.md, tests des modules secondaires, mise à jour de Notion par vos soins.

---

# Premier lot recommandé : L01

**Pourquoi L01 :**
1. C'est le seul risque critique **sans dépendance** et entièrement spécifié (P06, 10 tests).
2. Vous l'avez déjà qualifié de « risque de sécurité sérieux » (28/10).
3. Il ne change **rien** au fonctionnement des équipiers : zéro risque de contrarier une décision fonctionnelle.
4. Il est petit, relisible en une fois, et prépare le terrain de tous les lots suivants (une démonstration verrouillée évite de polluer les bases de test).
5. Les lots L02 à L04 sont plus larges (périmètres, migrations de protection), et L04 demande l'arbitrage F-05.

**Ensuite, dans l'ordre :** L05 (minuscule, à glisser entre deux lots), puis L02 → L03 → L04, puis L06.

**Ce qu'il me faut de vous pour lancer L01 :** « GO L01 », plus vos deux réponses sur les mots de passe et le marqueur en base (les valeurs par défaut ci-dessus s'appliquent sans réponse).
