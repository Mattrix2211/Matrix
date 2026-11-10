# F. Questions résiduelles

> **Mise à jour du 10/11** : cette pièce est le détail d'origine. Le statut à jour de F-01 à F-14 (résolue / contradiction / technique / reportable) est dans `J_TRIAGE_ET_ARBITRAGES.md`. Questions réellement ouvertes : C-1 (listes de quarts et de gardes) et C-2 (autorité qui qualifie un contrôle d'appareillage). F-02 (échanges), F-06 (qualifications) et F-09 sont résolues.

Seuls figurent ici les arbitrages **réellement nécessaires**, non décidés dans S1, S2, Notion ou le dépôt. Pour chacun : le contexte, les options, ma recommandation et ses conséquences. **Aucune ne bloque la rédaction du dossier ni les étapes 1 (P0) du plan** ; la colonne « Bloque » indique à partir de quelle étape une réponse devient nécessaire.

| ID | Sujet | Bloque (étape du plan D) | Anomalies |
|---|---|---|---|
| F-01 | Mise en œuvre des droits par fonction, intervention d'exception du supérieur, phasage de la suppléance | 2 | AUD-014, 015, 022 |
| F-02 | Listes de quarts/gardes publiées et échanges de tours : qui publie, qui décide | 5 | AUD-015, 033 |
| F-03 | Rattachement du matériel : service seul, secteur obligatoire ? | 2 (transfert), 4 | AUD-037, 044 |
| F-04 | Déroulé du ticket correctif | 4 | AUD-043 |
| F-05 | Suppression d'un compte sans historique ; autorité et délai de régularisation d'une mutation | 1.3 / 6 | AUD-034 |
| F-06 | Suppléance : qualifications réglementaires, retour anticipé, activation, durée maximale | 2 | — |
| F-07 | Appareillage : qui qualifie un contrôle d'obligatoire ou de critique ; qui signe | 5 | AUD-047 |
| F-08 | Niveau d'annonce « Urgent » ou « Critique » | 7 | AUD-041 |
| F-09 | Libellé « Mes tours de service(s) » | 7 | — |
| F-10 | Structure : marin transversal, fonction de gestion de la structure, niveau de réorganisation | 2.4 | AUD-019, 037 |
| F-11 | Sécurité : limitation des connexions, serveur d'application, autorité de certification | 2.8 | AUD-011, 035 |
| F-12 | Maintenance non conforme sur installation : ticket, alerte ou rien | 4 | AUD-023 |
| F-13 | Composition-type d'une fraction de service à quai : GO d'implémentation | 5 | AUD-046 |
| F-14 | Gouvernance : CI hors Internet, tests navigateur, mise à jour de Notion | 8 | AUD-002, 003, 004 |

---

## F-01 — Droits par fonction, exception du supérieur, phasage de la suppléance

