# Rapport de la passe finale — état intermédiaire : un contrôle C8 en échec, arrêt avant toute reconstruction supplémentaire

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire. Date : 20/11/2026. Branche `claude/fervent-wright-kl6gtx`. Ce rapport ne valide ni le contenu métier, ni le logiciel, ni la diffusion. Aucun changement applicatif, aucune décision métier, aucune PR, aucune fusion, aucune phase 13.

## 1. Résultat en une phrase

Les corrections approuvées (T1 à T4, D-04, D-05, D-06, D-07, phrase des quarts) sont faites et vérifiées, et les deux reconstructions autorisées (référentiel n° 7, dossier technique n° 3) sont exécutées ; **mais le contrôle C8 échoue sur les deux PDF reconstruits (un titre de section suivi d'une seule puce en bas de page chacun)**. Corriger ces deux défauts demande une reconstruction de plus pour chacun. Conformément à votre consigne, **je m'arrête et je vous présente le problème** (§6).

## 2. PDF obtenus (`pdf_candidats/`)

| PDF | Pages V2 → maintenant | Taille (octets) | SHA-256 | Statut |
|---|---|---|---|---|
| Guide utilisateur | 86 → 86 | 19 807 858 | `966983dc5aa7ee23e644747f303b98ae37526b4641143ca1f400ed254242f0a2` | **identique octet pour octet à V2** |
| Référentiel fonctionnel | 135 → **137** | 6 542 258 | `d0408e8e3ee8267c50e054d64cbc99b53afe77cd1191cef8a9fda26aa7b0359d` | reconstruit (n° 7) |
| Dossier technique | 94 → **96** | 5 272 854 | `4b3545e6e326eaa0a4b9070c491e3e998c2edd4e50530d1aa1ed038d20292079` | reconstruit (n° 3) |
| Registre | 52 → 52 | 1 812 916 | `61ee477df0ec8fc94ceaf16c5119db6aaba7ad6c8d0ac109b03fc27ebe910e38` | **identique octet pour octet à V2** |

Écart avec le plan : le dossier technique gagne 2 pages (prévu : inchangé), à cause de l'ajout de la phrase sur la provenance historique des tests (chapitre Qualité) et de S26 redessiné. Le référentiel gagne 2 pages (prévu : 136 à 138).

## 3. Corrections réalisées

| Réf. | Correction | Fichiers |
|---|---|---|
| T1, T2, T3 | Tickets : matériel mobile = ticket automatique ; installation = aucun ticket (NE-07, message inexact **non** présenté comme corrigé) ; relevé hors plage = lien pré-rempli vers une anomalie ; D1 = proposition 🟣 non arbitrée | RF `03_vue_ensemble`, DT `21_interactions_modules` |
| T4 | Libellés « matériel mobile » dans S24 et S26 (SVG régénérés) | `schemas/src`, `schemas/svg` |
| D-04 | S02, S14, S22, S27, S38 redessinés en schémas de flux ; tableau d'éléments (codes opaques) supprimé ; tous les tableaux « De / Condition / Vers » conservés et complétés (S02 : relations calendrier, notifications, discussions, ticket et noyau ; S14 : condition « tâches et programme absents du flux » ; S38 : ligne des lots livrés) | RF 03, 07, 11, 13, 25 |
| D-05 | « Dossier V1.2 (comptes rendus des lots L01, L05, L02 et L03) » | RF 25 |
| D-06 | Index généré des **46 schémas**, présence réelle par document (guide, référentiel, dossier technique), nom homogène, renvois résolus ; 5 schémas non repris dans les documents sont listés (S09, S10b, S24, S28b, S40) | `outils/generer_index_schemas.py`, RF 31 |
| D-07 | Tests « de l'ensemble 3 » reformulés en **preuve historique de l'édition initiale, non rejouée pour la révision 2** (fiches Logistique, Formations, Documentation et RETEX, Appareillage, Organisation, Rôles, Historique ; chapitre Qualité du dossier technique) ; seuls les tests de la prise en main sont présentés comme exécutés pour cette révision | RF 04, 05, 13, 14, 15, 16, 26 ; DT 24 |
| — | Phrase mal formée « comptes rendus de lots compte rendu du lot L02 » | DT 08 |
| D-12 | Aucune modification (17 captures partielles maintenues) | — |

**Défaut hérité de V2, corrigé à cette occasion.** Le dossier technique de V2 (94 pages) n'avait pas été reconstruit après la correction de l'état documentaire : ses pieds de page indiquaient encore « projet en cours de refonte — maquette pilote V1, non validé ». Le PDF actuel porte « PDF candidat de la révision 2 — non validé ». C'est un défaut que ma vérification de V2 n'avait pas relevé.

**Schémas S02.** Le placement automatique du moteur de schémas ne rendait pas lisible le croisement de trois sortes de liens ; S02 est donc dessiné par un script dédié (`outils/dessiner_s02.py`, source du dessin, au lieu d'un fichier Mermaid). Signification des flèches : bleu plein = alimente le calendrier central ; orange en tirets = émet des notifications ; gris pointillé = s'appuie sur le noyau commun (dépendance technique) ; vert = discussion attachée à un objet ; flèche pleine verticale = ticket correctif créé pour un contrôle non conforme sur un matériel mobile. Les flèches « calendrier » et « notifications » sont recoupées avec les imports réels du code (voir §4) ; les flèches fonctionnelles (« émet », « alimente ») expriment ce que les modules font les uns pour les autres, d'après le référentiel ; seule la dernière série est une dépendance technique.

## 4. Contrôles

| Contrôle | Résultat |
|---|---|
| Sources et aperçus HTML, avant génération | C1 à C14 applicables : 0 bloquant (rapports `apercus_G1/`) ; relations des schémas : voir ci-dessous |
| Relations des 5 schémas (`controle_relations_schemas.py`) | **0 écart** : S14 3 flèches, S22 5, S27 4, S38 5, chacune présente dans le tableau et inversement ; S02 : 7 modules vers le calendrier = exactement les imports de `calendar_app` (hors comptes et discussions), 12 modules vers les notifications tous importés par `notifications`, 6 groupes vers le noyau. Limites : « dashboard » et « calendar_app » apparaissent dans l'inventaire de `notifications` mais ne sont pas des émetteurs (ils consomment) ; ils ne sont pas dessinés comme tels |
| Lisibilité des schémas | 46 / 46 à ≥ 8 pt (S02 : 8,2 pt) |
| C3, C5, C6, C7, C13, C14 sur les PDF reconstruits | 0 écart ; sommaires exacts (RF 39 entrées, DT 38) ; mention sur 137 et 96 pages |
| C4 | 666 références de code, 0 erreur |
| C9, C1, C2, C11 | 0 écart ; matrice des droits identique ; **125 / 125 décisions** du registre PDF portent l'état de `registre.json` ; aucun statut modifié |
| Cohérence des tickets (recherche automatique sur le texte des quatre PDF) | 0 phrase « ticket + non conforme + création » sans précision matériel mobile / installation dans le guide, le référentiel et le dossier technique. **1 occurrence dans le registre** : voir §5 |
| **C8** | **ÉCHEC : RF 1 bloquant (titre orphelin p.69, section 12.2.2), DT 1 bloquant (titre orphelin p.89, section 23.2)**. Pages < 40 % : RF 5 (p.8, 16, 59, 130, 137), DT 5 (p.7, 9, 12, 56 : une seule ligne « Sources » seule, 82) |
| C12 (constructions temporaires, hors livrables) | Texte extrait et nombre de pages **identiques** sur deux constructions de contrôle successives du référentiel et du dossier technique |
| Guide et registre | **octets identiques à V2** (SHA-256 ci-dessus) : aucune modification |

## 5. Généralisation trouvée hors périmètre autorisé

Le **registre** (écart A25, « modules désactivés encore actifs par certains chemins ») dit : « … enchaînement interne : ticket créé depuis une maintenance non conforme » sans préciser « matériel mobile ». Le registre devant rester inchangé, je ne l'ai pas modifié. Correction proposée : ajouter « sur un matériel mobile », c'est-à-dire une reconstruction du registre (la 3e) ; elle est à votre décision.

## 6. Problème bloquant et demande d'autorisation

**Défaut.** Après insertion des schémas redessinés, la pagination déplace deux titres : RF p.69 (« 12.2.2 Ce que font les responsables », suivi d'une seule puce avant la coupure de page) et DT p.89 (« 23.2 Ce qui n'est pas couvert », idem). Ce n'est pas un titre entièrement isolé (une ligne de contenu le suit), mais le contrôle C8 le classe bloquant et je ne l'ai pas contourné ni assoupli.

**Correction minimale proposée** (générique, dans l'outil, sans toucher aux textes) : règle de mise en page qui interdit qu'un titre de niveau 3 soit suivi de moins de deux lignes avant un saut de page, et qui garde ensemble un titre et le début de sa liste.

**Reconstructions nécessaires.** Référentiel n° 8 et dossier technique n° 4 ; guide et registre inchangés. Si vous acceptez aussi la correction du registre (§5), une reconstruction du registre (la 3e) s'ajoute. J'engagerais alors, **sur ces dernières versions seulement**, l'inspection visuelle complète, car la pagination du référentiel et du dossier technique change à nouveau.

## 7. Inspection (journal : `pdf_candidats/JOURNAL_INSPECTION_V3.csv`)

| Document | Pages | Inspectées (build actuelle) | Contenu identique à une page inspectée en V2 | Non revues sur cette build |
|---|---|---|---|---|
| Guide | 86 | 86 (V2, fichier identique) | — | 0 |
| Référentiel | 137 | 20 | 20 | **97** |
| Dossier technique | 96 | 2 | 45 | **49** |
| Registre | 52 | 52 (V2, fichier identique) | — | 0 |

Pages vues à 100 ppp sur cette build : RF 9, 16, 17, 18, 19, 20, 69, 70, 83, 84, 95, 96, 97, 98, 127, 128, 134, 135, 136, 137 (cinq schémas redessinés, index complet, tableaux de relations, pages historiques) ; DT 89, 90. Constats : S02, S14, S22, S27, S38 lisibles (le texte de S02 est petit mais lisible) ; tableaux de relations complets ; index sans défaut. **Réserves visuelles** : RF p.16 (début de chapitre 4 : texte court, le schéma S02 passe en page suivante : 38 % de remplissage) ; DT p.56 (une ligne « Sources » seule sur la page). Je n'ai pas inspecté la totalité des pages décalées : 146 pages sont notées « NON REVUE » ou « reprise V2 » et ne sont pas déclarées inspectées.

## 8. Reconstructions et budget (après la candidate de phase 10)

| Document | Après V2 | Cette passe | Total | Dépassement du budget de 2 |
|---|---|---|---|---|
| Guide | 5 | 0 | 5 | + 3 |
| Référentiel | 6 | 1 | **7** | + 5 |
| Dossier technique | 2 | 1 | **3** | + 1 |
| Registre | 2 | 0 | 2 | 0 |

Constructions temporaires (hors livrables, non comptées) : 4 pour le contrôle de reproductibilité C12 de cette passe, hors dépôt. Les compteurs ne sont pas remis à zéro.

## 9. Réserves

1. C8 en échec sur RF p.69 et DT p.89 (§6).
2. Registre A25 : généralisation « ticket créé depuis une maintenance non conforme » (§5).
3. Pages non revues sur cette build : référentiel 97, dossier technique 49.
4. Schémas S09, S10b, S24, S28b et S40 non repris dans les documents (choix de la maquette) ; la généalogie des branches (S40) ne figure plus sous forme de figure.
5. Volumes : guide 86, référentiel 137, dossier technique 96, registre 52, hors des cibles initiales.
6. Une conformité automatique n'est pas une validation métier.

## 10. Décisions demandées

1. Autoriser la correction de mise en page générique et deux reconstructions supplémentaires (référentiel n° 8, dossier technique n° 4), suivies de l'inspection complète des pages de ces deux PDF.
2. Décider de la correction du registre (§5) et de sa reconstruction n° 3.
3. Confirmer que les pages « reprise V2 » peuvent être considérées comme inspectées à contenu identique, ou exiger leur revue.
