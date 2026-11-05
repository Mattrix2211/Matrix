# Décisions du Product Owner

Mise à jour du 2026-11-05 (3ᵉ passe). Les points interdépendants sont regroupés en quatre blocs pour limiter les arbitrages.

## 1. Décisions déjà prises (enregistrées)

| ID | Décision | Conséquence pour l'audit |
|---|---|---|
| DP-01 | `main` n'est pas touchée ; ni fusion, ni déploiement, ni modification applicative sans autorisation explicite ; audit sur branche dédiée, référence `1c37f22` | respecté |
| DP-03 (orientation) | option B complétée par D : section absente lorsqu'un secteur n'en possède aucune ; ne pas imposer de section fictive ni élargir accidentellement les droits d'un marin transversal | règle complète proposée : `propositions/P01` |
| DP-09 (orientation) | titulaire, suppléant ou délégataire et supérieur sont distincts ; un administrateur technique n'obtient pas de droits de visa métier ; traçabilité des délégations | matrice proposée : `propositions/P02` |
| DP-10 (orientation) | architecture de référence : reverse proxy avec terminaison TLS en réseau interne, validation par les responsables SIC avant déploiement | documentée : `propositions/P03` |
| DP-11 | besoin à terme d'un import en masse (prévisualisation, doublons, validation des rattachements, rapport) ; fonctionnalité de mise en service à planifier, non bloquante V1.1 | AUD-012 reclassé |
| DP-12 | le 404 initial du signalement est « non reproduit sur la version auditée » ; anomalie distincte pour le compte rendu | AUD-026 (**le 404 existe sur `main` et est corrigé par la V1.1**, ce qui explique l'observation initiale) et AUD-027 |
| DP-13 (orientation) | gestion de l'organisation locale par des fonctions habilitées ; priorité à modifier, renommer, archiver, désactiver ; pas de suppression physique perdant l'historique ou élargissant les accès | étude : `propositions/P04` |
| DP-14 | revue au cas par cas : planchers contre règles métier | réalisée par groupes : `propositions/P05` |

## 2. Décisions encore nécessaires (regroupées)

### Bloc A — Organisation, rattachements, structure, comptes (DP-03, DP-13, DP-11, AUD-019 à AUD-021, AUD-028, AUD-034)
Les trois sujets sont interdépendants : un seul chantier cohérent est proposé.
| Question | Options | Recommandation de l'audit |
|---|---|---|
| A1. Marin transversal : secteur entier explicite (T1) ou liste de sections désignées (T2) ? | T1 maintenant, T2 après V1.1 | T1 avec garde-fous (P01 §5) |
| A2. Qui détient la fonction « gestion de la structure » à bord ? | administrateur d'unité seul ; fonction attribuable à une personne désignée (recommandé) ; commandant | fonction désignée, l'administrateur technique pouvant la recevoir sans visa métier |
| A3. Niveau de réorganisation à livrer | garde-fous minimaux (option 1) ; écran de structure (option 2, recommandée) ; réorganisation assistée (option 3) | option 2 pour la mise en service, option 3 après V1.1 |
| A4. Période de grâce pour les comptes « à compléter » | immédiate ; durée configurable (recommandé) | durée configurable |
| A6. Réaffectation d'une installation à un autre service (AUD-044, recette RM-12) | décision seule du commandant ou de l'administrateur d'unité (actuel) ; demande du service quittant acceptée par le service receveur ; accord du commandant adjoint concerné | demande + acceptation du service receveur, avec notification et trace avant/après ; contrôle de filiation service/secteur/section |
| A5. Départ d'un marin | suppression du compte (actuel) ; **désactivation** avec historique conservé (recommandé) | désactivation, suppression réservée aux comptes sans historique (`propositions/P07`) |

### Bloc B — Droits fonctionnels et délégations (DP-09, DP-14, AUD-014, AUD-015, AUD-022)
| Question | Options | Recommandation |
|---|---|---|
| B1. Introduction | A exclusion ciblée de l'administrateur technique ; B fonction requise par action ; C B + délégations bornées | A en garde-fou immédiat si autorisé, B comme cible, C après V1.1 |
| B2. Intervention d'exception du supérieur | jamais ; si titulaire absent ou vacant, avec motif et notification (recommandé) | si absent ou vacant |
| B3. Publication des listes de service | COMAEQ seul ; COMAEQ et suppléant désigné (recommandé) ; tout état-major (actuel) | COMAEQ et suppléant |
| B5. Validation d'un RETEX (AUD-045, recette RM-39) | tout habilité (actuel) ; le COMA référent du domaine seul ; le référent d'abord, puis tout habilité si le référent est absent ou n'existe pas à bord | le référent d'abord, puis tout habilité ; tri fondé sur la fonction de commandant adjoint et non sur un texte libre |
| B4. Trois règles métier à décider au cas par cas | prêt à appareiller (déjà au backlog), validation des absences, bilans de pilotage | à trancher avec la revue P05 |

### Bloc C — Déploiement et sécurité (DP-10, AUD-009, AUD-010, AUD-011, AUD-017, AUD-031)
| Question | Options | Recommandation |
|---|---|---|
| C1. Garde-fou de la démonstration | refus par défaut + variable explicite + marqueur de base + test (recommandé) | à lancer en priorité (P0) |
| C2. Autorité de certification du bord | PKI de l'organisation ; AC locale ; auto-signé (déconseillé) | à décider avec les responsables SIC |
| C3. Serveur d'application | à choisir (non déclaré aujourd'hui) | décision technique + SIC |
| C4. Sauvegarde/restauration | procédure à écrire et tester | à planifier avant mise en service |
| C5. Limitation des tentatives de connexion (AUD-035) | délai croissant ; verrouillage temporaire ; aucune (actuel) | délai croissant configurable, journalisé, à valider avec les responsables SIC |

