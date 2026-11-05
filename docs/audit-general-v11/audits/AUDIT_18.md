# Audit 18 — Cohérence globale et stratégie (consolidation des 20 audits)

**Statut : Clôturé avec réserves.** Ce rapport **consolide** les conclusions des audits 01 à 17, 19 et 20 ; il s'appuie sur **un registre unique des anomalies** (`../04_REGISTRE_ANOMALIES.csv`, vue triée `../04_REGISTRE_ANOMALIES_TRIE.md`) et sur **une matrice unique de conformité** (`../03_MATRICE_CONFORMITE.md`, qui réunit les exigences du référentiel, les règles métier de l'audit 19 et la couverture de l'audit 20). Il ne contient aucune mesure nouvelle : il croise et hiérarchise.

## 1. Les 20 audits, leurs conclusions et leurs références

Organisation en six phases (addendum) : **1** référentiel historique (01) ; **2** cohérence Marine (19) ; **3** fonctionnalités, organisation, UX (02 à 12) ; **4** fondations techniques (13 à 17) ; **5** données de démonstration (20) ; **6** synthèse (18).

| Phase | Audit | Statut | Conclusion | Anomalies du registre | Exigences (matrice 03) |
|---|---|---|---|---|---|
| 1 | 01 Besoin et historique | CAR | La vision initiale est conservée ; les écarts sont des décisions datées, non des oublis. | AUD-006, AUD-004, AUD-005 | — |
| 2 | 19 Cohérence métier Marine nationale | CAR | Le code suit les règles écrites sur la hiérarchie, les circuits et la terminologie ; écarts sur les droits par niveau et la structure. | AUD-006, AUD-024, AUD-037, AUD-041 | 46 règles (RM) |
| 3 | 02 Configurabilité | CAR | Droits et modules configurables par bâtiment ; structure non autonome et suppression dangereuse. | AUD-020, AUD-019, AUD-034, AUD-012, AUD-021, AUD-022, AUD-028 | 3 |
| 3 | 03 Première mise en service | CAR | Installation, migration et nouveau bâtiment fonctionnent ; production non cadrée (HTTPS, sauvegarde). | AUD-009, AUD-011, AUD-019, AUD-012 | — |
| 3 | 04 Usage quotidien | CAR | Onze parcours rejoués sans erreur ; efficacité réelle non mesurée. | AUD-008, AUD-013, AUD-016, AUD-026, AUD-027 | 2 |
| 3 | 05 UX et accessibilité | CAR | Écran « Quarts » conforme aux maquettes et à la charte ; accessibilité de base correcte ; titres d'onglet identiques. | AUD-003, AUD-008, AUD-016, AUD-018, AUD-042 | 6 |
| 3 | 06 Rôles et permissions | CAR | Le serveur refuse correctement ; des droits par niveau restent trop larges. | AUD-001, AUD-014, AUD-015, AUD-008 | 6 |
| 3 | 07 Calendrier | CAR | Calendrier central à 7 sources, étanche ; conflits non détectés (fonction absente). | AUD-025 | 2 |
| 3 | 08 Maintenance et installations | CAR | Confirmation critique correcte ; non-conformité sur installation sans ticket, message faux. | AUD-023 | 4 |
| 3 | 09 Quarts et services MER/QUAI | CAR | Circuit de la feuille conforme au titulaire final ; voies directes et doublons sur listes publiées. | AUD-001, AUD-014, AUD-015, AUD-033 | 8 |
| 3 | 10 Logistique | CAR | Invariants du stock solides ; prêts et retours différés. | AUD-040 | 1 |
| 3 | 11 Communication | CAR | Accès par propriétaire et périmètre corrects ; archivage et rappels planifiés limités. | AUD-038, AUD-039, AUD-041 | 3 |
| 3 | 12 Formations et autres modules | CAR | Circuits documentaire et de formation fonctionnent ; modules secondaires peu testés. | AUD-030, AUD-007 | 4 |
| 4 | 13 Architecture | CAR | Code volumineux et très testé ; vues géantes à découper, dette d'hygiène. | AUD-022, AUD-032, AUD-005, AUD-007, AUD-029 | 2 |
| 4 | 14 Données et intégrité | CAR | PostgreSQL et migrations sûrs ; suppressions en cascade destructrices. | AUD-020, AUD-034, AUD-021, AUD-028 | 2 |
| 4 | 15 Sécurité et résilience | CAR | Périmètres étanches ; démonstration, secrets et HTTPS à cadrer ; pas de limitation de connexions. | AUD-009, AUD-001, AUD-011, AUD-031, AUD-010, AUD-017, AUD-035 | 2 |
| 4 | 16 Qualité des tests | CAR | Suite efficace sur les circuits travaillés ; couverture par action insuffisante. | AUD-002, AUD-003, AUD-030, AUD-013 | — |
| 4 | 17 Déploiement et exploitation | CAR | Sondes rejouables ; aucune procédure de production ni de sauvegarde. | AUD-011, AUD-031, AUD-002, AUD-010, AUD-017, AUD-032, AUD-039 | 1 |
| 5 | 20 Données de démonstration | CAR | Démonstration riche en quarts, tâches et échanges ; états et cas limites majeurs absents. | AUD-009, AUD-024, AUD-036 | matrice de couverture |
| 6 | 18 Cohérence globale | CAR | Consolidation de ce rapport. | — | — |

(CAR = clôturé avec réserves ; justification dans `../09_BILAN_DES_AUDITS.md`.)

## 2. Registre unique des anomalies : consolidation

**{len(corps)} entrées** : P0 2, P1 7, P2 16, P3 17.

