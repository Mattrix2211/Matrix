# A. Registre des décisions PO — part 1 : décisions des deux messages du PO

Base : V1.1 (`1c37f22`). Une décision par entrée. **Source** : S1 = message du PO « Consolidation des décisions », S2 = message de précisions ; N1 à N9 = pages Notion (voir `A_REGISTRE_DECISIONS.md` pour la légende) ; CLAUDE.md = règles du dépôt. **Statut** : « Confirmée PO » = formulée par le PO dans S1/S2 ; ce statut ne dit rien de l'état du code. **État du code** : Existe / Partiel / Absent / Non vérifié, avec preuve (`fichier:ligne` sur `1c37f22`). Les critères de validation renvoient aux tests de `E_STRATEGIE_TESTS.md`.


## Organisation et personnel

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-ORG-01 | S1 §4 | Confirmée PO | Tous | Structure : Bâtiment → Service → Secteur → Section facultative → Matériels et installations. | — | T-ORG-04, T-ORG-07 |
| DEC-ORG-02 | S1 §4 ; S2 | Confirmée PO | Chef de secteur | Un secteur peut n'avoir aucune section ; le secteur reste alors l'échelon responsable. | Pas de section fictive imposée (DP-03 option D). | T-ORG-04, T-ORG-05 |
| DEC-ORG-03 | S1 §4 | Confirmée PO | Gestionnaire matériel | Les matériels sont toujours rattachés à une entité responsable. | Ambiguïté : l'entité est-elle le service, le secteur ou la section ? (F-03) | T-ORG-07 |
| DEC-ORG-04 | S1 §4 ; N5 | Confirmée PO | Tous | Distinguer grade, fonction occupée, périmètre de responsabilité, spécialité, brevets/formations/habilitations. Les brevets ne sont pas des grades. | — | T-DRT-04 |
| DEC-ORG-05 | S1 §4 | Confirmée PO | Responsable formation | Prendre en compte FEM, BE, BAT, BS, BST et les évolutions récentes (BHT, C-CDM). | Libellés et validité exacts non fournis (IM-01). | à définir |
| DEC-ORG-06 | CLAUDE.md ; N1 §33 | Confirmée PO (Notion) | Tous | Configuration plutôt que code : aucune règle susceptible d'évoluer n'est codée en dur. | — | à définir |

## Droits

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-DRT-01 | S1 §4 | Confirmée PO | Tous | Les droits métier découlent des fonctions et des périmètres de responsabilité, pas du seul niveau hiérarchique. | — | T-DRT-04 |
| DEC-DRT-02 | S1 §4 ; DP-09 ; N1 §5 ; N3 | Confirmée PO | Admin technique | Un administrateur technique ne devient pas automatiquement autorité de validation métier ; il désigne les titulaires sans viser à leur place. | Application mécanique d'un transfert approuvé autorisée (DEC-MAT-02). | T-DRT-01, T-FDS-11 |
| DEC-DRT-03 | S1 §4 | Confirmée PO | Équipier | Consultation des documents de maintenance autorisés des autres sections du secteur ; pas de modification ni de clôture hors périmètre. | — | T-DRT-02 |
| DEC-DRT-04 | S1 §4 | Confirmée PO | Chef | Accès intersectoriels et documents sensibles : droits appropriés requis. | — | T-DRT-03 |
| DEC-DRT-05 | S1 §4 ; DP-13 ; N1 §41 | Confirmée PO | Admin / chefs | Éviter les suppressions physiques qui détruisent l'historique. | Suppression réservée aux objets sans historique (A5/P07, recommandation d'audit). | T-ORG-01, T-ORG-02, T-CPT-01 |
| DEC-DRT-06 | S1 §4 ; S2 | Confirmée PO | Autorité habilitée | Un compte dont le rattachement professionnel est incomplet n'accède pas aux informations opérationnelles d'un secteur sans autorisation. | Autorisation explicite et tracée. Remplace la grâce « immédiate/configurable » (A4) : pas de grâce implicite. | T-CPT-04, T-CPT-05 |