**Contexte.** S1 §4 pose le principe (droits par fonction et périmètre, administrateur technique sans validation métier). Reste : par quoi commencer et que faire si le titulaire est absent (B1, B2 de l'audit).

| Option | Description | Conséquence |
|---|---|---|
| A | Exclusion ciblée de l'administrateur technique des visas, publications, validations | Rapide, peu risquée ; ne règle pas le niveau hiérarchique |
| B | Fonction exigée par action (cible) | Correct, plus long ; dépend de la table des fonctions de chaque bâtiment |
| C | B + suppléances bornées générales | Complet ; c'est le cadre de S1 §10 |

**Recommandation.** A tout de suite (étape 2.1), puis B, puis C avec la suppléance générale de S1 §10. Exception du supérieur (B2) : autorisée **seulement si le titulaire est absent ou le poste vacant**, avec motif, notification et trace (c'est déjà la règle de N3 pour la feuille de service). **Conséquence** : sans réponse, l'étape 2.1 peut quand même partir (option A, réversible) ; B et C attendent. CT-02 est levé si vous confirmez le phasage.

## F-02 — Listes de quarts et de gardes, échanges de tours

**Contexte.** S1 §7 ne traite que la **feuille de service**. Pour les **listes de quarts/gardes**, N3 donne la création/publication au chef de liste ; AUD-015 constate des voies directes ouvertes au commandant et aux administrateurs. Pour les **échanges**, S1 dit COMAEQ ; N7 dit chef de liste habilité (CT-01).

| Option | Conséquence |
|---|---|
| 1. Chef de liste publie ; COMAEQ ou suppléant approuve ; échanges décidés par le COMAEQ | Cohérent avec S1 ; deux niveaux |
| 2. Chef de liste publie et décide les échanges (Notion) | Plus léger ; contredit S1 |
| 3. COMAEQ publie tout | Charge sur le COMAEQ |

**Recommandation.** Option 1 (S1 prime sur la tâche Notion, plus ancienne). Garder les voies D-05 A à D de Notion (proposer → valider → publier). **Conséquence** : mise à jour de la tâche Notion « Échanges de garde » ; la fermeture des voies directes d'AUD-015 devient un lot unique.

## F-03 — Rattachement du matériel

**Contexte.** DEC-ORG-03 : « toujours rattaché à une entité responsable ». Le code impose service **et** secteur (AUD-037) ; S2 fait du secteur l'échelon responsable.

| Option | Conséquence |
|---|---|
| Garder service + secteur obligatoires | Aucun changement ; bâtiments à deux niveaux impossibles |
| Secteur obligatoire, service dérivé du secteur | Supprime une redondance, évite les incohérences de filiation (AUD-044) |
| Entité responsable = service ou secteur ou section, au choix | Plus souple ; plus de cas à tester |

**Recommandation.** Secteur obligatoire, service dérivé (filiation contrôlée). **Conséquence** : migration des données ; le transfert (DEC-MAT-*) devient un changement de secteur ou de service dans une relation unique.

## F-04 — Déroulé du ticket correctif (AUD-043)

**Contexte.** Aujourd'hui, statuts arbitraires et sauts libres. **Recommandation** : rejeter les statuts inconnus immédiatement (sans risque). Pour les sauts, passer par « En test » avant « Remis en service » et mettre à jour l'état du matériel à la remise en service. Le contrôle croisé (remise en service par une autre personne que le réparateur) est optionnel : **à n'imposer que si vous le décidez**, car il alourdit le travail. **Conséquence** : sans réponse, seule la partie « rejeter les statuts inconnus » est faite.

## F-05 — Suppression d'un compte sans historique, régularisation d'une mutation

**Contexte.** DEC-MUT-07 : désactiver ou transférer. Reste deux points : (a) peut-on encore supprimer un compte **sans aucun historique** (création par erreur) ; (b) qui régularise une mutation sans réponse, après quel délai (IM-03).

**Recommandation.** (a) Oui, réservé à un administrateur d'unité, tracé. (b) L'autorité de rattachement du nouveau bâtiment (chef de service ou commandant adjoint compétent), délai configurable (7 jours par défaut proposé), justification obligatoire. **Conséquence** : sans réponse, la suppression est interdite dans tous les cas et la régularisation reste manuelle.

## F-06 — Suppléance

**Contexte.** DEC-SUP-06 : « qualifications réglementaires nécessaires à certains visas restent obligatoires », alors que DEC-QUA-01 interdit le blocage pour les tâches (CT-03).

| Option | Conséquence |
|---|---|
| Matrix **informe** (alerte visible, trace) sans bloquer | Cohérent avec DEC-QUA-01 ; responsabilité humaine |
| Matrix **bloque** les visas qui exigent une qualification | Plus strict ; une donnée périmée dans Matrix bloquerait un visa légitime |

**Recommandation.** Informer, et ne bloquer que si une fiche déclare explicitement une qualification **réglementaire** requise (configuration). **À décider aussi** : activation par le chef immédiat ou le commandant ; durée maximale (30 jours proposés, prolongeable) ; effet d'un retour anticipé (fin immédiate, récapitulatif au titulaire).

## F-07 — Appareillage : contrôles obligatoires et points critiques

**Contexte.** DEC-APP-10 et 12. Qui décide qu'un contrôle est « obligatoire » ou qu'un point est « critique non dérogeable » ?

**Recommandation.** Porter ces deux drapeaux **sur la fiche de référence** (donc validés par son circuit d'approbation, DEC-APP-03), pas dans le code. Le COMANAV est le dernier signataire (DEC-APP-02). **Conséquence** : aucun point n'est critique tant qu'une fiche approuvée ne le déclare ; le PO ou le chef de service doit donc fournir les premières fiches. La question « qui saisit » (Notion N7) se règle avec les droits de la section ou du secteur.

## F-08 — « Urgent » ou « Critique »

Le cahier (§19) dit « Critique », le code « Urgent ». **Recommandation** : « Critique », conformément au cahier. **Conséquence** : changement de libellé seulement, sans migration de données.

## F-09 — « Mes tours de service(s) »

Le code et N5 écrivent le singulier ; S1 le pluriel. **Recommandation** : « Mes tours de service » (singulier, déjà livré, aligné avec N5), sauf demande contraire. **Conséquence** : aucune.

## F-10 — Structure : marin transversal, fonction de gestion, réorganisation

**Contexte.** A1 à A3 de l'audit, non tranchés. **Recommandation de l'audit, reprise ici** : T1 (secteur entier explicite, avec garde-fous) pour le marin transversal ; fonction désignée « gestion de la structure » (l'administrateur technique peut la recevoir sans visa métier) ; écran de structure (renommer, archiver, réactiver) pour la mise en service, réorganisation assistée plus tard. **Conséquence** : sans réponse, l'étape 2.4 se limite à l'archivage effectif (AUD-028).

## F-11 — Sécurité (avec les experts SIC)

C2 (autorité de certification), C3 (serveur d'application), C4 (sauvegarde), C5 (limitation des connexions). **Pas de décision attendue du PO** : S1 §13 les réserve aux experts. À noter : la limitation des connexions (délai croissant, journalisé) et l'exigence de `DB_PASSWORD` peuvent être codées sans attendre ; les autres éléments attendent les SIC.

## F-12 — Maintenance non conforme sur installation

**Recommandation** : alerte dédiée au chef de secteur (cohérent avec DEC-ANO-04 : le chef de secteur décide d'ouvrir une anomalie), et message corrigé tout de suite. **Conséquence** : pas de ticket automatique.

## F-13 — Composition-type d'une fraction à quai

Principe validé par N8, mais « GO du PO requis » pour implémenter. **Recommandation** : composition par bâtiment et par type de fraction, signalement (pas blocage) des postes vacants à la publication. La recette V1.1 contient déjà l'exemple BRF. **Conséquence** : sans GO, rien ne change.

## F-14 — Gouvernance documentaire et CI

DP-04 (aligner Notion), DP-07 (CI sans Internet), DP-08 (tests navigateur versionnés). **Recommandation** : script local obligatoire avant fusion (suite + `makemigrations --check`), tests navigateur dans un dossier dédié, mise à jour de Notion par vos soins ou avec votre accord explicite. **Conséquence** : sans réponse, les tests restent des preuves non rejouables (AUD-003).
