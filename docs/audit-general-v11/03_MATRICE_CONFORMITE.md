# Matrice unique de conformité (exigences, règles métier Marine, couverture)

**Matrice unique** : partie A (48 exigences du référentiel), partie B (46 règles métier de l'audit 19), partie C (couverture de l'audit 20). Commit audité `1c37f22`, 2026-11-05. États : **V-C** vérifié conforme ; **V-NC** vérifié non conforme ; **PC** partiellement conforme ; **NV** non vérifié ; **DIFF** volontairement différé ; **ABS** absent, sans exigence de développement ; **ARB** à arbitrer. Un état « V-C » est limité au périmètre écrit dans la colonne Preuve.

## A. Exigences du référentiel

| Exigence | Intitulé | État | Preuve | Audit |
|---|---|---|---|---|
| EX-001 | Matrix = plateforme quotidienne, GMAO = un module | PC | 22 applications dont la GMAO en un module ; accueil rejoué (7 profils) ; la valeur quotidienne n'est pas mesurable sans usage réel | 04, 05 |
| EX-002 | Aucune règle susceptible d'évoluer en dur | V-NC partiel | 35 actions réglables par bâtiment, mais 55 comparaisons en dur (AUD-022) et structure non autonome (AUD-019) | 02 |
| EX-003 | Internet n'existe pas | V-C (code statique) | aucune ressource externe (gabarits, styles, scripts ; 7 profils en navigateur) ; réseau réel non testé | 15 |
| EX-004 | Tout est traçable, jamais d'écrasement silencieux | PC | AuditLog sur visas, stock, maintenance critique, désignations ; mais suppression d'unités sans trace par personne touchée (AUD-020) | 14, 15 |
| EX-005 | Proposer → valider → publier | PC | circuits de la feuille et du document rejoués ; voies directes sur listes publiées (AUD-015) | 09, 12 |
| EX-006 | Administration distribuée | PC | seuils et modules réglables par bâtiment (effet immédiat, limité au bâtiment) ; structure non autonome par l'écran (AUD-019) | 02 |
| EX-007 | Droits non déduits du seul grade ; vérification côté serveur | PC | contrôles serveur confirmés (1 407 + 196 essais) ; plusieurs droits par niveau (AUD-014) | 06 |
| EX-008 | Non-surcharge | NV | 6 à 13 cartes d'accueil, 23 à 29 liens de menu : densité non comparée aux maquettes | 05 |
| EX-009 | Tolérance aux coupures bord–terre | DIFF | Phase 7 volontairement différée | 13 |
| EX-010 | Le marin voit sa journée à l'ouverture | PC | accueil rejoué (7 profils, 61 comptes) ; tâche, échange, annonce, brouillon visibles ; liens refusés (AUD-016) ; justesse du contenu non évaluée par des marins | 04 |
| EX-011 | Calendrier unique | V-C | 7 sources, 3 vues (jour, semaine, mois) et panneau de détail rejoués en navigateur ; événement personnel conservé | 07 |
| EX-012 | Calendrier, colonne vertébrale du pilotage | NV | vues collectives et pilotage non rejoués | 07 |
| EX-013 | Recherche universelle | V-C (échantillon) | 12 recherches : résultats par périmètre, aucune donnée d'un autre bâtiment ; recherche rapide en 200 | 05 |
| EX-014 | Notifications explicites | PC | notifications nominatives (« Compte rendu saisi : <objet> », « Anomalie signalée : <titre> », « Blocage : … ») ; échéance non systématique ; archivage absent (ANO-012) | 11 |
| EX-020 | Chef de liste | PC | désignation et droits de gestion rejoués ; modification d'une liste publiée par proposition absente (D-05 A) | 09 |
| EX-021 | Génération automatique abandonnée | V-C | aucun générateur dans quarts/ | 09, 19 |
| EX-022 | Aucun rythme de quart en dur ; régimes | PC | aucune durée en dur hors affichage ; régimes nommés non implémentés (cadrage sans GO) | 09, 19 |
| EX-023 | « Hommes morts » et « de musique » | ABS (cadrage) | aucune occurrence dans le code ; développement non autorisé | 19 |
| EX-024 | Fraction de service : postes requis pourvus | NV | module postes présent ; composition-type de fraction non vérifiée | 12 |
| EX-025 | Feuille de service ≠ tableau de quart | V-C (structure) | la feuille n'agrège pas les quarts | 09 |
| EX-026 | Rédaction de la feuille réservée aux rédacteurs désignés | V-C sur 1c37f22 ; V-NC sur main | création (11 profils), écritures (16 profils), lectures (13 × 3 états), circuit en navigateur ; deux jeux de données | 06, 09 |
| EX-027 | Feuille par équipage, validation COMAEQ | V-C avec réserve | COMAEQ strict, rédacteurs par équipage, pas d'échappement inter-équipage ; visas intermédiaires élargis (AUD-014) | 06 |
| EX-028 | Échange de service | PC | demande, acceptation par B, validation par le chef rejouées (états `VALIDE`, `ACCEPTE`) ; explication d'impossibilité non rejouée | 09 |
| EX-029 | Service à quai, garde, quart distincts | PC | modèles distincts (Quart, ServiceGarde) ; non rejoué | 09 |
| EX-030 | Hiérarchie configurable par navire | PC | hiérarchie présente ; modification non autonome (AUD-019) ; sections facultatives non exercées (DP-03) | 02 |
| EX-031 | Service rattaché à son COMA, visa résolu par service | PC | `Service.commandant_adjoint` ; résolution par niveau dans deux circuits (P05) | 19 |
| EX-032 | Visa COMA : attente sans titulaire | PC | feuille rejouée ; autres circuits non rejoués | 19 |
| EX-033 | Double équipage A/B, relève, lecture seule à terre | PC | séparation des équipages vérifiée (création, désignation, lecture) ; relève et passation non rejouées ; passation à arbitrer (DP-02) | 06 |
| EX-034 | Commandement à terre sans écriture métier | PC | refus 403 du suivi de classe dans toutes les écritures sondées | 06 |
| EX-035 | Second : vision globale, écritures limitées | PC | ne publie pas, ne déclare pas de mouvement ; désigne des chefs de liste (décision ouverte) | 06 |
| EX-036 | Adjudant de compagnie, OSS | DIFF | aucune implémentation, conforme à l'absence de GO | 19 |
| EX-037 | Pas de « chef de groupement » / « CAN » | V-C | aucune occurrence | 19 |
| EX-038 | Organismes à terre comme unités | DIFF | consolidation V1 en cours | 19 |
| EX-040 | Fiche flotte : circuit en 7 étapes | NV | non rejoué | 08 |
| EX-041 | Fiche d'installation adaptable | NV | non rejoué | 08 |
| EX-042 | Compte rendu notifié au chef de secteur, sans visa | V-NC partiel | par l'API : ni ticket ni notification pour une installation non conforme (AUD-023) ; chemin web non rejoué | 08 |
| EX-043 | Complémentarité SSF, identifiants stables | PC | UUID sur tickets et installations ; pas d'interface SSF | 13 |
| EX-044 | Discussions contextuelles via threads | V-C (tâche) ; NV (autres objets) | discussion d'une tâche rejouée : message, réponse, notification, étanchéité entre bâtiments | 11 |
| EX-045 | Annonces par niveau et périmètre | PC | ciblage bâtiment conforme (404 hors cible) ; niveau « Urgent » au lieu de « Critique » | 11 |
| EX-046 | Logistique : stocks, prêts, retours, inventaires | PC | stock et mouvements conformes ; prêts/retours/inventaires de matériel différés | 10 |
| EX-047 | Documentation, formations, RETEX | PC | formation (candidature en attente d'approbation, validation par référent), documentation (circuit complet), RETEX et absences (formulaires) ; faible couverture de tests (AUD-030) | 12 |
| EX-048 | QR codes hors V1 | V-NC | route /scan/<uuid>/ fonctionnelle (DP-06) | 08, 19 |
| EX-049 | PÉPIN / CRAT / RAV/c | DIFF | absents, conforme | 19 |
| EX-050 | PC fixe 1366×768 ; mobile dégradé proprement | PC | 1366×768 et 375×667 sans débordement, menu mobile, mode sombre, impression ; tablette tactile non testée | 05 |
| EX-051 | Interface sobre, aide contextuelle | NV | maquettes non comparées | 05 |
| EX-052 | Tout en français | PC | gabarits et messages observés en français ; page technique en anglais seulement avec DEBUG ; code non relu | 05 |
| EX-053 | SQLite (dev) et PostgreSQL (prod) | V-C | suite complète verte sur SQLite et PostgreSQL ; migration d'une base peuplée de `main` vers la V1.1 sans perte sur les deux moteurs | 14, 17 |
| EX-054 | Rondes retirées | V-C | routes absentes ; résidu de modèles (AUD-007) | 12, 19 |

## B. Règles métier Marine nationale (audit 19)

Source, implémentation et preuve détaillées dans `audits/AUDIT_19_COHERENCE_MARINE.md` §2 ; nature du constat : documentée, usage variable, hypothèse, incohérence.

| N° | Règle métier | Nature | Conformité | Décision PO nécessaire | Audit |
|---|---|---|---|---|---|
| **A. Organisation hiérarchique et fonctionnelle** | | | | | |
| RM-01 | Chaîne embarquée : commandant → second → commandants adjoints → services → secteurs → sections → équipiers, configurable par bâtiment | Documentée | PC | A2 (fonction « gestion de la structure ») | 19 |
| RM-02 | Quatre commandants adjoints (COMAEQ, COMOPS, COMANAV, COMAVIA) ; COMAVIA seulement si l'organisation du bâtiment le prévoit | Documentée | V-C | — | 19 |
| RM-03 | Chaque service est rattaché explicitement à son commandant adjoint ; les visas résolvent service → COMA → titulaire (jamais un niveau « état-major ») | Documentée | PC | B (DP-09) | 19 |
| RM-04 | Commandant en second : remplaçant désigné, vision globale, écritures limitées aux responsabilités attribuées | Documentée | PC | Oui (tâche ouverte) | 19 |
| RM-05 | Double équipage A/B : deux équipages sur un même bâtiment, chacun sa chaîne ; équipage à terre en lecture adaptée | Documentée | V-C (séparation) ; NV (relève, passation) | DP-02 (passation) | 19 |
| RM-06 | Soutien à terre : « responsable de classe » = IRB (SSF), « responsable de spécialité » = ALFAN Exploitation ; lecture et commentaire, pas d'écriture sur le bord | Documentée | V-C | — | 19 |
| RM-07 | Fonctions « adjudant de compagnie » et « OSS » reconnues, sans GO d'implémentation | Documentée | Conforme à l'absence (DIFF) | aucune avant GO | 19 |
| RM-08 | Grade, fonction exercée, périmètre, habilitation et autorité de visa sont des dimensions distinctes ; les droits ne se déduisent pas du grade | Documentée | V-NC partiel | B (DP-09) | 19 |
| **B. Souplesse selon les bâtiments et adaptabilité à plusieurs organisations réelles** | | | | | |
| RM-09 | Chaque bâtiment est unique, y compris au sein d'une classe ; l'organisation se configure sans développeur pour les opérations courantes | Documentée | PC | A2, A3 | 19 |
| RM-10 | Sections facultatives selon le bâtiment | Hypothèse → orientation décidée (option B + D) | PC | A1 (marin transversal) | 19 |
| RM-11 | Les regroupements d'installations ne sont pas imposés par des catégories techniques prédéfinies | Hypothèse (brief) | V-C (catégories) ; limite (secteur obligatoire) | Confirmer si le secteur doit rester obligatoire pour une installation | 19 |
| RM-12 | Les rattachements d'installations aux services, secteurs, sections sont adaptables | Hypothèse (brief) | NV | — | 19 |
| RM-13 | Poste de COMAEQ vacant : le commandant de l'équipage peut viser la feuille, de façon identifiable ; ni le second, ni l'administrateur, ni un autre COMA | Documentée | V-C | — | 19 |
| **C. Rôles, fonctions, responsabilités, permissions** | | | | | |
| RM-14 | Rédaction de la feuille réservée à une fonction BSC ou délégation habilitée | Documentée | V-C | — | 19 |
| RM-15 | Chaque équipage a sa feuille ; validation par le COMAEQ compétent de l'équipage | Documentée | V-C | — | 19 |
| RM-16 | Chef de liste : création et publication des listes de service ; le COMAEQ porte le service courant | Documentée | Incohérence | B3 | 19 |
| RM-17 | Un administrateur technique gère la plateforme, pas le fonctionnement métier | Documentée | V-NC | B1 | 19 |
| **D. Processus de travail quotidiens** | | | | | |
| RM-18 | Le marin voit sa journée : où être, quoi faire, quoi savoir, avec qui, quoi signaler | Documentée | V-C (parcours rejoués) | — | 19 |
| RM-19 | Service courant : le BSC orchestre ; la feuille de service est le point de convergence du jour J | Documentée | V-C | — | 19 |
| RM-20 | Un chef attribue une tâche à un marin de son périmètre ; le marin la suit, la bloque avec motif ; le chef voit le blocage | Documentée | V-C | — | 19 |
| **E. Maintenance et répartition des installations** | | | | | |
| RM-21 | Le bord est le premier niveau de maintenance autorisée : exploitation, contrôle, diagnostic, entretien, compte rendu, essais | Documentée | V-C | — | 19 |
| RM-22 | Arborescence bâtiment → domaine → installation → équipement → sous-équipement → composant | Documentée | PC | — | 19 |
| RM-23 | Correctif : signalement → diagnostic → criticité → impact → réparation → essais → retour en service | Documentée | PC | — | 19 |
| RM-24 | Compte rendu d'intervention notifié au chef de secteur, sans visa, modifications tracées | Documentée | V-NC partiel | Message : correction immédiate ; comportement voulu pour les installations | 19 |
| RM-25 | Fiche matériel flotte : un bord ne la publie pas seul (circuit en 7 étapes) ; fiche d'installation adaptable au bord | Documentée | NV | — | 19 |
| RM-26 | Travail terminé ≠ matériel disponible : contrôle, essais, retour en service | Documentée | NV | Besoin à confirmer | 19 |
| **F. Quarts et services MER/QUAI** | | | | | |
| RM-27 | Quart à la mer, service à quai et garde sont des notions distinctes ; le mode MER/QUAI du bâtiment se déduit des mouvements, jamais d'un champ libre | Documentée | V-C | — | 19 |
| RM-28 | Aucun rythme, horaire ou durée de quart n'est codé en dur ; les horaires sont des attributs de chaque poste | Documentée | V-C | — | 19 |
| RM-29 | Régimes (bordées, tiers, quart, cinquième, sixième), « hommes morts », « de musique » | Documentée (cadrage sans GO) | Conforme à l'absence (DIFF) | GO du PO | 19 |
| RM-30 | Fraction de service à quai : postes requis tous pourvus ; composition-type paramétrable ; contrôle des qualifications seulement plus tard | Documentée (cadrage) | NV | Oui (GO) | 19 |
| RM-31 | La feuille de service et le tableau de quart sont deux supports distincts | Documentée | V-C | — | 19 |
| RM-32 | Échange de service : A → B → chef de liste ; l'historique conserve l'échange ; l'impossibilité est expliquée | Documentée | PC | — | 19 |
| RM-33 | Génération automatique des tours abandonnée ; planification manuelle avec contrôle | Documentée | V-C | — | 19 |
| **G. Circuits de validation** | | | | | |
| RM-34 | Feuille de service : chef de secteur → chef de service → COMAEQ | Documentée | PC | B1 | 19 |
| RM-35 | Listes : brouillon → proposition → validation → publication ; version publiée active jusqu'à validation | Documentée | PC | B | 19 |
| RM-36 | Document : rédaction → validation par une autre personne → publication, versions conservées | Documentée | V-C | — | 19 |
| RM-37 | Formation : candidature → hiérarchie → BRH → organisme ; validation par un référent de la formation | Documentée | PC | — | 19 |
| RM-38 | Fiche d'installation : section/secteur → service → COMA ; fiche flotte : 7 étapes jusqu'à la publication au catalogue | Documentée | NV | — | 19 |
| RM-39 | RETEX : proposé, validé par les habilités (COMA référent d'abord), publié comme document | Documentée | NV | — | 19 |
| RM-40 | Relève de double équipage validée par les autorités des deux équipages ; date d'effet ; fuseau du bâtiment | Documentée | NV | DP-02 (passation) | 19 |
| RM-41 | Prêt à appareiller : validation avec confirmation explicite tracée | Documentée | NV | Droits de saisie à décider (tâche ouverte) | 19 |
| **H. Terminologie métier** | | | | | |
| RM-42 | Ne pas afficher « chef de groupement » ni « CAN » ; utiliser les sigles et fonctions réels | Documentée | V-C | — | 19 |
| RM-43 | « Responsable de classe » = IRB ; « responsable de spécialité » = ALFAN Exploitation | Documentée | V-C | — | 19 |
| RM-44 | Annonces : Information / Important / **Critique** | Documentée | Incohérence mineure | Choisir le terme | 19 |
| RM-45 | Vocabulaire du quart : musique, homme mort, bordée, tiers… | Documentée (cadrage) | NV (non demandé en développement) | GO du PO | 19 |
| RM-46 | Messages PÉPIN, CRAT, RAV/c : circuits non validés, pas d'implémentation officielle | Documentée (différé) | Conforme à l'absence (DIFF) | Cartographie métier avant tout développement | 19 |

## C. Couverture des données de démonstration (audit 20)

Détail dans `audits/AUDIT_20_DONNEES_DEMONSTRATION.md` §4 à §6.

| Dimension | Résultat | Audit |
|---|---|---|
| Profils sondés avec un espace personnel riche | 3 sur 16 (`equipier_a`, `equipier_a2`, `chef_secteur_a`) | 20 |
| Profils sans aucune donnée propre hors notifications | 5 ; suivi à terre : aucune donnée ni notification | 20 |
| Machines à états entièrement couvertes | maintenance, tâches, échanges, anomalies, absences, notifications | 20 |
| Machines à états incomplètes | ticket (2 états absents), feuille de service (4), relève (4), candidature (6, aucune), difficulté (3), document (2), RETEX (2), annonce (1), liste de quart (1) | 20 |
| Cas limites d'organisation exercés | double équipage, modes MER/QUAI/non renseigné, échange, tâche bloquée, remplacement actif | 20 |
| Cas limites d'organisation **non** exercés | secteur sans section, marin transversal, COMAEQ vacant, COMAVIA, compte désactivé, suppression ou archivage | 20 (AUD-036) |

## Synthèse

| Partie | État | Nombre |
|---|---|---|
| A. Exigences | PC | 23 |
| A. Exigences | V-C | 11 |
| A. Exigences | NV | 6 |
| A. Exigences | DIFF | 4 |
| A. Exigences | V-NC | 3 |
| A. Exigences | ABS | 1 |
| B. Règles métier | V-C | 18 |
| B. Règles métier | PC | 11 |
| B. Règles métier | NV | 9 |
| B. Règles métier | Conforme à l'absence (DIFF) | 3 |
| B. Règles métier | V-NC | 3 |
| B. Règles métier | Incohérence | 2 |

Total : 48 exigences et 46 règles métier. Aucune ligne n'est déclarée conforme sur la seule existence du code ; « V-C » est toujours limité au périmètre de la colonne Preuve.
