# J. Triage des contradictions et des questions résiduelles

Mise à jour après votre message du 10/11 (S3). Cette pièce remplace, pour le suivi, les statuts de `I_CONTRADICTIONS_ET_MANQUES.md` et de `F_QUESTIONS_RESIDUELLES.md` (qui restent le détail d'origine). **Règle appliquée : une note Notion plus ancienne ne prévaut pas sur une décision PO plus récente et explicite.** Pour chaque entrée :

- **R** = déjà résolue par une décision PO ;
- **C** = contradiction réelle, arbitrage du PO nécessaire ;
- **T** = question technique : je propose une solution ;
- **E** = évolution pouvant être reportée.

## J.1 Résultat en une ligne

Sur 12 contradictions, 15 informations manquantes et 14 questions : **2 contradictions réelles** (C-1, C-2) et **1 dépendance externe** (architecture bord–terre, pour la mutation). Tout le reste est résolu, technique ou reportable.

## J.2 Notes Notion plus anciennes remplacées par une décision PO plus récente

| Note Notion | Date | Remplacée par | Conséquence |
|---|---|---|---|
| « Échanges de garde : validation par le chef de liste habilité » | 28/10 | S3 (10/11) : décision finale du COMAEQ ou de son suppléant habilité ; le chef de liste ou le BSC instruit | DEC-FDS-07 et DEC-FDS-13 ; la tâche Notion est à aligner par vos soins |
| « Pas de nouveau système de délégation en V1 » (N3) | octobre | S1 §10 et S3 : suppléance validée en principe ; la note vise le périmètre et le calendrier | DEC-SUP-07 ; la suppléance est un lot, pas une annulation |
| « Veille d'appareillage : chantier futur, ne pas développer » | 20/10 | S1 §8, S2, S3 : circuit, contrôles, réserves, points critiques | Le calendrier reste à votre main ; les règles sont retenues |
| Cahier §14 (échange impossible si non habilité) | 10/10 | S3 : pas de blocage pour les tâches ordinaires ; exigences réglementaires pour visas, fonctions de service, signatures officielles | DEC-QUA-01, DEC-QUA-04 |
| Recommandation d'audit B5 (« COMA référent d'abord ») | 05/11 | S1 §9, S2, S3 : circuit hiérarchique | DEC-RTX-01 |
| A4 (période de grâce), A5 (suppression), A6 (acceptation du service receveur) | 05/11 | S1, S2 | DEC-DRT-06, DEC-MUT-07, DEC-MAT-* |

À l'inverse, **deux notes Notion antérieures confirment vos règles** et sont conservées : mutation du 02/10 (formations et qualifications suivent le marin ; l'historique d'activité reste la propriété de l'ancien bâtiment ; les compteurs d'équité ne suivent pas) et rattachement obligatoire du 28/10 (aucun accès implicite du seul fait du grade).

## J.3 Les contradictions

| ID | Sujet | Classe | Traitement |
|---|---|---|---|
| CT-01 | Échanges : COMAEQ ↔ chef de liste | **R** | S3. Code actuel : `peut_valider_echange` donne la validation à qui gère la liste (quarts/echanges.py:205). Lot L10. |
| CT-02 | Suppléance ↔ « pas de délégation en V1 » | **R** (+ **E** pour le calendrier) | S3 : question de périmètre. Lot L08 placé après les lots P0 et l'exclusion de l'administrateur technique. |
| CT-03 | Qualifications ↔ blocage | **R** + **T** | S3 distingue les deux situations. Mécanisme proposé en T-3. |
| CT-04 | Publication des listes de quarts/gardes (chef de liste ↔ COMAEQ) | **C** (C-1) | Vos règles ne couvrent que la feuille de service et les échanges. |
| CT-05 | Appareillage ↔ cadrages « ne pas développer » | **R** (règles) + **E** (calendrier) | S1, S2, S3. L'autorité qui définit obligatoire/critique reste ouverte : C-2. |
| CT-06 | « Mes tours de services » ↔ « de service » | **R** | S1 est la décision explicite la plus récente : libellé de S1 à appliquer au lot UX. |
| CT-07 | RETEX : code ↔ circuit | **R** | Écart code/décision, lot L11. |
| CT-08 | Épinglage du menu, recherche de personnes | **E** | Retenus par S1, calendrier en fin de plan (lot L24). |
| CT-09 | Cahier obsolète (génération automatique, Rondes) | **E** | Alignement de Notion par vos soins. |
| CT-10 | Passation | **R** | S1, S2 : pas de module autonome, préserver l'existant. |
| CT-11 | Visas par niveau ↔ droits par fonction | **R** | Écart code/décision, lots L06 et L09. |
| CT-12 | Durée automatique ↔ « ne pas sur-automatiser » | **R** | Option B tranchée ; garde-fous PT-DUR-06. |