## Mutation et départ de personnel

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-MUT-01 | S1 §4 | Confirmée PO | Marin | Un marin conserve son compte Matrix lorsqu'il change de bâtiment. | — | T-CPT-06 |
| DEC-MUT-02 | S1 §4 | Confirmée PO | Nouveau et ancien bâtiments | Le nouveau bâtiment demande le rattachement ; l'ancien est informé et peut confirmer le départ. | — | T-CPT-06 |
| DEC-MUT-03 | S1 §4 | Confirmée PO | Autorité habilitée | Sans réponse, une autorité habilitée régularise avec justification et journalisation. | Autorité et délai non définis (IM-03). | T-CPT-07 |
| DEC-MUT-04 | S1 §4 | Confirmée PO | Système | Anciens droits retirés à la date effective de mutation ; nouveaux droits attribués selon l'affectation d'accueil. | — | T-CPT-08 |
| DEC-MUT-05 | S1 §4 | Confirmée PO | Système | L'historique est conservé. | — | T-CPT-08 |
| DEC-MUT-06 | S1 §4 | Confirmée PO | Chef de secteur | Les tâches ouvertes sont réattribuées ou signalées « non affectées à un responsable ». | — | T-CPT-09 |
| DEC-MUT-07 | S2 | Confirmée PO | Admin d'unité | Compte d'un marin quittant le bâtiment ou la Marine : désactivé ou transféré selon le cas, sans destruction d'historique. | Suppression seulement pour un compte sans historique (recommandation d'audit, à confirmer en F-05). | T-CPT-01, T-CPT-02, T-CPT-03 |

## Attribution et priorités des tâches

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-TAC-01 | S1 §5 | Confirmée PO | Chef de section | Le chef de section attribue les tâches de sa section. | — | T-TAC-03 |
| DEC-TAC-02 | S1 §5 | Confirmée PO | Chef de secteur | Le chef de secteur supervise, attribue directement et réaffecte. | — | T-TAC-04 |
| DEC-TAC-03 | S1 §5 | Confirmée PO | Chef de service | Le chef de service dispose de la supervision correspondant à sa fonction. | — | à définir |
| DEC-TAC-04 | S1 §5 | Confirmée PO | Chef | Trois priorités : normale, haute, urgente. | — | T-TAC-01 |
| DEC-TAC-05 | S1 §5 | Confirmée PO | Chef de secteur / de section | Une priorité imposée par le chef de secteur ne peut pas être abaissée par le chef de section. | — | T-TAC-02 |
| DEC-TAC-06 | S1 §5 | Confirmée PO | Système | Les changements d'attribution et de priorité sont tracés et notifiés aux personnes concernées. | — | T-TAC-04 |

## Qualifications (information, pas de blocage)

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-QUA-01 | S1 §5 | Confirmée PO | Chef | Matrix ne bloque pas l'attribution ni l'exécution d'une tâche selon formations, brevets ou habilitations ; le responsable humain choisit. | — | T-TAC-15 |
| DEC-QUA-02 | S1 §5 | Confirmée PO | Chef | Les qualifications connues peuvent être affichées à titre informatif. | — | T-TAC-15 |
| DEC-QUA-03 | S1 §5 | Confirmée PO | Système | Une information manquante ou périmée ne bloque pas l'attribution. | Les obligations réglementaires et de sécurité restent applicables hors Matrix. | T-TAC-15 |

## Tâches collectives

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-COL-01 | S1 §5 | Confirmée PO | Chef | Plusieurs marins peuvent participer à une même tâche. | — | T-TAC-09 |
| DEC-COL-02 | S1 §5 | Confirmée PO | Système | Matrix propose comme coordinateur le participant au grade le plus élevé. | Nécessite un ordre des grades (IM-02). | T-TAC-09 |
| DEC-COL-03 | S1 §5 | Confirmée PO | Chef | En cas d'égalité de grade, le chef choisit. | — | T-TAC-10 |
| DEC-COL-04 | S1 §5 | Confirmée PO | Chef | Le chef peut désigner un autre participant comme coordinateur. | — | T-TAC-10 |
| DEC-COL-05 | S1 §5 | Confirmée PO | Coordinateur | Le coordinateur peut déclarer le travail réalisé, mais ne remplace pas une autorité de visa technique. | — | T-TAC-11 |

