> **Révision du 14/11/2026** : ce rapport est complété par `RAPPORT_V1_REVISION.md` (arbitrages du PO traités) et par `apercus_V1/DOSSIER_PRESENTATION_PILOTE_V1.pdf`. Les aperçus ont été reconstruits ; les chiffres de pages ci-dessous sont ceux du 13/11/2026.

# Rapport du jalon V1 — maquette pilote « Maintenance »

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, pas une classification officielle. Date : 13/11/2026. Branche `claude/fervent-wright-kl6gtx`. Plan de référence : `../PLAN_EXECUTION_REFONTE_G0.md`.
> **Statut : phases 0 à 3 exécutées ; arrêt au jalon V1 comme demandé.** Rien n'est rédigé au-delà du chapitre pilote. Aucun code applicatif touché, `main` intacte, aucune PR, aucune fusion, sources initiales et anciens PDF conservés.

## 1. Ce qui est livré

| Livrable | Fichier |
|---|---|
| **Aperçu PDF du guide utilisateur** (19 p.) | `apercus_V1/Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf` |
| **Aperçu PDF du référentiel fonctionnel** (11 p.) | `apercus_V1/Matrix_G0R2_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf` |
| **Aperçu PDF du dossier technique** (10 p.) | `apercus_V1/Matrix_G0R2_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf` |
| Registre initial (JSON, Markdown, HTML autonome) | `5_registre/registre.json`, `ECARTS_ET_DECISIONS.md`, `registre.html` |
| Contrôles : mesure de base, barrières, contrôles des aperçus | `baseline/`, `apercus_V1/controles_*.md` |
| Schémas retravaillés (44 sources) et mesure de lisibilité | `schemas/src`, `schemas/svg`, `baseline/schemas_lisibilite_v1.csv`, `schemas/tableaux/` |
| Outillage (constructeur, contrôles, générateurs) | `outils/` |
| Mapping ancien → nouveau (549 lignes), registre des faits (21 chiffres) | `MAPPING_ANCIEN_NOUVEAU.csv`, `faits.yaml` |

## 2. Comparatif avant / après (chapitre 12 « Maintenance »)

| | Avant (dossier G0 initial) | Après (maquette V1) |
|---|---|---|
| Emplacement | 1 chapitre diffusable (≈ 8 p.) + 1 complément technique (2 p.), dans **deux** PDF | **3 documents** par public : fiche (RF), parcours illustrés (GU), chapitre technique (DT) |
| Texte | 2 475 mots (diffusable) + 578 mots (technique) | 2 078 mots (RF), 1 053 mots (GU), 1 240 mots (DT) |
| Mention de diffusion | « DIFFUSION GÉNÉRALE » sur chaque page | « DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE » + précaution sur la couverture |
| Références internes (commit, branche, chemins de code) | présentes dans le « diffusable » | **absentes de GU et RF** (contrôle C5 : 0) ; réservées à DT |
| Cartouche en tête de chapitre | 5 lignes répétées | 1 ligne (public, module, écran, étiquettes) |
| Captures d'écran dans le chapitre | aucune | 12 (GU), profil et repères sur chacune |
| Sommaire | sans numéros de page | paginé, vérifié par le contrôle C6 (0 écart) |
| Décisions du PO | plages (« DEC-PER-01 à 04 ») | **21 décisions citées une à une**, avec état |
| Écarts | texte libre | tableau tiré du registre (A20, A21, A25, D1, D2, NE-01, NE-02) |
| Erreurs de l'audit | rondes présentées comme fonction (ch. 1), « impression non trouvée » (ch. 8) | **rondes** : « retiré de l'interface » ; NE-01 (bouton « Exécuter ») documenté |
| Étiquette ⚪ | « ◦ » minuscule | pastille « ◯ » lisible |

### Schémas : lisibilité à la largeur utile d'une page portrait
| Schéma | Avant (pt min) | Après (pt min) | Changement |
|---|---|---|---|
| S01 réseau | 6,2 | 8,0 | disposition verticale |
| S04 relève | 5,8 | 10,1 | libellés coupés |
| S05 cycle de vie d'une unité | 9,4 | 12,8 | refait en diagramme d'états simple |
| **S10 organisation** | **5,0 (illisible)** | 19,8 | **scindé en deux** (S10 et S10b) |
| S11 chaîne d'une requête | 7,2 | 8,7 | libellés coupés |
| **S13 page Aujourd'hui** | 5,8 | 10,3 | libellés coupés |
| S15 listes | 6,0 | 11,8 | disposition verticale |
| S25 états d'une occurrence | 9,4 | 11,3 | corps de 18 px |
| S26 ticket et anomalie | 6,9 | 8,3 | corps de 18 px |
| S28 formation | 5,8 | 12,1 | circuit C séparé (S28b) |
Résultat global : **44 schémas, 0 sous 8 pt** (avant : 10 sous 6,2 pt). S17, S21, S31 et S33 portent maintenant, **dans l'image**, le bandeau « CIBLE VALIDÉE PAR LE PO — NON DÉVELOPPÉ DANS L'ÉTAT B » avec cadre pointillé. Dix schémas « liste de cases » sont remplacés par des tableaux (brouillons générés dans `schemas/tableaux/`, à rédiger aux phases 5 à 7). Les schémas S09, S11 et S13, signalés petits à l'audit, ont été relayoutés ; S09 n'est pas encore refait (voir réserves).

## 3. Résultats des contrôles de non-régression sur les aperçus