## J.4 Les informations manquantes

| ID | Sujet | Classe | Traitement |
|---|---|---|---|
| IM-01 | Libellés et validité des brevets (BHT, C-CDM…) | **E** | Référentiel configurable, alimenté par le bord ; Notion 02 et 03 non lues (voir L). |
| IM-02 | Ordre des grades | **T** | Rang configurable sur le grade ; les valeurs sont saisies par le PO, jamais codées en dur (lot L16). |
| IM-03 | Autorité et délai de régularisation d'une mutation | **E** | Reporté avec la mutation (dépendance à l'architecture). |
| IM-04 | Anomalie à plusieurs interventions | **T** | À examiner dans le lot L22 ; aucun choix métier à faire. |
| IM-05 | Qui active une suppléance, durée maximale | **T** | Proposition : l'autorité hiérarchique directe du titulaire ou supérieure, durée obligatoire à la création, plafond configurable (valeur par défaut proposée : 30 jours). |
| IM-06 | Qui est le suppléant officiel du COMAEQ | **T** | Il l'est par une suppléance explicite activée par l'autorité compétente, pas par un statut permanent. |
| IM-07 | Réimpression d'une feuille affichée | **T** | Le BSC acquitte « imprimée et remplacée » ; trace. |
| IM-08 | Coordinateur d'une tâche à deux équipages | **T** | Les participants viennent du périmètre de la tâche ; aucune règle spéciale. |
| IM-09 | « Fin de journée » | **T** | Heure de fin de journée configurable par bâtiment, dans son fuseau. |
| IM-10 | Conservation des estimations et notifications | **T** | Estimations : conservées sans limite ; notifications lues : délai d'archivage configurable. |
| IM-11 | « Chef de service » ou « commandant adjoint » | **R** | S1 §11 et §8 disent « chef de service » : on suit S1. La COMA compétente n'intervient que si le circuit de fiche (N3) l'exige. |
| IM-12 | Sources non lues | Voir L | — |
| IM-13 | « Administrateur habilité » (application d'un transfert) | **T** | Administrateur d'unité du bâtiment concerné, sans droit de décision ; configurable. |
| IM-14 | Maintenance à calendrier fixe | **T** | Case « calendrier fixe » portée par la fiche, avec justification. |
| IM-15 | « Intervention » ↔ objets du code | **T** | À cartographier au lot L22. |

## J.5 Les questions F

| ID | Classe | Traitement |
|---|---|---|
| F-01 | **T** | Garde-fou A immédiat, puis droits par fonction. L'« exception du supérieur » (B2) n'est pas un mécanisme séparé : le supérieur **active une suppléance** (explicite, tracée, bornée). Cela évite un système parallèle. À confirmer en une ligne. |
| F-02 | **R** (échanges) + **C** (listes) | C-1 pour les listes. |
| F-03 | **T** + **E** | Proposition : secteur obligatoire, service dérivé (cohérent avec « le secteur est l'échelon responsable »). Reporté (P3). |
| F-04 | **T** + **E** | Statuts inconnus rejetés (lot L22). Sauts de statut et contrôle croisé reportés. |
| F-05 | **T** + **E** | Suppression d'un compte sans aucun historique permise à un administrateur d'unité, tracée. Mutation : reportée. |
| F-06 | **R** (qualifications) + **T** | Qualifications résolues par S3. Activation, durée, retour anticipé : propositions IM-05, IM-06. |
| F-07 | **C** (C-2) | Autorité qui définit « obligatoire » ou « critique ». |
| F-08 | **E** | « Critique » (cahier §19) par défaut, lot UX. |
| F-09 | **R** | Voir CT-06. |
| F-10 | **T** + **E** | Marin transversal : secteur entier explicite (T1) ; fonction « gestion de la structure » attribuée comme les autres fonctions ; écran de structure plus tard. |
| F-11 | **E** (externe) | Experts SIC. La limitation des connexions peut être codée sans attendre (lot L21). |
| F-12 | **T** | Message corrigé tout de suite ; alerte au chef de secteur (cohérent avec DEC-ANO-04). |
| F-13 | **E** | GO du PO requis ; hors plan actif. |
| F-14 | **E** | Gouvernance documentaire et CI, fin de plan. |

## J.6 Les contradictions réellement restantes

### C-1 — Qui publie les listes de quarts et de gardes ?

**Constat.** Vous avez tranché la feuille de service (BSC prépare, COMAEQ approuve) et les échanges (COMAEQ décide, BSC ou chef de liste instruit). Pour les **listes de quarts et de gardes** elles-mêmes, la note N3 donne la création/publication au chef de liste ; le code laisse aussi modifier une liste publiée au commandant et aux administrateurs (AUD-015). Aucune décision récente ne dit qui publie.

**Recommandation.** Chef de liste prépare et propose ; **COMAEQ ou son suppléant habilité approuve et publie** ; modification après publication = nouvelle version (proposer → valider → publier, CLAUDE.md principe 7). C'est la même logique que la feuille et les échanges, sans nouveau mécanisme.

**Conséquence si vous refusez.** Si le chef de liste publie seul, il faut au moins interdire les voies directes du commandant et des administrateurs (AUD-015). Aucun lot P0 n'en dépend ; seul le lot L09 attend.

### C-2 — Qui définit qu'un contrôle d'appareillage est « obligatoire » ou « critique » ?

**Ce que j'ai trouvé, sans rien en déduire :**

- La note Notion « Veille d'appareillage » (PO, 20/10) dit que **les chefs de secteur habilités** créent et modifient les modèles de checklists dans Matrix, sans modifier le code ; que les modèles sont versionnés ; que la validation des modèles et les responsabilités « seront définies plus tard avec le PO ».
- S1 §8 dit que les modifications des références suivent « leur propre circuit d'approbation » (non décrit).
- Pour les fiches d'installation, un circuit existe : section ou secteur → chef de service → commandant adjoint compétent (N3).
- La note « Prêt à appareiller » (06/10) donne la saisie aux équipiers et chefs de section, la modification aux chefs de secteur et de service.

**Ce qui n'est donc pas défini** : l'autorité qui qualifie un contrôle de « obligatoire » et celle qui le qualifie de « critique non dérogeable ». Je ne la choisis pas.

**Question au PO.** Parmi les fonctions existantes, laquelle valide cette qualification pour votre bâtiment : le circuit déjà prévu pour les fiches d'installation, le COMANAV, ou une autre fonction ? Une réponse en une ligne suffit.

**Position par défaut (technique, sans règle métier).** Tant que rien n'est défini, **aucun contrôle n'est « obligatoire » ni « critique »** : les deux caractéristiques sont des attributs de la fiche de référence, vides par défaut, modifiables seulement par le circuit d'approbation de cette fiche. Le lot d'appareillage (L23) attend cette réponse ; aucun autre lot n'en dépend.

### Dépendance externe — architecture bord–terre (mutation)

La note du 02/10 indique que la mutation **dépend de la décision d'architecture** (une base partagée ou un serveur par bâtiment). Ce n'est pas une contradiction mais une dépendance : le lot de mutation (L25) est reporté tant que ce choix, réservé aux experts SIC (S1 §13), n'est pas fait. Les lots qui préparent la mutation (désactivation, rattachement obligatoire) n'en dépendent pas.

## J.7 Propositions techniques liées

### T-3 — Contrôle des exigences réglementaires (qualifications)

- Les tâches ordinaires ne consultent jamais les qualifications.
- Un **visa technique, une fonction de service ou une signature officielle** peut porter une « exigence » (qualification requise), **vide par défaut**, renseignée seulement par le circuit d'approbation correspondant, à partir des textes du bord.
- Si une exigence est renseignée et non satisfaite : refus explicite avec le motif. Sinon : aucun contrôle.
- Une donnée périmée dans Matrix ne bloque donc que ce que le bord a explicitement déclaré réglementaire. Test : T-QUA-01.

### T-1 et T-2 (reprises)

- T-1 : B2 absorbée par la suppléance (voir F-01).
- T-2 : pas de nouveau système d'accès « pour l'exception du supérieur » (évite l'usine à gaz).