## Clôture et validation des tâches

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-CLO-01 | S1 §5 | Confirmée PO | Chef | À la création/planification, case « Validation du responsable requise ». | — | T-TAC-05 |
| DEC-CLO-02 | S1 §5 | Confirmée PO | Équipier | Sans l'option : l'équipier termine directement ; la réalisation est enregistrée. | — | T-TAC-08 |
| DEC-CLO-03 | S1 §5 | Confirmée PO | Équipier, chef de section ou de secteur | Avec l'option : l'équipier déclare terminé, la tâche passe « À valider » ; le chef approuve ou demande une correction motivée. | — | T-TAC-05, T-TAC-06 |
| DEC-CLO-04 | S1 §5 ; S2 | Confirmée PO | Chef de secteur | Le chef de secteur valide directement, chef de section absent, sans suppléance. | — | T-TAC-07 |
| DEC-CLO-05 | S1 §5 ; S2 ; N3 | Confirmée PO | Titulaires de visa | Les visas techniques obligatoires restent distincts de la validation facultative. | — | T-TAC-11 |

## Tâches bloquées et non réalisées

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-BLQ-01 | S1 §5 | Confirmée PO | Équipier | Un équipier peut déclarer une tâche « Bloquée » avec motif. | — | T-TAC-12 |
| DEC-BLQ-02 | S1 §5 | Confirmée PO | Responsable | Le responsable est informé du blocage. | — | T-TAC-12 |
| DEC-BLQ-03 | S1 §5 | Confirmée PO | Chef | Le chef peut débloquer et reprogrammer sans obligation de créer une anomalie. | — | T-TAC-13 |
| DEC-BLQ-04 | S1 §5 | Confirmée PO | Chef de secteur | Le chef de secteur décide si un défaut technique nécessite une anomalie. | — | T-TAC-13 |
| DEC-BLQ-05 | S1 §5 | Confirmée PO | Système | Une tâche non terminée en fin de journée n'est pas reportée en silence ; état explicite « Non réalisée — À reprogrammer ». | Définition de « fin de journée » (IM-09). | T-TAC-14 |

## Maintenance périodique

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-PER-01 | S1 §5 | Confirmée PO | Système | Les tâches périodiques sont générées à partir des fiches de maintenance et des matériels concernés. | — | T-MNT-01 |
| DEC-PER-02 | S1 §5 | Confirmée PO | Chef de secteur | Périodicités : hebdomadaire, mensuelle, trimestrielle, annuelle, biennale, quinquennale. | — | T-MNT-02 |
| DEC-PER-03 | S1 §5 | Confirmée PO | Système | Prochaine échéance calculée depuis la réalisation effective, sauf calendrier fixe réglementaire ou technique. | Critère « calendrier fixe » à définir par fiche (IM-14). | T-MNT-03, T-MNT-04 |
| DEC-PER-04 | S1 §5 | Confirmée PO | Système | Les historiques sont conservés, retards compris. | — | T-MNT-05 |

## Durée estimée (option B)

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-DUR-01 | S1 §5 (option B) | Confirmée PO (principe) | Système | Matrix actualise automatiquement la durée indicative des maintenances à partir des temps réellement constatés. | Méthode statistique = proposition technique PT-DUR-*, non validée. | T-DUR-02 |
| DEC-DUR-02 | S1 §5 | Confirmée PO | Système | Conserver la durée initiale. | — | T-DUR-01 |
| DEC-DUR-03 | S1 §5 | Confirmée PO | Système | Conserver l'historique des estimations. | — | T-DUR-01 |
| DEC-DUR-04 | S1 §5 | Confirmée PO | Système | Distinguer temps écoulé et charge totale en heures-personnes. | — | T-DUR-04 |
| DEC-DUR-05 | S1 §5 | Confirmée PO | Système | Éviter que interventions exceptionnellement longues, attentes et interruptions faussent l'estimation. | — | T-DUR-03 |
| DEC-DUR-06 | S1 §5 | Confirmée PO | Chef de secteur | Le chef de secteur peut corriger manuellement la durée. | — | T-DUR-05 |
| DEC-DUR-07 | S1 §5 | Confirmée PO | Système | Ne pas modifier automatiquement consignes techniques ou de sécurité. | — | T-DUR-06 |

## Outillage et amélioration continue

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-OUT-01 | S1 §5 | Confirmée PO | Équipier | Signaler : outil manquant, inutile, inadapté, instruction ambiguë, information manquante. | — | T-MNT-06 |
| DEC-OUT-02 | S1 §5 | Confirmée PO | Chef de secteur | Remarques conservées et visibles du chef de secteur. | — | T-MNT-07 |
| DEC-OUT-03 | S1 §5 | Confirmée PO | Système | La liste d'outillage n'est jamais modifiée automatiquement. | — | T-MNT-07 |
| DEC-OUT-04 | S1 §5 | Confirmée PO | Chef | Le chef décide de modifier ou non la fiche de référence. | — | T-MNT-08 |
| DEC-OUT-05 | S1 §5 ; N3 | Confirmée PO | Chaîne de validation | Procédures techniques et de sécurité : validations applicables conservées. | — | T-MNT-08 |

