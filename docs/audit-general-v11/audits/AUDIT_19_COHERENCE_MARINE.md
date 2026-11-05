# Audit 19 — Cohérence métier Marine nationale

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Commit audité `1c37f22`, comparaison avec `main` dans `../10_COMPARAISON_MAIN_V11.md`.

Cet audit confronte le code et le comportement observé aux **règles écrites dans Notion** (hub « Organigramme et rôles » et ses 13 sous-pages, Cahier des charges, décisions du PO). **Aucune doctrine n'est affirmée** : les sources publiques n'ont pas été consultées, les usages propres à une unité sont signalés comme variables.

## 1. Questions auxquelles l'audit répond

1. L'organisation hiérarchique et fonctionnelle du code correspond-elle aux règles documentées ? (A)
2. Les structures sont-elles assez souples pour plusieurs bâtiments réels ? (B)
3. Les rôles, fonctions, responsabilités et permissions suivent-ils les responsabilités métier ? (C)
4. Les processus quotidiens, la maintenance et la répartition des installations, les quarts et services MER/QUAI, les circuits de validation et la terminologie sont-ils cohérents avec la source ? (D à H)

**Nature des constats** (colonne 4 de la matrice) : *Documentée* (règle écrite, source citée) ; *Usage variable* (pratique propre à une unité, à ne pas figer) ; *Hypothèse* (source = brief du PO ou lecture de l'audit) ; *Incohérence* (code et source divergent) ; *Décision PO* (arbitrage nécessaire, colonne 8). **Conformité** : V-C vérifié conforme ; V-NC vérifié non conforme ; PC partiellement conforme ; NV non vérifié ; DIFF différé volontairement.

## 2. Matrice règle métier / source / implémentation / conformité / preuve / décision nécessaire

| N° | Règle métier | Source | Nature | Implémentation | Conformité | Preuve | Décision PO nécessaire |
|---|---|---|---|---|---|---|---|
| **A. Organisation hiérarchique et fonctionnelle** | | | | | | | |
| RM-01 | Chaîne embarquée : commandant → second → commandants adjoints → services → secteurs → sections → équipiers, configurable par bâtiment | Notion p.01, p.13 ; Cahier §4 | Documentée | `Roles`, modèles `org` (Ship, Service, Sector, Section) ; 5 organisations de démonstration | PC | `sondes/organisations_reelles.py` ; AUDIT_02 : hiérarchie présente, mais modifiable seulement par le compte de flotte (écran) ou l'API | A2 (fonction « gestion de la structure ») |
| RM-02 | Quatre commandants adjoints (COMAEQ, COMOPS, COMANAV, COMAVIA) ; COMAVIA seulement si l'organisation du bâtiment le prévoit | p.01, p.13 | Documentée | `UserProfile.fonction_coma` (4 valeurs) ; titulaire par bâtiment et équipage | V-C | Bâtiments sans aucun COMA (BordOps I), avec 1 à 3 COMA (Normandie, Jacques Chevallier, Bretagne) ; variante exécutée : COMAVIA désigné sur Bretagne, titulaire reconnu | — |
| RM-03 | Chaque service est rattaché explicitement à son commandant adjoint ; les visas résolvent service → COMA → titulaire (jamais un niveau « état-major ») | p.01, p.13 | Documentée | `Service.commandant_adjoint` + `titulaires_commandant_adjoint` ; mais `assets/fiche_validation.py:97` et `proposition_article.py:186` traitent le niveau état-major comme commandant adjoint | PC | Rattachements observés : Bretagne COMANAV 2, COMAEQ 1, COMOPS 1 ; un service sans rattachement (BordOps I) ; P05 (2 sites par niveau) | B (DP-09) |
| RM-04 | Commandant en second : remplaçant désigné, vision globale, écritures limitées aux responsabilités attribuées | p.13 (octobre) | Documentée | vision commandement en lecture ; exclu de la publication des listes ; peut désigner des chefs de liste et configurer les rubriques | PC | AUDIT_06 §1 (ne publie pas, ne déclare pas de mouvement) ; tâche Notion « Commandant en second : actions d'écriture » à faire plus tard | Oui (tâche ouverte) |
| RM-05 | Double équipage A/B : deux équipages sur un même bâtiment, chacun sa chaîne ; équipage à terre en lecture adaptée | p.13 (rectifications du 18 et du 19/10) | Documentée | champs `equipage`, relèves, `EquipageATerreMiddleware` | V-C (séparation) ; NV (relève, passation) | création de feuille, désignation de rédacteurs et lecture sans fuite entre A et B ; relève non rejouée | DP-02 (passation) |
| RM-06 | Soutien à terre : « responsable de classe » = IRB (SSF), « responsable de spécialité » = ALFAN Exploitation ; lecture et commentaire, pas d'écriture sur le bord | p.12, p.13 (21/10) | Documentée | `ResponsableClasseNavire`, `ResponsableSpecialite` ; l'interface dit « Responsable de classe de navire » et « Responsables de spécialité » ; IRB n'apparaît que dans le routage RETEX (`retex/services.py:28`) | V-C | `terre_classe` : 403 sur toutes les écritures sondées ; libellés relevés dans le code | — |
| RM-07 | Fonctions « adjudant de compagnie » et « OSS » reconnues, sans GO d'implémentation | p.ORG (31/10) | Documentée | absentes | Conforme à l'absence (DIFF) | recherche textuelle sans résultat | aucune avant GO |
| RM-08 | Grade, fonction exercée, périmètre, habilitation et autorité de visa sont des dimensions distinctes ; les droits ne se déduisent pas du grade | p.01 (principe central), directive du 31/10 | Documentée | droits par niveau de rôle ; fonctions COMA, rédacteur, référent, chef de liste existent mais coexistent avec des seuils de niveau | V-NC partiel | AUD-014, AUD-015, AUD-022 ; mutations de tests (AUDIT_16) | B (DP-09) |
| **B. Souplesse selon les bâtiments et adaptabilité à plusieurs organisations réelles** | | | | | | | |
| RM-09 | Chaque bâtiment est unique, y compris au sein d'une classe ; l'organisation se configure sans développeur pour les opérations courantes | Cahier §4 ; p.13 (« FREMM, FDA, FLF, BRF… peuvent différer ») ; brief du PO | Documentée | 5 organisations de démonstration de formes différentes (voir §3) ; configuration par l'API (administrateur d'unité) ou le compte de flotte | PC | `organisations_reelles.py` : type, classe, double équipage, mode, nombre de services, secteurs, sections, COMA présents, rattachements, effectif, listes ; AUD-019 | A2, A3 |
| RM-10 | Sections facultatives selon le bâtiment | Brief du PO (aucune source écrite antérieure) | Hypothèse → orientation décidée (option B + D) | `Section` optionnelle sur le profil ; secteur sans section accepté ; non exercé par la démonstration | PC | `AUDIT_DP03_SECTIONS.md`, `propositions/P01` ; nouveau bâtiment simulé avec secteurs sans section : tous les écrans s'ouvrent | A1 (marin transversal) |
| RM-11 | Les regroupements d'installations ne sont pas imposés par des catégories techniques prédéfinies | Brief du PO | Hypothèse (brief) | regroupement « bigramme » = table configurable (`name`, `active`, 2 lignes) ; installation rattachée à un service **et** un secteur obligatoires, section facultative | V-C (catégories) ; limite (secteur obligatoire) | `organisations_reelles.py` (champs des modèles) ; AUD-037 | Confirmer si le secteur doit rester obligatoire pour une installation |
| RM-12 | Les rattachements d'installations aux services, secteurs, sections sont adaptables | Brief du PO | Hypothèse (brief) | clés étrangères protégées ; réaffectation par édition de la fiche ; non rejouée | NV | — | — |
| RM-13 | Poste de COMAEQ vacant : le commandant de l'équipage peut viser la feuille, de façon identifiable ; ni le second, ni l'administrateur, ni un autre COMA | p.13 (18 et 19/10) | Documentée | `peut_viser_comaeq` + `commandant_habilite_si_comaeq_vacant` | V-C | variante exécutée : poste vacant → seul `cdt_a` peut viser ; `second_a`, `admin_navire`, `coma_comanav` refusés | — |
| **C. Rôles, fonctions, responsabilités, permissions** | | | | | | | |
| RM-14 | Rédaction de la feuille réservée à une fonction BSC ou délégation habilitée | p.06 (point de sécurité) | Documentée | `peut_rediger_feuille_service` + `RedacteurFeuilleService` | V-C | AUDIT_06 ; comparaison avec `main` (corrigé) | — |
| RM-15 | Chaque équipage a sa feuille ; validation par le COMAEQ compétent de l'équipage | p.13 (19/10) | Documentée | `equipage_de_feuille_pour`, visa COMAEQ strict | V-C | AUDIT_06 §2 | — |
| RM-16 | Chef de liste : création et publication des listes de service ; le COMAEQ porte le service courant | p.13 ; p.01 ; p.06 | Documentée | publication par niveau (seuil CHEF_SERVICE) : COMANAV et COMOPS publient aussi | Incohérence | AUDIT_06 §1 ; `docs/propositions/droits_comaeq.md` | B3 |
| RM-17 | Un administrateur technique gère la plateforme, pas le fonctionnement métier | Cahier §5 | Documentée | l'administrateur d'unité (niveau 8) franchit les seuils métier | V-NC | AUD-014, 015 ; AUDIT_06 | B1 |
| **D. Processus de travail quotidiens** | | | | | | | |
| RM-18 | Le marin voit sa journée : où être, quoi faire, quoi savoir, avec qui, quoi signaler | Cahier §2, §6, §40 | Documentée | accueil « Aujourd'hui », calendrier, tâches, annonces, discussion, signalement | V-C (parcours rejoués) | AUDIT_04 : 11 parcours en navigateur sans erreur | — |
| RM-19 | Service courant : le BSC orchestre ; la feuille de service est le point de convergence du jour J | p.06 | Documentée | module feuille de service, circuit de visas | V-C | circuit complet rejoué en navigateur | — |
| RM-20 | Un chef attribue une tâche à un marin de son périmètre ; le marin la suit, la bloque avec motif ; le chef voit le blocage | CDC bandeau 09/10 ; p.13 | Documentée | `taches` | V-C | attribution, démarrage, blocage, carte « Blocage à lever » chez le chef | — |
| **E. Maintenance et répartition des installations** | | | | | | | |
| RM-21 | Le bord est le premier niveau de maintenance autorisée : exploitation, contrôle, diagnostic, entretien, compte rendu, essais | p.04 | Documentée | exécution de maintenance par les marins (seuil équipier), compte rendu, confirmation sur critique | V-C | exécution web et API rejouées ; confirmation critique | — |
| RM-22 | Arborescence bâtiment → domaine → installation → équipement → sous-équipement → composant | p.04 | Documentée | `Installation.parent` / `sous_ensemble` ; domaine = service/secteur | PC | structure lue ; non rejouée en navigateur | — |
| RM-23 | Correctif : signalement → diagnostic → criticité → impact → réparation → essais → retour en service | p.04 | Documentée | `CorrectiveTicket` (REPORTED…TESTING, RETURNED_TO_SERVICE, CLOSED) avec confirmation à la remise en service | PC | états observés en démonstration, sauf RETURNED_TO_SERVICE absent (AUDIT_20) | — |
| RM-24 | Compte rendu d'intervention notifié au chef de secteur, sans visa, modifications tracées | p.13 | Documentée | notification « Compte rendu saisi » ; correction motivée (`ModificationCompteRendu`) ; message de ticket faux pour une installation | V-NC partiel | AUD-023 ; notification vérifiée (chefs A et B) | Message : correction immédiate ; comportement voulu pour les installations |
| RM-25 | Fiche matériel flotte : un bord ne la publie pas seul (circuit en 7 étapes) ; fiche d'installation adaptable au bord | p.04, p.13 | Documentée | `assets/fiche_validation.py`, `fiche_flotte.py`, `fiche_adaptation.py` | NV | couvert par la suite de tests, non rejoué | — |
| RM-26 | Travail terminé ≠ matériel disponible : contrôle, essais, retour en service | p.04 | Documentée | étape TESTING du ticket ; pas de modèle d'essais statique/fonctionnel/système | NV | — | Besoin à confirmer |
| **F. Quarts et services MER/QUAI** | | | | | | | |
| RM-27 | Quart à la mer, service à quai et garde sont des notions distinctes ; le mode MER/QUAI du bâtiment se déduit des mouvements, jamais d'un champ libre | p.06 ; recette V1 | Documentée | `Quart`, `ServiceGarde`, `mode_du_batiment` (None si jamais renseigné) | V-C | démonstration : Bretagne QUAI, Auguste Bénébig QUAI, Jacques Chevallier MER, BordOps I et Normandie sans mode | — |
| RM-28 | Aucun rythme, horaire ou durée de quart n'est codé en dur ; les horaires sont des attributs de chaque poste | p.06 ; Cahier §8, §33 | Documentée | créneau libre (poste, début, fin) ; durée par défaut portée par la liste (`duree_creneau_heures`) | V-C | recherche textuelle : aucune durée en dur hors affichage | — |
| RM-29 | Régimes (bordées, tiers, quart, cinquième, sixième), « hommes morts », « de musique » | p.06 (rectification 31/10) | Documentée (cadrage sans GO) | absents | Conforme à l'absence (DIFF) | recherche textuelle sans résultat | GO du PO |
| RM-30 | Fraction de service à quai : postes requis tous pourvus ; composition-type paramétrable ; contrôle des qualifications seulement plus tard | p.06 | Documentée (cadrage) | module Postes (effectif requis, titulaires) ; composition-type de fraction non retrouvée | NV | 5 postes et 9 affectations en démonstration | Oui (GO) |
| RM-31 | La feuille de service et le tableau de quart sont deux supports distincts | p.06 | Documentée | la feuille n'agrège pas les quarts | V-C | structure lue ; maquettes | — |
| RM-32 | Échange de service : A → B → chef de liste ; l'historique conserve l'échange ; l'impossibilité est expliquée | Cahier §12 à §14 | Documentée | `EchangeService` (7 états) | PC | demande, acceptation, validation rejouées ; explication d'impossibilité non rejouée | — |
| RM-33 | Génération automatique des tours abandonnée ; planification manuelle avec contrôle | CDC bandeau 09/10 | Documentée | aucun générateur | V-C | AUDIT_09 | — |
| **G. Circuits de validation** | | | | | | | |
| RM-34 | Feuille de service : chef de secteur → chef de service → COMAEQ | p.13 | Documentée | 3 paliers ; visas intermédiaires ouverts à d'autres niveaux | PC | AUD-014 | B1 |
| RM-35 | Listes : brouillon → proposition → validation → publication ; version publiée active jusqu'à validation | Cahier §34 ; p.13 | Documentée | versionnage ; voies directes sur listes publiées | PC | AUD-015 ; D-05 au backlog | B |
| RM-36 | Document : rédaction → validation par une autre personne → publication, versions conservées | Cahier §34 ; p.13 | Documentée | `documentation` (circuit) | V-C | circuit rejoué : l'auteur ne valide pas, le COMA valide, version applicable | — |
| RM-37 | Formation : candidature → hiérarchie → BRH → organisme ; validation par un référent de la formation | p.03 | Documentée | `CandidatureFormation` (6 états) ; `ReferentFormation` | PC | candidature créée (en attente d'approbation) ; validation par référent vérifiée ; suite du circuit NV | — |
| RM-38 | Fiche d'installation : section/secteur → service → COMA ; fiche flotte : 7 étapes jusqu'à la publication au catalogue | p.13 | Documentée | `fiche_validation.py` | NV | tests | — |
| RM-39 | RETEX : proposé, validé par les habilités (COMA référent d'abord), publié comme document | p.13 ; Notion RETEX | Documentée | `retex` (états PROPOSE, VALIDE…) | NV | états présents en démonstration, circuit non rejoué | — |
| RM-40 | Relève de double équipage validée par les autorités des deux équipages ; date d'effet ; fuseau du bâtiment | p.13 | Documentée | `ReleveEquipage`, application planifiée | NV | un seul état présent en démonstration (en attente) | DP-02 (passation) |
| RM-41 | Prêt à appareiller : validation avec confirmation explicite tracée | p.13 ; Notion | Documentée | `pret_appareillage` (texte versionné) | NV | couvert par les tests, non rejoué | Droits de saisie à décider (tâche ouverte) |
| **H. Terminologie métier** | | | | | | | |
| RM-42 | Ne pas afficher « chef de groupement » ni « CAN » ; utiliser les sigles et fonctions réels | p.01, p.13 | Documentée | aucune occurrence dans gabarits et vues | V-C | recherche textuelle | — |
| RM-43 | « Responsable de classe » = IRB ; « responsable de spécialité » = ALFAN Exploitation | p.12 | Documentée | libellés de l'interface conformes | V-C | recherche dans les gabarits et le code | — |
| RM-44 | Annonces : Information / Important / **Critique** | Cahier §19 | Documentée | l'interface propose « Urgent » | Incohérence mineure | niveaux relevés en navigateur | Choisir le terme |
| RM-45 | Vocabulaire du quart : musique, homme mort, bordée, tiers… | p.06 | Documentée (cadrage) | absent de l'interface | NV (non demandé en développement) | — | GO du PO |
| RM-46 | Messages PÉPIN, CRAT, RAV/c : circuits non validés, pas d'implémentation officielle | p.12, p.13 | Documentée (différé) | absents | Conforme à l'absence (DIFF) | recherche textuelle | Cartographie métier avant tout développement |

**Bilan** (46 règles) : V-C 18, PC 11, NV 9, Conforme 3, V-NC 3, Incohérence 2.

## 3. Adaptabilité à plusieurs organisations réelles : ce que montrent les cinq bâtiments de démonstration

Mesure `sondes/organisations_reelles.py` (pipeline complet) :

| Bâtiment | Type, classe | Équipages | Mode | Services / secteurs / sections | COMA titulaires | Rattachement des services | Effectif |
|---|---|---|---|---|---|---|---|
| BordOps I | navire, — | 1 | non renseigné | 1 / 2 / 2 | aucun | aucun COMA | 1 |
| Bretagne | navire, FREMM | **2 (A et B)** | QUAI | 4 / 5 / 5 | COMAEQ, COMOPS, COMANAV (pas COMAVIA) | COMANAV 2, COMAEQ 1, COMOPS 1 | 36 |
| Normandie | navire, FREMM | 1 | non renseigné | 1 / 1 / 1 | aucun | COMANAV | 3 |
| Jacques Chevallier | navire, — | 1 | MER | 1 / 1 / 1 | COMAEQ seul | COMANAV | 6 |
| Auguste Bénébig | navire, — | 1 | QUAI | 1 / 1 / 1 | COMAEQ seul | COMANAV | 7 |

**Lecture** : le modèle accepte des organisations très différentes (un à quatre services, un ou deux équipages, zéro à trois commandants adjoints, mode MER, QUAI ou non renseigné). **Limites constatées** : (1) l'organisation n'est modifiable que par le compte de flotte ou l'API (AUD-019) ; (2) une installation exige un service **et** un secteur (AUD-037) : un bâtiment qui n'aurait que des services ne pourrait pas déclarer d'installations ; (3) aucun bâtiment de démonstration n'a de COMAVIA, de secteur sans section ni de marin transversal : ces cas ne sont exercés que par les variantes de l'audit ; (4) les rôles à terre et les organismes (division, bureau) ne sont pas modélisés comme unités (différé par décision).

**Variantes exécutées (transactions annulées)** : COMAEQ vacant (la feuille ne peut être visée que par le commandant de l'équipage) ; COMAVIA désigné avec un service rattaché (titulaire reconnu) ; installation sans secteur (impossible : champ obligatoire).

## 4. Incohérences et décisions PO nécessaires (synthèse)

| Sujet | Nature | Règles | Anomalie | Décision |
|---|---|---|---|---|
| Droits par niveau au lieu de fonction | Incohérence | RM-08, 16, 17, 34 | AUD-014, 015, 022 | Bloc B |
| COMA résolu par niveau dans deux circuits | Incohérence | RM-03 | P05 | Bloc B |
| Structure non autonome | Incohérence avec le brief | RM-01, 09 | AUD-019 | Bloc A |
| Message de ticket faux pour une installation | Incohérence | RM-24 | AUD-023 | Bloc D |
| « Urgent » au lieu de « Critique » | Incohérence mineure | RM-44 | — | à choisir |
| Secteur obligatoire pour une installation | Hypothèse | RM-11 | AUD-037 | à confirmer |
| Régimes de quart, fraction de service, adjudant de compagnie, OSS, PÉPIN/CRAT | Documentée sans GO | RM-07, 29, 30, 45, 46 | — | GO du PO |

## 5. Terminologie : points relevés

« responsable de classe de navire » et « responsable de spécialité » sont les libellés de l'interface (équivalents IRB et ALFAN Exploitation selon la source) ; IRB et ERO n'apparaissent que dans le routage RETEX ; « mode du bâtiment : QUAI/MER » et « Difficultés signalées » sont cohérents avec les décisions ; aucun terme proscrit n'est affiché.

## Clôture (4ᵉ passe et addendum)

**Statut : Clôturé avec réserves.** L'analyse technique est achevée : 46 règles, 5 organisations, 3 variantes exécutées. Les réserves ne sont pas des conformités.

### Non vérifié ou dépendant d'une validation externe

Règles marquées NV dans la matrice (fiches, RETEX, relève, prêt à appareiller, fraction de service) ; vérification indépendante par des sources publiques ; validation par un expert du bord de ce qui relève d'un usage variable ; libellés complets de l'interface un à un (échantillon de menus et d'écrans seulement).