| Contrôle | RF | GU | DT |
|---|---|---|---|
| C1 couverture du mapping (titres de l'ancien chapitre) | **13/13** couverts ou retirés | — | **8/8** (dont 1 retiré avec motif) |
| C2 étiquettes 🔵🟣⚪ conservées | 0 perdue ou promue ; 1 phrase à revoir à la main | — | 0 |
| C3 chiffres | 0 écart | 0 | 0 |
| C5 séparation et mention provisoire | **0 violation** | **0 violation** | 0 |
| C6 sommaire et renvois | 0 écart (9 entrées) | 0 écart (6) | 0 écart (12) |
| C7 décisions | 0 plage, 0 inconnue | 0 | 0 |
| C8 mise en page automatique | 0 bloquant ; 3 pages < 40 % | 0 bloquant ; 5 pages < 40 % | 0 bloquant ; 2 pages < 40 % |
| C13 application intacte depuis `637de94` | **0 fichier** | 0 | 0 |
| C14 données sensibles | 0 | 0 | 0 |
| G2 registre | 22 contrôles verts (`baseline/BARRIERE_G2.md`) | | |
| C4 références de code (DT) | 37 vérifiées, **1 « erreur » attendue** : le contrôleur cherche `audit_preuves/…` dans l'état B ; ce chemin est un fichier de preuve documentaire, pas du code | | |
| Tests du paquet `maintenance` sur la copie isolée de l'état B | **OK** (rejoués le 13/11/2026) | | |

Calibrage : les mêmes contrôles appliqués à l'ancien dossier (`baseline/MESURE_DE_BASE_ancien_dossier.md`) y détectent les défauts connus de l'audit (113 « diffusion générale », mention absente sur 108 pages, légende de S10 séparée, tableaux cassés p. 37 et 79, annexe F.5 dégradée).

## 4. Registre initial
26 écarts A1–A26, 8 points B, 7 propositions D, 6 NE, **38 anomalies documentaires** (36 actives), **125 décisions** avec état : 88 « non développée », 20 « à instruire », 8 « réalisée » (dont 2 lots livrés), 2 « partielle », 7 en écart documenté. Un statut de décision est déduit du plan en lots V1.2 ou vérifié dans le code ; **« à instruire » n'est pas un constat de non-réalisation**. Les 29 tests A14/A20/A25 restent dans `audit_preuves/` (décision du PO n° 3).

## 5. Difficultés et réserves (à lire avant de valider V1)
1. **Captures provisoires.** Les 12 captures du pilote sont celles du 12/11/2026, marquées « capture provisoire … reprise prévue en phase 4 » dans leur légende. Elles contiennent des textes anglais du navigateur (dates `mm/dd/yyyy`, « Choose File ») et des messages parasites, défauts de l'audit (AUD-014, 015) que la phase 4 corrigera.
2. **Page de partie presque vide.** Chaque partie (« Modules », « Parcours et écrans ») ouvre sur une page de titre seule : choix de structure à valider ; l'indicateur C8 la compte parmi les pages peu remplies.
3. **Pages peu remplies résiduelles** (RF 3, GU 5, DT 2) : surtout couvertures, pages de partie et fins de chapitre. Le traitement fin (couverture et pages de partie exclues du contrôle) sera fait avec la maquette validée.
4. **S09 non refait** (carte des dépendances entre paquets) : il reste lisible à 8,0 pt mais dense ; sa refonte demande une décision sur le niveau de détail.
5. **Contrôle C2 faible.** La comparaison d'étiquettes est lexicale ; elle a produit un faux positif corrigé et ne remplace pas la relecture. 1 phrase du pilote reste « à revoir à la main ».
6. **Contrôle automatique ≠ vérification éditoriale.** Les contrôles ne jugent ni le ton, ni la pédagogie, ni l'exactitude fonctionnelle ; c'est l'objet de votre revue V1.
7. **Inspection à taille réelle** : non réalisée à ce stade (prévue en phase 11). Les aperçus ont été regardés à 96 dpi, deux pages côte à côte, sans journal page à page ; **ne pas lire cette revue comme l'inspection finale**.
8. **Volumes.** Le chapitre pilote représente environ 6 pages de contenu dans le référentiel (11 avec couverture, sommaire et page de partie). Le total annoncé au plan (90 à 110 pages pour le référentiel) est indicatif ; aucune taille de caractère n'a été réduite pour s'en approcher (corps 10 pt, tableaux 8,8 pt).
9. **Références croisées.** Les renvois `GU §1`, `RF §1` ne sont résolus que dans le même document (liens) ; entre documents, ils ne sont que des mentions de texte (ancres non reliées d'un PDF à l'autre).
10. **Identifiant documentaire.** `EB-2026-11-11` désigne l'état B dans GU et RF ; la correspondance avec l'état applicatif n'est écrite que dans la couverture du dossier technique.

## 6. Ce que je vous demande de juger à V1
- **Structure** : trois documents par public, fiches de module, parcours illustrés.
- **Style et densité** : texte condensé et tableaux, cartouche réduit à une ligne.
- **Lisibilité** : corps de texte, schémas ≥ 8 pt, captures pleine largeur avec repères.
- **Pédagogie** : le guide est-il suffisant pour un marin ? la fiche pour un responsable ? le chapitre technique pour un mainteneur ?
- **Points ouverts** : pages de partie (garder ou non), repères sur les captures, place du registre dans les fiches.

**Je m'arrête ici. Aucune rédaction complète n'est lancée avant votre validation de V1.**