## Anomalies et interventions

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-ANO-01 | S1 §6 | Confirmée PO | Chef de secteur | Anomalie = problème technique à suivre ; intervention = action effectuée pour le traiter. | Correspondance code/vocabulaire à vérifier (IM-15). | T-ANO-01 |
| DEC-ANO-02 | S1 §6 | Confirmée PO | Chef de secteur | Une anomalie peut nécessiter plusieurs interventions. | — | T-ANO-01 |
| DEC-ANO-03 | S1 §6 | Confirmée PO | Système | La clôture d'une intervention ne clôture pas automatiquement l'anomalie. | — | T-ANO-02 |
| DEC-ANO-04 | S1 §6 | Confirmée PO | Chef de secteur | Le chef de secteur décide de la suite : intervention supplémentaire, demande d'information, ouverture d'anomalie, clôture justifiée. | — | T-ANO-03 |
| DEC-ANO-05 | S1 §6 | Confirmée PO | Système | Préserver les liens tâches ↔ interventions ↔ anomalies ↔ matériels ↔ historique. | — | T-ANO-01 |

## Feuilles de service et quarts

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-FDS-01 | S1 §7 ; N8 | Confirmée PO | BSC | Le BSC prépare les feuilles de service ; il n'est pas une autorité parallèle au COMAEQ. | — | T-FDS-01, T-FDS-02 |
| DEC-FDS-02 | S1 §7 ; N3 | Confirmée PO | COMAEQ ou suppléant habilité | Le COMAEQ, ou un suppléant officiellement habilité, approuve la feuille. | COMAEQ vacant : commandant de l'équipage, de façon tracée (N3, 18-19/10). Mécanisme de suppléant officiel absent. | T-FDS-03, T-FDS-04 |
| DEC-FDS-03 | S1 §7 | Confirmée PO | Système | Après approbation, publication numérique. | — | T-FDS-03 |
| DEC-FDS-04 | S1 §7 | Confirmée PO | BSC | Le BSC assure l'impression A4 pour l'affichage. | — | à définir |
| DEC-FDS-05 | S1 §7 | Confirmée PO | BSC / COMAEQ | Une modification après publication entraîne une nouvelle version officielle. | — | T-FDS-05 |
| DEC-FDS-06 | S1 §7 | Confirmée PO | Système | Matrix signale la nécessité de réimprimer et remplacer une feuille déjà affichée. | — | T-FDS-06 |
| DEC-FDS-07 | S1 §7 | Confirmée PO | COMAEQ | Échanges de tours : circuit d'examen puis validation, décision finale du COMAEQ. | Contredit la tâche Notion « validation par le chef de liste habilité » (CT-01). | T-FDS-07 |
| DEC-FDS-08 | S1 §7 ; N8 | Confirmée PO | BSC | Les fractions de service à quai sont configurables par bâtiment. | Composition-type : GO du PO requis (AUD-046). | T-FDS-08 |
| DEC-FDS-09 | S1 §7 | Confirmée PO | BSC | Écarts signalés et justifiés, sans blocage automatique injustifié. | — | T-FDS-09 |
| DEC-FDS-10 | S1 §7 | Confirmée PO | Tous | Exigences opérationnelles et réglementaires restent applicables. | — | à définir |
| DEC-FDS-11 | S1 §7 | Confirmée PO | Équipier | La création d'une feuille n'est pas ouverte à n'importe quel équipier. | — | T-FDS-01 |
| DEC-FDS-12 | S1 §7 ; N3 | Confirmée PO | COMAEQ des deux équipages | Prendre en compte deux équipages ; chaque équipage a sa feuille, sans validation croisée par le seul grade. | — | T-FDS-10 |