- **Par catégorie** : TECHNIQUE 13, MÉTIER 8, BUG 6, SÉCURITÉ 5, ÉVOLUTION 5, UX 5.
- **Par origine** : Préexistant 37, Non 2, Introduit 1, Mixte 1, Présent 1 (les entrées « Non déterminé », « Mixte », « Présent sur main » sont détaillées dans `../10_COMPARAISON_MAIN_V11.md`).
- **Dédoublonnage** : chaque anomalie n'apparaît qu'une fois, avec la liste des audits qui la constatent (par exemple AUD-014 : audits 06 et 09 ; AUD-020 : audits 02 et 14). Les anomalies déjà connues de la recette du dépôt (ANO-008, 010, 012, 013) sont reprises (AUD-038, 039, 042).
- **Audit sans anomalie propre** : le 18 (synthèse).

## 3. Matrice unique de conformité : consolidation

`../03_MATRICE_CONFORMITE.md` réunit : **A.** 48 exigences du référentiel (états V-C, V-NC, PC, NV, DIFF, ABS) ; **B.** 46 règles métier de l'audit 19 avec source, implémentation, conformité, preuve et décision nécessaire ; **C.** la couverture de l'audit 20 par module et profil. Chaque ligne renvoie à son audit. La matrice de **non-régression** reste séparée (`../05_MATRICE_NON_REGRESSION.md`).

## 4. Six problèmes transversaux

| N° | Problème | Audits | Anomalies | Cause commune |
|---|---|---|---|---|
| T1 | **Droits fondés sur le niveau** plutôt que sur la fonction | 02, 06, 09, 12, 19 | AUD-014, 015, 022 | registre de seuils en niveaux ; administrateur d'unité au-dessus du commandant |
| T2 | **Organisation du bord modifiable mais non gouvernée** : suppression physique, archivage sans effet, périmètre déduit d'un champ vide, structure hors de portée du bord, départ d'un marin = suppression | 02, 03, 14, 19, 20 | AUD-019, 020, 021, 028, 034, 037 | trois mécanismes indépendants (suppression, périmètre, archivage) jamais pensés ensemble |
| T3 | **Interface et serveur ne disent pas la même chose** : liens refusés, messages inexacts, accueil non filtré | 04, 05, 06, 08, 19 | AUD-008, 016, 023, 027, 041 | masquage et textes réécrits à chaque écran |
| T4 | **Mise en service et exploitation non cadrées** | 03, 15, 17 | AUD-009, 010, 011, 017, 031, 032, 035, 039 | dépôt organisé pour le développement ; aucun mode « bord » défini |
| T5 | **Suite verte, parcours rouges** | 13, 16 | AUD-002, 003, 029, 030, 033 | tests écrits pour les règles actuelles, pas pour l'intention métier ; 16 clés de seuil sans test |
| T6 | **Démonstration non représentative** : états et cas limites absents, noms réels | 20, 19 | AUD-024, 036 | générateurs centrés sur le matelot A et le chef de secteur A |

## 5. Contradictions entre sources

| Sujet | Source A | Source B | Traitement |
|---|---|---|---|
| Passation | « maintenue en V1, configurable » | « retirée par la PR #7, différée » | DP-02 |
| QR codes | « hors V1 » | route de scan active | DP-06 |
| Administrateur technique | « gère la plateforme, pas le métier » (Cahier §5) | niveau supérieur au commandant | T1 |
| Chaîne « inspection → ticket » | documentée comme générale | limitée au matériel mobile ; message faux pour les installations | AUD-023 |
| Niveaux d'annonce | « Critique » (cahier, Notion) | « Urgent » (interface) | AUD-041 |
| Charte graphique | lien Google Fonts (charte générique) | polices auto-hébergées (Matrix) | Matrix conforme à « Internet n'existe pas » |
| Structure du bord | « configurable par les responsables » (Cahier §4, brief) | écran réservé au compte de flotte | AUD-019 |

## 6. Fonctionnalités orphelines ou résiduelles

QR (scan actif hors V1) ; Rondes (modèles sans route ni test) ; champs `archived` (aucun effet) ; `boto3` et `django-storages` (probablement inutiles) ; vocabulaire de quart cadré mais non implémenté ; clé de registre `structure_navire_ecriture` (API seulement) ; vue collective du calendrier par défaut dans l'API.

## 7. Dépendances entre corrections (ordre recommandé)

1. **P0 sans dépendance** : verrou de la démonstration (AUD-009, `propositions/P06`) ; interdiction de la suppression physique d'unités et de comptes avec historique (AUD-020, 034, `propositions/P07`).
2. **Socle de désignation** (`propositions/P02`, options A puis B) avant les écrans de structure, car la fonction « gestion de la structure » en dépend.
3. **États de rattachement** (`propositions/P01`) avec archivage effectif (AUD-028) : prérequis de l'assistant de transfert (`propositions/P04`) et de l'import de personnel (DP-11).
4. **Déploiement de référence** (`propositions/P03`) : indépendant du fonctionnel, dépend des responsables SIC ; en parallèle.
5. **Tests** : chaque correction ajoute son test ; tests navigateur versionnés (AUD-003) et CI hors ligne (AUD-002) avant la première fusion de correctifs.
6. **Démonstration** : compléter les générateurs (AUD-036) **après** les corrections qui changent les états (désactivation, états de rattachement), sinon elle sera à refaire.

## 8. Ce que cette consolidation ne peut pas dire

Voir `../09_BILAN_DES_AUDITS.md` : efficacité réelle des marins, validation SIC, expert du bord, volumes réels, poste Windows, tablette, lecteur d'écran.

## Clôture (addendum)

**Statut : Clôturé avec réserves.** La consolidation couvre les 20 audits ; ses réserves sont celles des audits consolidés.