### Bloc D — Périmètre produit et gouvernance (DP-02, DP-04 à DP-08)
| ID | Question | Recommandation |
|---|---|---|
| DP-02 | Synthèse de passation : maintenue en V1 (complément d'octobre) ou différée (bandeau du 10/10) ? | trancher et aligner Notion |
| DP-04 | Mettre à jour le cahier et la feuille de route (Rondes retirées, baseline, vocabulaire) | à faire |
| DP-05 | Données de Rondes : conserver tant qu'aucune suppression physique n'est autorisée | conserver |
| DP-06 | QR codes « hors V1 » mais route active | désactiver la route en V1 ou l'assumer |
| DP-07 | CI compatible hors Internet | serveur interne ou script local obligatoire avant fusion |
| DP-08 | Tests navigateur versionnés | oui, dans un dossier dédié |
| (nouveau) | Chemin de non-conformité sur installation (AUD-023) : ticket automatique, alerte dédiée, ou aucune action ? En attendant : corriger le message affiché | alerte dédiée au chef de secteur ; message corrigé immédiatement |
| (nouveau) | Secteur obligatoire pour une installation (AUD-037, audit 19) : le garder, ou prévoir un secteur par défaut pour les organisations à deux niveaux | à décider avec le bloc A (structure) |
| (nouveau) | Niveau d'annonce « Urgent » ou « Critique » (AUD-041) | « Critique » (terme du cahier) ou décision écrite du changement |
| (nouveau) | Déroulé du ticket correctif (AUD-043, recette RM-26) : quels sauts de statut autoriser, passage obligatoire par « En test » avant « Remis en service », remise en service par une autre personne que le réparateur, état du matériel mis à jour | rejeter les statuts inconnus tout de suite ; décision du PO sur les sauts et sur le contrôle croisé |
| (nouveau) | Composition-type d'une fraction de service à quai (AUD-046, RM-30) | GO du PO ; composition par bâtiment et par type de fraction ; signalement (pas blocage) à la publication d'une liste |
| (nouveau) | Prêt à appareiller (AUD-047, RM-41) : qui saisit, qui signe, tous les points vérifiés exigés ? | à trancher avec B4 |
| (nouveau) | Complément de la démonstration (AUD-036, 13 scénarios) | après les corrections qui changent les états ; autorisation du PO requise |

## 3. Pas de décision attendue, dépendances connues

Commandant en second (écritures), Prêt à appareiller, fraction de service (composition-type), régimes de quart, organismes à terre, PÉPIN/CRAT/RAV-c : cadrés ou différés dans Notion, non traités par l'audit.