## Préparation à l'appareillage

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-APP-01 | S1 §8 | Confirmée PO | Chef de secteur | Chaque départ génère des contrôles à partir des fiches de référence applicables. | — | T-APP-01 |
| DEC-APP-02 | S1 §8 | Confirmée PO | Section/secteur, Service, COMANAV | Circuit : section ou secteur → service → COMANAV. | Pas de signature intermédiaire constatée (une seule `valide_par`). | T-APP-02 |
| DEC-APP-03 | S1 §8 | Confirmée PO | Chaîne d'approbation | Les modifications des références suivent leur propre circuit d'approbation. | — | T-MNT-08 |
| DEC-APP-04 | S1 §8 | Confirmée PO | Système | Référence approuvée modifiée : les préparations ouvertes sont actualisées. | — | T-APP-06 |
| DEC-APP-05 | S1 §8 | Confirmée PO | Système | Les réponses toujours valables sont conservées. | — | T-APP-06 |
| DEC-APP-06 | S1 §8 | Confirmée PO | Système | Les contrôles modifiés ou ajoutés sont rouverts. | — | T-APP-07 |
| DEC-APP-07 | S1 §8 | Confirmée PO | Système | Les contrôles supprimés sont archivés. | — | T-APP-07 |
| DEC-APP-08 | S1 §8 | Confirmée PO | Système | Les signatures affectées sont invalidées. | — | T-APP-07 |
| DEC-APP-09 | S1 §8 | Confirmée PO | Système | Les préparations clôturées conservent leur version historique. | — | T-APP-08 |
| DEC-APP-10 | S2 | Confirmée PO | Chef de service, COMANAV | Les contrôles obligatoires sont vérifiés avant validation. | Qui qualifie un contrôle d'« obligatoire » : F-07. | T-APP-03 |
| DEC-APP-11 | S1 §8 ; S2 | Confirmée PO | Chef de secteur | Réserves justifiées possibles, gérées explicitement, dans les limites des règles de sécurité. | — | T-APP-04 |
| DEC-APP-12 | S2 | Confirmée PO | Chaîne de validation | Les points critiques non dérogeables n'admettent aucune réserve. | Qui désigne un point « critique » : F-07. | T-APP-05 |
| DEC-APP-13 | S1 §8 | Confirmée PO | Tous | Matrix ne délivre pas l'autorisation opérationnelle d'appareiller. | — | T-APP-09 |

