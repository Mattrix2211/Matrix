# Rapport de révision du jalon V1 — arbitrages du PO traités

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE** (précaution documentaire, pas une classification officielle). Date : 14/11/2026. Branche `claude/fervent-wright-kl6gtx`. Suite du rapport `RAPPORT_JALON_V1.md` (commit `c2fdd7d`).
> **Phases 4 à 13 : non commencées. V1 : en attente de validation explicite.** Aucun code applicatif touché ; sources initiales, anciens PDF et tests A14/A20/A25 inchangés.

## 1. Les six arbitrages
| # | Arbitrage du PO | Réalisation | Preuve |
|---|---|---|---|
| 1 | Supprimer les pages de partie presque vides | Le constructeur n'émet plus de page de partie : un surtitre discret précède le premier titre | RF p. 3, GU p. 3, DT p. 3 (0 page de partie) |
| 2 | Repères discrets, lisibles, sans masquer d'action | Repères de 4,4 mm, marge gauche de l'élément, ombre fine ; conservés | Vus sur GU p. 4 et 5 : aucun bouton ni libellé masqué |
| 3 | Fiches : écarts et décisions pertinents, renvoi au registre central | RF : 6 décisions (sur 21) et 5 écarts (sur 7) ; deux encadrés « Registre central » avec renvois `RE §7`, `RE §2`, `RE §3` | `2_referentiel_fonctionnel/12_fiche_maintenance.md` |
| 4 | S09 : vue synthétique par groupes ; détail au dossier technique | `S09_groupes_fonctionnels` (5 groupes, couples reliés par ≥ 5 liens, chiffres de l'inventaire) ; ancien S09 conservé sous `S09d_dependances_detail` pour le DT | `schemas/src`, `apercus_V1/DOSSIER_PRESENTATION_PILOTE_V1.pdf` p. 7 |
| 5 | C4 : distinguer code et preuves, pas d'erreur « attendue » | Nouveau `outils/verifier_references_refonte.py` : trois totaux séparés (code, preuves, clés du registre) ; toute référence introuvable est une erreur, jamais comptée comme réussite. DT : **36 références de code, 2 preuves, 4 clés, 0 erreur**. Essai négatif : 3 fausses références détectées | `apercus_V1/controle_C4_DT.md` |
| 6 | C2 renforcé par relecture manuelle | 14 affirmations étiquetées + 8 affirmations factuelles relues contre l'ancien texte et le code : **1 correction** (condition de la confirmation d'une installation critique) et **2 précisions** (état actuel des périodicités et des durées) | `apercus_V1/REVUE_MANUELLE_C2.md` |

## 2. Défauts trouvés et corrigés pendant la révision
- **Contrôle G2 trop faible** : il ne voyait pas les plages de décisions écrites entre guillemets de code (« `DEC-MAT-01` à `DEC-MAT-04` »). Les plages sont maintenant **dépliées en listes explicites** dans le registre et les contrôles G2 et C7 les détectent.
- **Registre** : titres d'écarts coupés au milieu d'un code (A18, A21) → titres courts rédigés ; l'ancienne mention de diffusion large n'est plus reproduite dans le registre.
- **Dossier technique** : mots coupés au hasard dans les tableaux de routes et de clés → césures contrôlées ; « trois tâches planifiées » contredisait la liste de huit : corrigé.
- **Dossier de présentation** : le schéma S09 affichait des balises `<b>` : corrigé.

## 3. État des contrôles (aperçus reconstruits le 14/11/2026)
| Contrôle | RF (9 p.) | GU (18 p.) | DT (9 p.) | RE (36 p.) |
|---|---|---|---|---|
| C1 titres de l'ancien chapitre retrouvés ou retirés | 13/13 | — | 8/8 | — |
| C5 séparation + mention provisoire sur chaque page | 0 violation | 0 | 0 | 0 |
| C6 sommaire et renvois (dont `RE §n`, maintenant résolus) | 0 écart | 0 | 0 | 0 |
| C8 mise en page automatique | 0 bloquant ; 1 page < 40 % | 0 bloquant ; 4 pages < 40 % | 0 ; 1 page < 40 % | 0 ; 5 pages < 40 % |
| C4 (DT) | — | — | 36 code, 2 preuves, 4 clés, 0 erreur | — |
| C13 application intacte | 0 fichier modifié hors documentation depuis `637de94` | | | |
| Schémas ≥ 8 pt | 45 sur 45 | | | |
Limite : un contrôle automatique n'est pas une vérification éditoriale. Voir `apercus_V1/INSPECTION_V1.md` pour la couverture exacte de mon inspection visuelle (partielle, non indépendante).

## 4. Livrable de présentation
`apercus_V1/DOSSIER_PRESENTATION_PILOTE_V1.pdf` (9 pages) : arbitrages réalisés, 7 pages représentatives des trois documents, S09 avant/après, choix graphiques, 8 points à arbitrer. Les trois PDF pilotes sont dans le même dossier (`Matrix_G0R2_1_…`, `_2_…`, `_3_…`, et `_5_…` pour le registre) : **je recommande de les ouvrir en entier plutôt que de se fier à la présentation.**

## 5. Réserves
1. **La relecture indépendante n'est pas faite.** Je n'ai inspecté qu'une partie des pages (voir le journal) et je suis l'auteur : ce n'est pas indépendant.
2. **Captures provisoires** (12/11/2026) : textes anglais du navigateur, messages de confirmation visibles.
3. **Fins de page blanches** avant les pages de capture paysage (GU p. 3) : à arbitrer.
4. **Renvois entre documents** : texte, pas liens.
5. 20 décisions restent « à instruire ».

## 6. À arbitrer
Voir la dernière page du dossier de présentation (8 points : fins de page, taille des captures, renvois, décisions « à instruire », captures provisoires, relecture indépendante, place du registre).

**Je ne lance rien de plus. J'attends votre validation explicite de V1.**
