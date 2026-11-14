# Rapport des corrections V1 après relecture indépendante

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE** (précaution documentaire, pas une classification officielle). Date : 14/11/2026. Branche `claude/fervent-wright-kl6gtx`. Base : commit `028086e`. Phases 4 à 13 non commencées ; aucun code applicatif touché ; `main`, anciens documents et PDF d'origine intacts.

## 1. Pages avant / après
| Document | Avant | Après | Pourquoi |
|---|---|---|---|
| Guide utilisateur | 18 p. | **15 p.** | Captures recadrées (menu retiré) : une capture par page, plus grande ; étape 3 regroupe avant/après |
| Référentiel fonctionnel | 9 p. | 9 p. | Tableaux ajustés, nouveau constat NE-07 |
| Dossier technique | 9 p. | 9 p. | Tableau des routes sans mot coupé ; S25 détaillé |
| Registre | 36 p. | **33 p.** | Constats raccourcis dans la table des anomalies ; sections B et D sans saut de page |

## 2. Corrections de pagination demandées
| Page signalée | Constat vérifié | Correction |
|---|---|---|
| GU 3 et 8 | Blanc avant captures paysage : confirmé | Le texte du guide est repris sur la page suivante ; plus de blanc anormal avant une capture. Reste le blanc de **fin de page** après une capture (≈ 20 %), justifié par le passage en paysage |
| RE 36 | Fin du tableau des décisions seule | Constats raccourcis ; le tableau se termine sur une page pleine (RE 33) |
| RE 16, 21, 27 | Fins de section peu remplies | Sections « Points à confirmer » et « Propositions » enchaînées sans saut ; le reste (fin d'une fiche d'écart, p. 16) est **conservé : justifié** |
| DT 9 | Peu remplie | Reste en fin de chapitre (≈ 60 %) : **justifié** |
Aucune taille de police réduite.

## 3. Captures du guide
Recadrage sur la zone utile (menu latéral et bandeau retirés ; la ligne « Navigation » de la légende dit où se trouve l'écran) ; texte d'écran passé d'environ 6 pt à 9–12 pt ; repères conservés et recalculés ; messages verts parasites exclus par le cadrage (étape 5) ; captures redondantes regroupées (étape 3 : 3 vignettes de 2 captures) ; présentation homogène (même cadre, même légende). Les captures restent **provisoires** (12/11/2026, textes anglais « Choose File » visibles) : remplacement en phase 4, non engagée. Aucune modification du logiciel.

## 4. Cohérence fonctionnelle (maintenance non conforme)
Vérifié dans le navigateur (14/11/2026, comptes fictifs) et le code :
- **Découverte** : à la fin d'un compte rendu non conforme sur une **installation**, l'écran annonce « Un ticket correctif sera (ou a été) ouvert automatiquement » alors que **0 ticket** est créé (échéance « En validation »). Écart documenté **NE-07**. Le lien « signaler une anomalie » de cet écran n'apparaît que pour un relevé hors plage.
- **Guide** : un tableau « Ce que Matrix fait seul / ce que vous pouvez faire / limite » distingue 🟢 actuel, 🟣 proposition (D1, D2) et A20 ; le signalement manuel est dit « manuel et facultatif, ni automatique ni validation ».
- **Schémas** : S25 simplifié (référentiel) et S25d détaillé avec références de code (dossier technique), même fond ; S25 et S25d ajoutent l'état « Annulée » **automatique** (fiche remplacée), absent de la version précédente ; le guide ne montre aucune règle non arbitrée comme décidée.
- Registre : NE-07 ajouté (7 nouveaux écarts) ; `DEC-PRE-06` et `DEC-DRT-05`, jusque-là « réalisées » à tort alors qu'un de leurs lots n'est pas livré, deviennent « partielles ».

## 5. Contrôles (reconstruction du 14/11/2026)
C1 : 13/13 et 8/8 titres retrouvés ou retirés ; C5 : 0 violation (le guide et le référentiel ne citent plus un chemin d'épreuve ni un chemin de code) ; C6 : sommaires vérifiés, 0 écart ; C7/G2 : 0 plage ; C4 (DT) : 0 erreur ; C8 : 0 bloquant ; C13 : 0 fichier hors documentation modifié ; schémas : 46 sources, 0 sous 8 pt ; registre : tous les contrôles G2 verts.

## 6. Inspection (voir journaux)
- `JOURNAL_INSPECTION_V1_CORRIGE.csv` : 66 pages des PDF corrigés. **Vues sur le build final : GU 13, RF 7, DT 5, RE 8** ; vues sur un build antérieur seulement : 6 ; **non vues individuellement : 27** (RE 25, DT 2 : couverture et sommaire). Résolution : 96 dpi, deux pages côte à côte ; **aucune page à 100 % de la taille d'écran réelle** ; je ne peux pas juger un rendu sur un écran physique.
- `JOURNAL_INSPECTION_72_PAGES_INITIALES.md` : seules **7 pages initiales** ont été examinées individuellement dans cette séance.
**Je n'ai donc pas atteint l'exigence « 72 pages individuellement » ni « toutes les pages corrigées » : je ne déclare pas ces pages inspectées.**

## 7. Réserves ouvertes
1. Inspection incomplète (voir §6) ; la relecture indépendante de ChatGPT est précisément utile sur le registre (RE 3–14, 17–26, 29–30, 33) et sur GU 1–2.
2. Captures provisoires (textes anglais, date du 12/11).
3. Fin de page blanche résiduelle après les captures paysage, ≈ 20 % (justifié).
4. Renvois entre documents (`RF §1`, `RE §7`) : mentions de texte, non liens.
5. 20 décisions « à instruire » ; C2 = revue manuelle de l'auteur.
6. NE-07 découvert par ce travail : la formulation de l'encadré de fin de compte rendu n'a pas été corrigée (ce serait un changement de logiciel, non autorisé).

## 8. Recommandation
**V1 validable avec réserves, sous condition d'une nouvelle relecture indépendante** : la structure, le style, la densité (texte d'écran lisible, plus de blanc anormal avant capture) et la cohérence fonctionnelle de la maintenance non conforme sont corrigés et vérifiés dans le navigateur et le code. Mais mon inspection visuelle reste incomplète et les captures sont provisoires ; je ne recommande donc pas de valider V1 avant le second audit indépendant. Aucune rédaction complète n'est lancée.