## RETEX

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-RTX-01 | S1 §9 ; S2 | Confirmée PO | Auteur, chef de section (si présent), chef de secteur, chef de service | Circuit RETEX : auteur → chef de section si présent → chef de secteur → chef de service. | Remplace la recommandation B5 (« COMA référent d'abord »). | T-RTX-01, T-RTX-02, T-RTX-05 |
| DEC-RTX-02 | S1 §9 | Confirmée PO | Valideur | Une demande de correction doit être motivée. | — | T-RTX-03 |
| DEC-RTX-03 | S1 §9 | Confirmée PO | Auteur, valideurs | La correction entraîne une nouvelle version et les validations nécessaires. | — | T-RTX-03 |
| DEC-RTX-04 | S1 §9 | Confirmée PO | Système | Traçabilité de qui a proposé, modifié, validé ou rejeté. | — | T-RTX-04 |

## Suppléance

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-SUP-01 | S1 §10 | Confirmée PO | Autorité compétente | La suppléance est explicite, temporaire, limitée à une fonction et un périmètre, activée par une autorité compétente, traçable. | — | T-SUP-01, T-SUP-02 |
| DEC-SUP-02 | S1 §10 | Confirmée PO | Système | Une seule personne exerce la responsabilité active d'un même périmètre à un instant donné. | — | T-SUP-03 |
| DEC-SUP-03 | S1 §10 | Confirmée PO | Valideur | Le retour anticipé ou la fin de suppléance suit les règles de validation retenues. | Règles non précisées (F-06). | T-SUP-06 |
| DEC-SUP-04 | S1 §10 | Confirmée PO | Système | Les actes du suppléant restent attribués à leur auteur. | — | T-SUP-04 |
| DEC-SUP-05 | S1 §10 | Confirmée PO | Titulaire | Le titulaire retrouve un récapitulatif des actions réalisées pendant son absence. | — | T-SUP-05 |
| DEC-SUP-06 | S1 §10 | Confirmée PO | Suppléant | Les qualifications réglementaires nécessaires à certains visas restent obligatoires. | Matrix bloque-t-il ou informe-t-il ? (F-06, tension avec DEC-QUA-01). | T-SUP-07 |

## Mouvements de matériels

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-MAT-01 | S1 §11 | Confirmée PO | Chef de service | Transfert entre secteurs d'un même service : approbation du chef de service. | — | T-MAT-01 |
| DEC-MAT-02 | S1 §11 | Confirmée PO | Deux chefs de service, admin habilité | Transfert entre deux services : approbation des deux chefs de service, puis application par l'administrateur habilité. | Remplace la recommandation A6 ; « chef de service » vs « commandant adjoint » (IM-11). | T-MAT-02, T-MAT-05 |
| DEC-MAT-03 | S1 §11 | Confirmée PO | Chef de secteur | Les tâches ouvertes suivent le matériel et sont réattribuées si nécessaire. | — | T-MAT-03 |
| DEC-MAT-04 | S1 §11 | Confirmée PO | Système | L'historique des interventions et des tâches clôturées reste conservé. | — | T-MAT-04 |

## Ergonomie

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-UX-01 | S1 §12 ; N4 | Confirmée PO | Marin | À l'ouverture : tâches du jour, tours de service, actions en attente, urgences, informations utiles. | — | T-UX-01 |
| DEC-UX-02 | S1 §12 ; N5 | Confirmée PO | Tous | Éviter grands espaces vides et défilement inutile ; réduire les textes explicatifs permanents ; cartes cliquables. | Alertes et mentions réglementaires conservées (N4). | T-UX-01 |
| DEC-UX-03 | S1 §12 ; N5 | Confirmée PO | Tous | Recherche globale centrée et utile. | — | T-UX-02 |
| DEC-UX-04 | S1 §12 ; N7 | Confirmée PO | Marin | Permettre d'épingler des entrées du menu. | Notion : « IDÉE FUTURE », hors périmètre du 01/11 (CT-08). | T-UX-03 |
| DEC-UX-05 | S1 §12 | Confirmée PO | Marin | Afficher clairement les tours de service à venir, à valider et effectués. | — | T-UX-04 |
| DEC-UX-06 | S1 §12 ; N5 | Confirmée PO | Marin | Notifications lues conservées dans le centre mais retirées de la liste principale. | « Lu » ≠ « traité » (N5). | T-UX-05 |
| DEC-UX-07 | S1 §12 | Confirmée PO | Tous | Corriger les boutons inactifs et les parcours de navigation défaillants. | — | T-UX-06 |
| DEC-UX-08 | S1 §12 | Confirmée PO | Marin | Terminologie « Mes tours de services ». | Le code et N5 écrivent « Mes tours de service » (CT-06). | T-UX-04 |
| DEC-UX-09 | S1 §12 ; N7 | Confirmée PO | Chef | Recherche de personnes : informations professionnelles pertinentes, sous réserve des droits. | Notion : IDÉE FUTURE. | T-UX-07 |
| DEC-UX-10 | S1 §12 ; N4 | Confirmée PO | Utilisateur expérimenté | Interface adaptée aux utilisateurs expérimentés, sans aides envahissantes ; aide progressive réactivable. | — | T-UX-01 |
| DEC-UX-11 | S1 §12 ; N1 §15 | Confirmée PO | Marin | Le calendrier reste un élément central. | — | T-UX-08 |

## Fonctionnalités à préserver

| ID | Source | Statut | Acteurs | Règle | Exceptions / précisions | Critères de validation |
|---|---|---|---|---|---|---|
| DEC-PRE-01 | S1 §13 | Confirmée PO | Tous | Le module d'absences est limité aux corrections nécessaires (un système extérieur gère les absences). | — | T-REG-06 |
| DEC-PRE-02 | S1 §13 ; S2 | Confirmée PO | Tous | Pas de module autonome de passation ; préserver les fonctions existantes utiles. | Lève en partie AUD-006 / DP-02. | T-REG-03 |
| DEC-PRE-03 | S1 §13 | Confirmée PO | Chef | Conserver les exports PDF, Excel et CSV de pilotage, puis en améliorer la qualité. | — | T-REG-05 |
| DEC-PRE-04 | S1 §13 ; S2 | Confirmée PO | Tous | QR et inspections mobiles non prioritaires : reportés, sans suppression précipitée de l'existant. | Tranche DP-06 : la route QR reste. | T-REG-07 |
| DEC-PRE-05 | S1 §13 | Confirmée PO | Tous | Préserver le fonctionnement local sur le réseau du bord. | — | à définir |
| DEC-PRE-06 | S1 §13 | Confirmée PO | Experts SIC | Architecture de déploiement, PKI, sauvegarde et sécurité des SI : à soumettre aux experts compétents. | Aucune décision technique n'est prise ici. | à définir |
