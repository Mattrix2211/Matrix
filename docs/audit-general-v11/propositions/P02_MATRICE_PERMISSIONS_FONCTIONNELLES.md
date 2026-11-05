# P02 — Matrice de permissions fonctionnelles (DP-09)

**Statut : proposition d'audit, non implémentée ; aucun circuit n'est modifié.** Orientation du PO : distinguer le **titulaire** d'une fonction, son **suppléant ou délégataire** et un **supérieur hiérarchique** ; un administrateur technique n'obtient pas de droits de visa métier ; conserver contrôle et traçabilité des délégations. Sources métier : Notion « Organigramme et rôles » p.06 et p.13 (visa COMA : « aucun grade ne remplace un COMA non désigné » ; feuille : COMAEQ ou, poste vacant, commandant de l'équipage ; « les droits d'écriture se vérifient au serveur, sans les déduire du seul grade »).

## 1. Constat : aujourd'hui, les droits suivent le niveau

- 35 actions du registre de seuils, **toutes** exprimées en niveau minimal (`matrix/core/role_thresholds.py`). Comme le niveau de l'administrateur d'unité (8) dépasse celui du commandant (7), **l'administrateur d'unité franchit tous les seuils sauf ceux du compte de flotte (9)**.
- Effets mesurés (`AUDIT_06.md`, `AUDIT_09.md`, `AUDIT_12.md`) pour l'administrateur d'unité : visa « chef de secteur » et « chef de service » de la feuille, publication de listes, modification directe de listes publiées, validation de formation (qualification d'un marin), plus tous les seuils ≤ 8 du registre.
- Pour le COMANAV et le COMOPS (niveau état-major) : publication des listes de service, visas intermédiaires de la feuille, gestion du matériel, des stocks et des fiches.
- Mécanismes de fonction **déjà présents** à réutiliser : titulaire COMA par `fonction_coma` (`matrix/core/commandants_adjoints.py`), chef de liste (`ChefDeListe`) et son remplacement (`RemplacementChefDeListe`), rédacteur de la feuille (`RedacteurFeuilleService`), référent de formation (`ReferentFormation`), délégation du programme (`DelegationProgramme`), commandant de l'équipage en cas de poste COMAEQ vacant.

## 2. Définitions proposées

| Terme | Définition | Exemple |
|---|---|---|
| **Titulaire** | Personne désignée sur la fonction, pour un périmètre (bâtiment, équipage, service, secteur) | COMAEQ de l'équipage A ; chef de secteur Moteurs |
| **Suppléant** | Personne désignée **à l'avance** pour tenir la fonction pendant une indisponibilité, avec dates | remplaçant du chef de liste |
| **Délégataire** | Personne à qui le titulaire délègue **une action précise**, pour une durée et un périmètre bornés | marin BSC autorisé à rédiger la feuille |
| **Supérieur hiérarchique** | Autorité au-dessus du titulaire : **supervise (lecture, alerte)** ; n'agit à la place du titulaire que par une **intervention d'exception** (§4) | commandant |
| **Administrateur technique** | Gère la plateforme et les **désignations** ; n'exerce **aucun** acte métier | administrateur d'unité, compte de flotte |

## 3. Matrice proposée (acte métier × qui peut l'exercer)

Légende : **T** titulaire de la fonction ; **S** suppléant ou délégataire désigné ; **Sup.** intervention d'exception d'un supérieur (§4) ; **—** aucun droit ; « état actuel » = ce qui a été mesuré sur 1c37f22.

| Acte | Titulaire | Suppléant / délégataire | Supérieur | Admin. technique | État actuel (mesuré) |
|---|---|---|---|---|---|
| Rédiger / proposer la feuille de service | rédacteur BSC désigné de l'équipage | autre rédacteur désigné (délégation du COMAEQ) | — | — | **Conforme** (403 hors rédacteurs) |
| Désigner les rédacteurs | COMAEQ de l'équipage | commandant d'équipage si poste vacant | — | — | **Conforme** |
| Visa « chef de secteur » de la feuille | chef de secteur du rédacteur | suppléant désigné du chef de secteur | chef de service (Sup.) | — | Écart : COMA, commandant et admin. d'unité peuvent |
| Visa « chef de service » | chef de service du rédacteur | suppléant désigné | COMA du service (Sup.) | — | Écart : idem |
| Visa COMAEQ (final) | COMAEQ titulaire de l'équipage | commandant de l'équipage **si poste vacant** (déjà décidé) | — | — | **Conforme** |
| Publier une liste de service | COMAEQ (domaine « service courant ») | suppléant désigné | commandant (Sup.) | — | Écart : COMANAV, COMOPS, admin. d'unité |
| Proposer la modification d'une liste publiée | chef de liste | son remplaçant (existant) | — | — | Refusé au chef de liste (tâche D-05 A à faire) |
| Modifier directement une liste publiée (urgence) | — | — | commandant ou COMAEQ, **motif + justification + notification** (D-05 C) | — | Écart : commandant et admin. d'unité, sans second regard |
| Désigner les chefs de liste | chef de service / COMAEQ | — | commandant | — | Large (chefs de service, COMA, second, commandant, admin.) |
| Régler rubriques et fonctions de la feuille | COMAEQ | — | — | — | Large (idem) |
| Déclarer un mouvement du bâtiment | COMAEQ | suppléant | commandant | — | Conforme sur l'échantillon (COMAEQ, commandant) |
| Valider une qualification (formation) | référent de **cette** formation | autre référent désigné | commandant (règle documentée « COMMANDANT+ ») | — | Écart : l'admin. d'unité valide aussi |
| Clôturer une maintenance sur installation critique | exécutant habilité + confirmation tracée | — | — | — | Conforme (confirmation explicite côté API) |
| Valider fiche d'installation / article / document | circuit prévu (chef de section → secteur → service → COMA compétent) | suppléants | — | — | Non audité jusqu'au bout |
| Désigner un titulaire de fonction | chef hiérarchique direct de la fonction | — | commandant | **oui : désigne sans exercer** | partiel |
| Administrer la structure (services, secteurs, sections) | fonction habilitée « gestion de la structure » (P04) | suppléant | commandant | peut recevoir la fonction, sans visa métier | API pour admin. d'unité ; écran superutilisateur seulement |

## 4. Intervention d'exception d'un supérieur

Un supérieur peut agir à la place d'un titulaire **uniquement si** : (1) le titulaire est absent déclaré, a été désigné comme indisponible ou le poste est vacant (cas déjà décidé pour le visa COMAEQ) ; (2) un **motif** est saisi ; (3) l'acte est **identifiable** comme intervention d'exception dans l'interface, les journaux et les documents produits ; (4) le titulaire et le supérieur direct sont **notifiés** ; (5) elle ne s'applique pas aux visas de **séparation des tâches** (deux visas successifs différents, §5). Aucun grade ne remplace un titulaire présent.

## 5. Garde-fous des délégations et des suppléances

| Garde-fou | Règle |
|---|---|
| Désignation | explicite, écrite en base : qui délègue, à qui, quelle action, quel périmètre |
| Durée | début et fin obligatoires ; durée maximale configurable ; expiration automatique |
| Non transitive | un délégataire ne délègue pas |
| Pas d'auto-délégation | on ne se délègue pas à soi-même |
| Séparation des tâches | une même personne ne donne pas deux visas successifs d'un même circuit, sauf intervention d'exception motivée |
| Traçabilité | `AuditLog` : « par délégation de X », acteur réel, date, motif ; mention visible sur le document visé |
| Révocation | immédiate par le titulaire ou son supérieur ; notification de l'intéressé |
| Revue | liste des délégations actives visible du titulaire, du supérieur et de la fonction de gestion ; alerte au-delà de la durée configurée |
| Administrateur technique | peut **enregistrer** une désignation demandée par l'autorité compétente (la désignation est tracée à son nom et au nom du demandeur), jamais agir |

## 6. Conséquences de la suppression des droits « par simple niveau »

**Ce qui change pour les personnes** (liste établie par les sondes) : l'administrateur d'unité perd visas, publication, modification directe, validation de formation ; COMANAV et COMOPS perdent la publication des listes et les visas intermédiaires de la feuille ; le commandant perd l'accès « automatique » aux actes de ses subordonnés (il garde l'intervention d'exception) ; le chef de service ne vise plus « à la place » du chef de secteur sans suppléance désignée.

**Ce que cela impose** :
1. **Continuité** : sans suppléance désignée, une absence bloque un circuit. Il faut des suppléants par défaut (par fonction), l'alerte « circuit en attente depuis N heures » et l'intervention d'exception.
2. **Registre** : les 35 clés `niveau minimal` deviennent `fonction requise` + `périmètre` ; les clés de simple plancher (par exemple « écriture d'exploitation ») restent des niveaux (P05).
3. **Migration des désignations** : il faut pouvoir exprimer toutes les fonctions aujourd'hui implicites (chef de secteur « du rédacteur », COMA « du service »). Les mécanismes existants couvrent déjà COMA, chef de liste, rédacteur, référent ; manquent les suppléants génériques et les délégations bornées.
4. **Tests** : au moins 85 occurrences d'`ADMIN_NAVIRE` dans les tests et le test `test_supervision_globale_vise_secteur_et_service_pas_le_comaeq` encodent le comportement actuel ; ils sont à réécrire **avec** le changement, jamais supprimés pour obtenir du vert.
5. **Démonstration** : les comptes de démonstration doivent porter les fonctions (COMA, rédacteur, référent, suppléants).
6. **Risque de régression** élevé : toucher les seuils modifie quarts, maintenance, formation, documentation, annonces.

## 7. Options d'introduction

| Option | Principe | Avantages | Risques |
|---|---|---|---|
| **A — Exclusion ciblée** | l'administrateur technique n'obtient plus les actes de visa et de validation (liste fermée) ; le reste inchangé | rapide ; répond au besoin le plus net | laisse COMANAV/COMOPS et commandant tels quels |
| **B — Fonction requise par action** (recommandée) | chaque acte de visa/validation exige une fonction ou une désignation ; les planchers restent des niveaux | cohérent avec Notion ; supprime la classe de défauts AUD-014/015 | chantier plus large ; suppléances à concevoir |
| **C — B + délégations bornées** | B + modèle de délégation générique | couvre le terrain | le plus long |

**Recommandation** : A à court terme comme garde-fou (si le PO l'autorise), B comme cible, C après V1.1.
